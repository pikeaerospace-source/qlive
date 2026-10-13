import { useCallback, useEffect, useRef, useState } from "react";
import type Hls from "hls.js";
import type { Stream } from "../types";

/** Automatic network recoveries before the viewer is asked to retry. */
const MAX_AUTO_RECOVERIES = 2;
/** Backoff between automatic recovery attempts (exported for tests). */
export const RETRY_BACKOFF_MS = 1500;

/** Viewer-facing playback state of the player. */
export type PlaybackState =
  "connecting" | "playing" | "recovering" | "interrupted" | "unsupported";

/** Viewer-facing buffer health derived from the buffered-ahead window. */
export type BufferHealth = "buffering" | "low" | "healthy";

/**
 * Classify buffer health from the playback state and seconds buffered ahead.
 *
 * `buffering` when playback isn't running or the buffer is under half a second,
 * `low` under a 2 s threshold, otherwise `healthy`.
 */
export function bufferHealth(
  state: PlaybackState,
  bufferedAheadSec: number,
): BufferHealth {
  if (state !== "playing" || bufferedAheadSec < 0.5) return "buffering";
  if (bufferedAheadSec < 2) return "low";
  return "healthy";
}

/** ABR sentinel: hls.js `currentLevel = -1` selects the automatic level. */
export const AUTO_LEVEL = -1;

/** A selectable rendition advertised by the HLS manifest. */
export interface QualityLevel {
  height?: number;
  bitrate: number;
}

/** Human label for a rendition (e.g. `1080p`, or `4500 kbps` without a height). */
export function levelLabel(level: QualityLevel): string {
  return level.height
    ? `${level.height}p`
    : `${Math.round(level.bitrate / 1000)} kbps`;
}

/** Public playback controls exposed by the player (for keyboard shortcuts). */
export interface PlayerControls {
  togglePlay(): void;
  toggleMute(): void;
  toggleFullscreen(): void;
  togglePip(): void;
  nudgeVolume(delta: number): void;
}

/** Aggregated media state surfaced to the control bar. */
interface MediaStatus {
  paused: boolean;
  muted: boolean;
  volume: number;
  bufferedAheadSec: number;
  liveEdgeSec: number;
  /** Native fullscreen support (jsdom and older browsers lack it). */
  fullscreen: boolean;
  canFullscreen: boolean;
  /** Picture-in-picture is engaged for this element. */
  pip: boolean;
  canPip: boolean;
}

const INITIAL_MEDIA: MediaStatus = {
  paused: false,
  muted: true,
  volume: 1,
  bufferedAheadSec: 0,
  liveEdgeSec: 0,
  fullscreen: false,
  canFullscreen: false,
  pip: false,
  canPip: false,
};

/** Narrow view of the (non-standard in TS DOM lib) PiP members we touch. */
type PipDocument = Document & {
  pictureInPictureEnabled?: boolean;
  pictureInPictureElement?: Element | null;
  exitPictureInPicture?: () => Promise<void>;
};
type PipVideo = HTMLVideoElement & {
  requestPictureInPicture?: () => Promise<unknown>;
};

