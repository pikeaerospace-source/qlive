/**
 * Tests for the stream publisher seam (offline registry ↔ QDN).
 */

import { afterEach, describe, expect, it } from "vitest";

import {
  MOCK_PUBLISHER_NAME,
  MockStreamPublisher,
  mockPublisher,
  selectPublisher,
} from "./publisher";
import { qliveStreamIdentifier } from "./qapp";

const PUBLICATION = {
  streamId: "abc123",
  title: "Test stream",
  category: "gaming",
  status: "live" as const,
  fragmentDurationMs: 1000,
  resolution: { width: 1920, height: 1080, fps: 30 },
  bitrate: { video: 4_500_000, audio: 128_000 },
  startedAt: 1,
};

const setHost = (value: unknown) => {
  (globalThis as Record<string, unknown>).qortalRequest = value;
};

const clearHost = () => {
  delete (globalThis as Record<string, unknown>).qortalRequest;
};

describe("MockStreamPublisher", () => {
  it("records the published document in the offline registry", async () => {
    const publisher = new MockStreamPublisher();
    const result = await publisher.publishStream(PUBLICATION);

    expect(result.identifier).toBe(qliveStreamIdentifier("abc123"));
    expect(result.name).toBe(MOCK_PUBLISHER_NAME);
    expect(result.service).toBe("JSON");
    expect(publisher.streamIds).toEqual(["abc123"]);
    expect(publisher.getDoc("abc123")).toEqual(
      expect.objectContaining({
        type: "qlive-stream",
        publisher: MOCK_PUBLISHER_NAME,
        status: "live",
      }),
    );
  });

  it("replaces the document when the lifecycle changes", async () => {
    const publisher = new MockStreamPublisher();
    await publisher.publishStream(PUBLICATION);
    await publisher.publishStream({ ...PUBLICATION, status: "ended" });

    // Same identifier, one resource — only the status changed.
    expect(publisher.streamIds).toEqual(["abc123"]);
    expect(publisher.getDoc("abc123")?.status).toBe("ended");
  });

  it("drops the document on unpublish", async () => {
    const publisher = new MockStreamPublisher();
    await publisher.publishStream(PUBLICATION);
    await publisher.unpublishStream("abc123");

    expect(publisher.getDoc("abc123")).toBeUndefined();
    expect(publisher.streamIds).toEqual([]);
  });
});

describe("selectPublisher", () => {
  afterEach(clearHost);

  it("uses the offline registry when no Qortal host is present", () => {
    clearHost();
    expect(selectPublisher()).toBe(mockPublisher);
  });

  it("uses the QDN publisher when the host injects qortalRequest", () => {
    setHost(() => Promise.resolve({}));
    expect(selectPublisher()).not.toBe(mockPublisher);
  });
});
