import { useEffect, useRef } from "react";
import type Hls from "hls.js";
import type { Stream } from "../types";

export default function Player({ stream }: { stream: Stream }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const isLive = stream.status === "live";

  useEffect(() => {
    const video = videoRef.current;
    const url = stream.playbackUrl;
    if (!video || !url) return;

    // Native HLS (Safari) — no hls.js needed.
    if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = url;
      return;
    }

    let hls: Hls | undefined;
    let cancelled = false;

    // Lazy-load hls.js only when a real stream is being played.
    import("hls.js").then((mod) => {
      const HlsClass = mod.default;
      if (cancelled || !HlsClass.isSupported()) return;
      // Low-latency mode applies to the live edge only; a replay is the same
      // archived fragments played back at normal latency (no re-encoding).
      hls = new HlsClass({ enableWorker: true, lowLatencyMode: isLive });
      hls.loadSource(url);
      hls.attachMedia(video);
    });

    return () => {
      cancelled = true;
      hls?.destroy();
    };
  }, [stream.playbackUrl, isLive]);

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
    <video
      ref={videoRef}
      className="player"
      controls
      autoPlay
      muted
      playsInline
    />
  );
}
