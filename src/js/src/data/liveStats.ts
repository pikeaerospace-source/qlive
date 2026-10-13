import type { Stream, StreamStats } from "../types";

/**
 * A source of live stream statistics.
 *
 * Implementations either connect to a real WebSocket endpoint or simulate
 * updates locally (offline/mock mode). Consumers depend only on `StatsClient`,
 * so the backend can be swapped without touching the UI.
 */
export interface StatsClient {
  /** Subscribe to live stats for a stream. Returns an unsubscribe function. */
  subscribe(
    streamId: string,
    onUpdate: (stats: StreamStats) => void,
  ): () => void;
  /** Close the client, disconnecting and clearing any timers. */
  close(): void;
}

/** Simulates live viewer/bandwidth updates without a network connection. */
export class MockStatsClient implements StatsClient {
  private timers = new Map<string, ReturnType<typeof setInterval>>();
  private stats = new Map<string, StreamStats>();
  private nominalKbps = new Map<string, number>();

  constructor(streams: Stream[]) {
    for (const stream of streams) {
      const nominal = Math.round(stream.bitrate.video / 1000);
      this.nominalKbps.set(stream.streamId, nominal);
      this.stats.set(stream.streamId, {
        viewers: stream.viewers,
        bandwidthKbps: nominal,
        bufferState: "healthy",
        chunksProduced: 0,
        retransmissions: 0,
      });
    }
  }

  subscribe(
    streamId: string,
    onUpdate: (stats: StreamStats) => void,
  ): () => void {
    const current = this.stats.get(streamId);
    if (current) onUpdate({ ...current });

    const timer = setInterval(() => {
      const stats = this.stats.get(streamId);
      if (!stats) return;
      stats.viewers = Math.max(
        0,
        stats.viewers + Math.floor(Math.random() * 9) - 4,
      );
      stats.chunksProduced += 1;
      // Jitter bandwidth around the nominal so the dashboard graph moves, and
      // occasionally record a retransmission.
      const nominal = this.nominalKbps.get(streamId) ?? stats.bandwidthKbps;
      stats.bandwidthKbps = Math.max(
        1,
        Math.round(nominal * (1 + (Math.random() - 0.5) * 0.1)),
      );
      if (Math.random() < 0.15) stats.retransmissions += 1;
      onUpdate({ ...stats });
    }, 2000);

    this.timers.set(streamId, timer);
    return () => {
      clearInterval(timer);
      this.timers.delete(streamId);
    };
  }

  close(): void {
    for (const timer of this.timers.values()) clearInterval(timer);
    this.timers.clear();
  }
}

/** Connects to a real WebSocket endpoint and dispatches stats messages. */
export class WebSocketStatsClient implements StatsClient {
  private ws: WebSocket | null = null;
  private subscribers = new Map<string, Set<(stats: StreamStats) => void>>();
  private reconnectDelay = 1000;

  constructor(private readonly url: string) {
    this.connect();
  }

  private connect(): void {
    try {
      const ws = new WebSocket(this.url);
      this.ws = ws;

      ws.onopen = () => {
        this.reconnectDelay = 1000;
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(
            String(event.data),
          ) as Partial<StreamStats> & {
            type?: string;
            streamId?: string;
          };
          if (
            message.type === "stats" &&
            typeof message.streamId === "string"
          ) {
            this.dispatch(message.streamId, message as StreamStats);
          }
        } catch {
          // Ignore malformed messages.
        }
      };

      ws.onclose = () => {
        this.ws = null;
        setTimeout(() => this.connect(), this.reconnectDelay);
        this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30_000);
      };
    } catch {
      // WebSocket unavailable — stay dormant.
    }
  }

  private dispatch(streamId: string, stats: StreamStats): void {
    this.subscribers.get(streamId)?.forEach((cb) => cb(stats));
  }

  subscribe(
    streamId: string,
    onUpdate: (stats: StreamStats) => void,
  ): () => void {
    let set = this.subscribers.get(streamId);
    if (!set) {
      set = new Set();
      this.subscribers.set(streamId, set);
    }
    const subscriberSet = set;
    subscriberSet.add(onUpdate);
    return () => {
      subscriberSet.delete(onUpdate);
      if (subscriberSet.size === 0) this.subscribers.delete(streamId);
    };
  }

  close(): void {
    this.ws?.close();
    this.ws = null;
  }
}

/**
 * Create the appropriate stats client for the current environment.
 *
 * Set `VITE_STATS_WS_URL` to a WebSocket endpoint to receive real updates;
 * otherwise a local simulator is used so the UI works fully offline.
 */
export function createStatsClient(streams: Stream[]): StatsClient {
  const url = import.meta.env.VITE_STATS_WS_URL;
  if (typeof url === "string" && url.length > 0) {
    return new WebSocketStatsClient(url);
  }
  return new MockStatsClient(streams);
}