export default function Player({
  stream,
  controlsRef,
}: {
  stream: Stream;
  /** Optional sink for the playback controls (used by keyboard shortcuts). */
  controlsRef?: { current: PlayerControls | null };
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  /** Live hls.js instance (for the quality selector). */
  const hlsRef = useRef<Hls | null>(null);
  const [state, setState] = useState<PlaybackState>("connecting");
  /** Bumped by Retry to rebuild the playback pipeline from scratch. */
  const [attempt, setAttempt] = useState(0);
  const [media, setMedia] = useState<MediaStatus>(INITIAL_MEDIA);
  /** Renditions advertised by the HLS manifest (empty until parsed). */
  const [levels, setLevels] = useState<QualityLevel[]>([]);
  /** Selected rendition index, or `AUTO_LEVEL` for ABR. */
  const [quality, setQuality] = useState<number>(AUTO_LEVEL);

  const isLive = stream.status === "live";
  const url = stream.playbackUrl;

  /**
   * Low-latency playback mode. Defaults to on for a live stream (chase the live
   * edge) and off for a replay (a static archive has no edge). hls.js only reads
   * this at construction, so toggling it rebuilds the pipeline.
   */
  const [lowLatency, setLowLatency] = useState(isLive);

  // A replay has no live edge, so reset the mode whenever the stream changes.
  useEffect(() => {
    setLowLatency(isLive);
  }, [isLive]);

  // Mirror the media element's state into React. Kept as a `useEffect` (rather
  // than inline handlers) so the controls stay in sync with both the hls.js and
  // native playback paths.
  useEffect(() => {
    const video = videoRef.current;
    if (!video || !url) return;

    const sync = () => {
      let bufferedAhead = 0;
      const { buffered, currentTime } = video;
      for (let i = 0; i < buffered.length; i += 1) {
        if (
          buffered.start(i) <= currentTime &&
          currentTime <= buffered.end(i)
        ) {
          bufferedAhead = buffered.end(i) - currentTime;
          break;
        }
      }
      const doc = document as PipDocument;
      setMedia({
        paused: video.paused,
        muted: video.muted,
        volume: video.volume,
        bufferedAheadSec: bufferedAhead,
        // Live edge = distance from the end of the buffered range; a replay
        // reports 0 because it is not tracked against a live target.
        liveEdgeSec: isLive && buffered.length > 0 ? bufferedAhead : 0,
        fullscreen: document.fullscreenElement === video,
        canFullscreen: typeof video.requestFullscreen === "function",
        pip: doc.pictureInPictureElement === video,
        canPip:
          doc.pictureInPictureEnabled === true &&
          typeof (video as PipVideo).requestPictureInPicture === "function",
      });
    };

    const events = [
      "play",
      "pause",
      "volumechange",
      "progress",
      "playing",
      "waiting",
      "enterpictureinpicture",
      "leavepictureinpicture",
    ] as const;
    events.forEach((event) => video.addEventListener(event, sync));
    document.addEventListener("fullscreenchange", sync);
    sync();

    return () => {
      events.forEach((event) => video.removeEventListener(event, sync));
      document.removeEventListener("fullscreenchange", sync);
    };
  }, [url, isLive]);

  const togglePlay = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    if (video.paused) {
      // jsdom doesn't implement play(); tolerate a non-Promise return.
      const playing = video.play();
      if (playing && typeof playing.catch === "function") {
        playing.catch(() => undefined);
      }
    } else {
      video.pause();
    }
  }, []);

  const toggleMute = useCallback(() => {
    const video = videoRef.current;
    if (video) video.muted = !video.muted;
  }, []);

  const nudgeVolume = useCallback((delta: number) => {
    const video = videoRef.current;
    if (video) video.volume = Math.min(1, Math.max(0, video.volume + delta));
  }, []);

  const toggleFullscreen = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    if (document.fullscreenElement === video) {
      void document.exitFullscreen?.().catch(() => undefined);
    } else {
      void video.requestFullscreen?.().catch(() => undefined);
    }
  }, []);

  const togglePip = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    const doc = document as PipDocument;
    if (doc.pictureInPictureElement === video) {
      void doc.exitPictureInPicture?.().catch(() => undefined);
      return;
    }
    const request = (video as PipVideo).requestPictureInPicture;
    if (typeof request === "function") {
      const result = request.call(video) as Promise<unknown> | undefined;
      if (result && typeof result.catch === "function") {
        result.catch(() => undefined);
      }
    }
  }, []);

  // Publish the controls so a host (e.g. the watch page) can wire shortcuts.
  useEffect(() => {
    if (!controlsRef) return;
    controlsRef.current = {
      togglePlay,
      toggleMute,
      toggleFullscreen,
      togglePip,
      nudgeVolume,
    };
    return () => {
      if (controlsRef) controlsRef.current = null;
    };
  }, [
    controlsRef,
    togglePlay,
    toggleMute,
    toggleFullscreen,
    togglePip,
    nudgeVolume,
  ]);

  // Keyboard shortcuts (Space/K = play-pause, M = mute, F = fullscreen,
  // I = picture-in-picture, ↑/↓ = volume). Scoped to the player wrapper so they
  // don't hijack typing in the page's search/inputs. `preventDefault` stops Space
  // from scrolling.
  useEffect(() => {
    const wrap = wrapRef.current;
    if (!wrap) return;
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.tagName === "SELECT" ||
        target.isContentEditable
      ) {
        return;
      }
      switch (event.key) {
        case " ":
        case "k":
        case "K":
          event.preventDefault();
          togglePlay();
          break;
        case "m":
        case "M":
          toggleMute();
          break;
        case "f":
        case "F":
          toggleFullscreen();
          break;
        case "i":
        case "I":
          togglePip();
          break;
        case "ArrowUp":
          event.preventDefault();
          nudgeVolume(0.1);
          break;
        case "ArrowDown":
          event.preventDefault();
          nudgeVolume(-0.1);
          break;
        default:
          break;
      }
    };
    wrap.addEventListener("keydown", onKeyDown);
    return () => wrap.removeEventListener("keydown", onKeyDown);
  }, [togglePlay, toggleMute, toggleFullscreen, togglePip, nudgeVolume]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !url) return;

    setState("connecting");
    // The pipeline is rebuilt on every window/retry change: drop stale renditions.
    setLevels([]);
    setQuality(AUTO_LEVEL);
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
      // archived fragments played back at normal latency (no re-encoding). The
      // mode is a constructor option, so toggling it re-runs this effect.
      hls = new HlsClass({ enableWorker: true, lowLatencyMode: lowLatency });
      hlsRef.current = hls;

      // Expose the manifest's renditions so the control bar can offer a quality
      // selector, and keep it in sync as ABR switches levels.
      hls.on(HlsClass.Events.MANIFEST_PARSED, () => {
        setLevels(
          (hls?.levels ?? []).map((level) => ({
            height: level.height,
            bitrate: level.bitrate,
          })),
        );
      });
      hls.on(HlsClass.Events.LEVEL_SWITCHED, () => {
        setQuality(
          hls?.autoLevelEnabled
            ? AUTO_LEVEL
            : (hls?.currentLevel ?? AUTO_LEVEL),
        );
      });

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
      hlsRef.current = null;
      hls?.destroy();
    };
  }, [url, isLive, lowLatency, attempt]);

  /** Select a rendition, or `AUTO_LEVEL` to re-enable ABR. */
  function selectQuality(value: number) {
    setQuality(value);
    if (hlsRef.current) hlsRef.current.currentLevel = value;
  }

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

  const health = bufferHealth(state, media.bufferedAheadSec);
  const bufferedAheadLabel = `${media.bufferedAheadSec.toFixed(1)}s`;

  return (
    <div className="player-wrap" ref={wrapRef}>
      <video ref={videoRef} className="player" autoPlay muted playsInline />

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

      <div className="player-controls">
        <button
          type="button"
          className="player-controls__btn"
          onClick={togglePlay}
          aria-label={media.paused ? "Play" : "Pause"}
        >
          {media.paused ? "▶" : "❚❚"}
        </button>

        <button
          type="button"
          className="player-controls__btn"
          onClick={toggleMute}
          aria-label={media.muted ? "Unmute" : "Mute"}
        >
          {media.muted || media.volume === 0 ? "🔇" : "🔊"}
        </button>

        <input
          type="range"
          className="player-controls__volume"
          min={0}
          max={1}
          step={0.05}
          value={media.muted ? 0 : media.volume}
          aria-label="Volume"
          onChange={(e) => {
            const video = videoRef.current;
            if (!video) return;
            video.volume = Number(e.target.value);
            video.muted = Number(e.target.value) === 0;
          }}
        />

        <span className="player-controls__spacer" />

        {isLive && (
          <span className="player-controls__badge" title="Seconds behind live">
            {media.liveEdgeSec > 0.5
              ? `${media.liveEdgeSec.toFixed(1)}s behind live`
              : "At live edge"}
          </span>
        )}

        <span
          className={`player-controls__buffer player-controls__buffer--${health}`}
          title={`${bufferedAheadLabel} buffered ahead`}
          data-buffer-health={health}
        >
          {health === "buffering"
            ? "Buffering"
            : `Buffer ${media.bufferedAheadSec.toFixed(1)}s`}
        </span>

        {levels.length > 0 ? (
          <select
            className="player-controls__quality"
            aria-label="Stream quality"
            title="Stream quality"
            value={quality}
            onChange={(e) => selectQuality(Number(e.target.value))}
          >
            <option value={AUTO_LEVEL}>Auto</option>
            {levels.map((level, index) => (
              <option key={index} value={index}>
                {levelLabel(level)}
              </option>
            ))}
          </select>
        ) : (
          <span className="player-controls__quality" title="Stream quality">
            Source
          </span>
        )}

        {isLive && (
          <button
            type="button"
            className="player-controls__btn player-controls__toggle"
            onClick={() => setLowLatency((value) => !value)}
            aria-pressed={lowLatency}
            aria-label="Low latency mode"
            title="Low latency mode"
          >
            LL
          </button>
        )}

        <button
          type="button"
          className="player-controls__btn"
          onClick={togglePip}
          aria-label={
            media.pip ? "Exit picture in picture" : "Picture in picture"
          }
          title="Picture in picture"
          disabled={!media.canPip}
        >
          ⧉
        </button>

        <button
          type="button"
          className="player-controls__btn"
          onClick={toggleFullscreen}
          aria-label={media.fullscreen ? "Exit fullscreen" : "Fullscreen"}
          disabled={!media.canFullscreen}
        >
          ⛶
        </button>
      </div>
    </div>
  );
}
