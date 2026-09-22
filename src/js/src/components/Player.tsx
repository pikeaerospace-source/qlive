import { useEffect, useRef, useState } from "react";
import type Hls from "hls.js";
import type { Stream } from "../types";

/** Automatic network recoveries before the viewer is asked to retry. */
const MAX_AUTO_RECOVERIES = 2;
/** Backoff between automatic recovery attempts (exported for tests). */
export const RETRY_BACKOFF_MS = 1500;

/** Viewer-facing playback state of the player. */
export type PlaybackState =
  | "connecting"
  | "playing"
  | "recovering"
  | "interrupted"
  | "unsupported";

export default function Player({ stream }: { stream: Stream }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [state, setState] = useState<PlaybackState>("connecting");
  /** Bumped by Retry to rebuild the playback pipeline from scratch. */
  const [attempt, setAttempt] = useState(0);

  const isLive = stream.status === "live";
  const url = stream.playbackUrl;

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !url) return;

    setState("connecting");
    let cancelled = false;
    let hls: Hls | undefined;
    let recoveries = 0;
    let mediaRecoveries = 0;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const onPlaying = () => {
      recoveries = 0;
      mediaRecoveries = 0;
      setState("playing");
    };
    video.addEventListener("playing", onPlaying);

    /** Retry a recovery step after a backoff, or ask the viewer to retry. */
    const recoverAfterBackoff = (recover: () => void) => {
      if (recoveries >= MAX_AUTO_RECOVERIES) {
        setState("interrupted");
        return;
      }
      recoveries += 1;
      setState("recovering");
      timer = setTimeout(() => {
        if (!cancelled) recover();
      }, RETRY_BACKOFF_MS);
    };

    // Native HLS (Safari) — no hls.js; recover by re-attaching the source.
    if (video.canPlayType("application/vnd.apple.mpegurl")) {
      const onNativeError = () =>
        recoverAfterBackoff(() => {
          video.src = url;
        });
      video.src = url;
      video.addEventListener("error", onNativeError);
      return () => {
        cancelled = true;
        if (timer) clearTimeout(timer);
        video.removeEventListener("playing", onPlaying);
        video.removeEventListener("error", onNativeError);
      };
    }

    // Lazy-load hls.js only when a real stream is being played.
    import("hls.js").then((mod) => {
      const HlsClass = mod.default;
      if (cancelled) return;
      if (!HlsClass.isSupported()) {
        setState("unsupported");
        return;
      }
      // Low-latency mode applies to the live edge only; a replay is the same
      // archived fragments played back at normal latency (no re-encoding).
      hls = new HlsClass({ enableWorker: true, lowLatencyMode: isLive });

      hls.on(HlsClass.Events.ERROR, (_event, data) => {
        if (!data.fatal) return; // hls.js recovers non-fatal errors by itself.
        if (data.type === HlsClass.ErrorTypes.NETWORK_ERROR) {
          // Slow/stalled network (or a dropped broadcaster): resume loading.
          recoverAfterBackoff(() => hls?.startLoad());
          return;
        }
        if (data.type === HlsClass.ErrorTypes.MEDIA_ERROR) {
          // Media pipeline errors can be recovered once (codec swap/rebuffer).
          if (mediaRecoveries === 0) {
            mediaRecoveries += 1;
            setState("recovering");
            hls?.recoverMediaError();
            return;
          }
          setState("interrupted");
          return;
        }
        setState("interrupted");
      });

      hls.loadSource(url);
      hls.attachMedia(video);
    });

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
      video.removeEventListener("playing", onPlaying);
      hls?.destroy();
    };
  }, [url, isLive, attempt]);

  if (!stream.playbackUrl) {
    return (
      <div className="player player--placeholder">
        <strong>{stream.title}</strong>
        <span className="muted">
          No {isLive ? "live" : "replay"} source available — mock/offline mode.
        </span>
      </div>
    );
  }

  return (
    <div className="player-wrap">
      <video
        ref={videoRef}
        className="player"
        controls
        autoPlay
        muted
        playsInline
      />

      {state !== "playing" && (
        <div
          className="player-overlay"
          role="status"
          aria-live="polite"
          data-playback-state={state}
        >
          {state === "connecting" && <span>Connecting…</span>}
          {state === "recovering" && <span>Reconnecting…</span>}
          {state === "unsupported" && (
            <span>This browser cannot play the stream.</span>
          )}
          {state === "interrupted" && (
            <>
              <strong>Playback interrupted</strong>
              <button
                type="button"
                className="btn"
                onClick={() => setAttempt((n) => n + 1)}
              >
                Retry
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
