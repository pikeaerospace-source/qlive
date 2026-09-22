/**
 * QLive — stream signaling publisher seam.
 *
 * Mirrors the read-side seam in `api.ts` (`selectApi()`) for the **write** path:
 * callers publish stream metadata through `selectPublisher()`, which is
 * QDN-backed when running inside a Qortal UI host (`qortalRequest` present) and
 * an in-memory registry otherwise — so the broadcaster dashboard works in
 * offline dev, CI, and unit tests without touching a node.
 *
 * The offline publisher is deliberately *not* a fake QDN: it records documents in
 * memory so the UI can show what it would have published. Nothing leaves the
 * browser until a host is present.
 */

import {
  qliveStreamIdentifier,
  qliveStreamPublisher,
  streamPublicationToDoc,
} from "./qapp";
import type {
  QLiveStreamDoc,
  StreamPublication,
  StreamPublisher,
  StreamPublishResult,
} from "./qapp";

/** Qortal Name reported by the offline publisher (no real identity offline). */
export const MOCK_PUBLISHER_NAME = "offline";

/**
 * In-memory `StreamPublisher` for offline mode: keeps the latest
 * `qlive-stream` doc per stream id instead of publishing to QDN.
 */
export class MockStreamPublisher implements StreamPublisher {
  private readonly registry = new Map<string, QLiveStreamDoc>();

  constructor(private readonly name: string = MOCK_PUBLISHER_NAME) {}

  publishStream = async (
    pub: StreamPublication,
  ): Promise<StreamPublishResult> => {
    const doc = streamPublicationToDoc(pub, this.name);
    this.registry.set(pub.streamId, doc);
    return {
      name: this.name,
      identifier: qliveStreamIdentifier(pub.streamId),
      service: "JSON",
      doc,
    };
  };

  unpublishStream = async (streamId: string): Promise<void> => {
    this.registry.delete(streamId);
  };

  /** The document currently "published" for a stream (offline inspection). */
  getDoc(streamId: string): QLiveStreamDoc | undefined {
    return this.registry.get(streamId);
  }

  /** Stream ids currently in the offline registry. */
  get streamIds(): string[] {
    return [...this.registry.keys()];
  }

  clear(): void {
    this.registry.clear();
  }
}

/** Shared offline registry (module singleton, mirroring the mock `api`). */
export const mockPublisher = new MockStreamPublisher();

const hasHost = (): boolean =>
  typeof (globalThis as { qortalRequest?: unknown }).qortalRequest ===
  "function";

/**
 * Prefer the QDN publisher inside a Qortal UI host, otherwise the offline
 * registry. The check is a host-presence probe, exactly like `selectApi()`.
 */
export const selectPublisher = (): StreamPublisher =>
  hasHost() ? qliveStreamPublisher : mockPublisher;
