/**
 * QLive — live stream chat client.
 *
 * Chat is an *ephemeral, stream-scoped* channel (like the swarm data plane, not
 * QDN): messages ride the live transport and vanish with the stream. This module
 * defines the seam the Web UI depends on and ships an offline simulator so chat
 * works in mock mode with no network or host.
 *
 * A WebSocket/mesh-backed client (`WebSocketChatClient`) lands with the live
 * transport; swap it in behind `createChatClient()` without touching the UI.
 */

/** A single chat line. */
export interface ChatMessage {
  id: string;
  /** Qortal Name of the author (or a display handle). */
  author: string;
  text: string;
  /** Unix epoch ms. */
  at: number;
}

/** A source of live chat messages for a stream. */
export interface ChatClient {
  /** Subscribe to a stream's chat. Returns an unsubscribe function. */
  subscribe(
    streamId: string,
    onMessage: (message: ChatMessage) => void,
  ): () => void;
  /** Send a message to a stream's chat. */
  send(streamId: string, text: string, author?: string): void;
  /** Disconnect and clear any state. */
  close(): void;
}

/** Canned audience lines replayed when a viewer joins a mock stream. */
const SEED_LINES: { author: string; text: string }[] = [
  { author: "bob", text: "Just joined — stream looks great!" },
  { author: "carol", text: "Audio is clean on my end 👍" },
];

/** Placeholder replies so a mock chat feels alive (a real client streams mesh). */
const CANNED_REPLIES: string[] = [
  "Nice one!",
  "Same here 🙂",
  "Thanks for watching!",
];

let sequence = 0;
const nextId = () => `msg-${++sequence}`;

/** Simulates a live stream chat locally (offline/mock mode). */
export class MockChatClient implements ChatClient {
  /** Per-stream message log, replayed to new subscribers. */
  private logs = new Map<string, ChatMessage[]>();
  /** Live subscribers per stream (a sent message is echoed back to all of them). */
  private subscribers = new Map<string, Set<(message: ChatMessage) => void>>();
  private timers = new Set<ReturnType<typeof setTimeout>>();
  /** Index into CANNED_REPLIES for deterministic mock replies. */
  private replyIndex = 0;

  subscribe(
    streamId: string,
    onMessage: (message: ChatMessage) => void,
  ): () => void {
    let log = this.logs.get(streamId);
    if (!log) {
      log = [];
      this.logs.set(streamId, log);
      // Seed a short "audience" the first time the stream is joined.
      for (const line of SEED_LINES) {
        log.push({
          id: nextId(),
          author: line.author,
          text: line.text,
          at: Date.now(),
        });
      }
    }
    // Replay history, then track the subscriber for live messages.
    [...log].forEach(onMessage);

    let set = this.subscribers.get(streamId);
    if (!set) {
      set = new Set();
      this.subscribers.set(streamId, set);
    }
    const subscriberSet = set;
    subscriberSet.add(onMessage);

    return () => {
      subscriberSet.delete(onMessage);
      if (subscriberSet.size === 0) this.subscribers.delete(streamId);
    };
  }

  send(streamId: string, text: string, author = "you"): void {
    const trimmed = text.trim();
    if (trimmed.length === 0) return;

    // Echo the message back through the subscription (single source of truth).
    this.post(streamId, {
      id: nextId(),
      author,
      text: trimmed,
      at: Date.now(),
    });

    // A single canned reply keeps the mock alive; the real client has none.
    const reply = CANNED_REPLIES[this.replyIndex % CANNED_REPLIES.length];
    this.replyIndex += 1;
    const timer = setTimeout(() => {
      this.timers.delete(timer);
      this.post(streamId, {
        id: nextId(),
        author: "bob",
        text: reply,
        at: Date.now(),
      });
    }, 1200);
    this.timers.add(timer);
  }

  close(): void {
    for (const timer of this.timers) clearTimeout(timer);
    this.timers.clear();
    this.logs.clear();
    this.subscribers.clear();
  }

  /** Append a message to the log and dispatch it to live subscribers. */
  private post(streamId: string, message: ChatMessage): void {
    const log = this.logs.get(streamId) ?? [];
    this.logs.set(streamId, log);
    log.push(message);
    this.subscribers.get(streamId)?.forEach((cb) => cb(message));
  }
}

let client: ChatClient | undefined;

/**
 * The chat client for the current environment. Returns the offline simulator —
 * a mesh/WebSocket client replaces it once the live transport is wired.
 */
export function createChatClient(): ChatClient {
  if (!client) client = new MockChatClient();
  return client;
}

/** Reset the shared client (used by tests). */
export function resetChatClient(): void {
  client?.close();
  client = undefined;
}
