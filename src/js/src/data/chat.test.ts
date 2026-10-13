/**
 * Tests for the offline live-chat client.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { type ChatMessage, MockChatClient } from "./chat";

describe("MockChatClient", () => {
  let client: MockChatClient;

  beforeEach(() => {
    client = new MockChatClient();
  });

  afterEach(() => {
    client.close();
    vi.useRealTimers();
  });

  it("seeds an audience and replays history to new subscribers", () => {
    const first: ChatMessage[] = [];
    client.subscribe("s1", (m) => first.push(m));

    expect(first.length).toBeGreaterThan(0);
    expect(first.map((m) => m.author)).toContain("bob");

    // A later subscriber receives the same history.
    const second: ChatMessage[] = [];
    client.subscribe("s1", (m) => second.push(m));
    expect(second.map((m) => m.text)).toEqual(first.map((m) => m.text));
  });

  it("echoes a sent message to subscribers, trimmed", () => {
    const seen: ChatMessage[] = [];
    client.subscribe("s1", (m) => seen.push(m));
    const before = seen.length;

    client.send("s1", "  hello world  ", "alice");

    expect(seen).toHaveLength(before + 1);
    expect(seen[seen.length - 1]).toMatchObject({
      author: "alice",
      text: "hello world",
    });
  });

  it("ignores blank messages", () => {
    const seen: ChatMessage[] = [];
    client.subscribe("s1", (m) => seen.push(m));
    const before = seen.length;

    client.send("s1", "   ");

    expect(seen).toHaveLength(before);
  });

  it("gives every message a unique id", () => {
    const seen: ChatMessage[] = [];
    client.subscribe("s1", (m) => seen.push(m));
    client.send("s1", "a");
    client.send("s1", "b");

    expect(new Set(seen.map((m) => m.id)).size).toBe(seen.length);
  });

  it("delivers a canned reply after a delay", () => {
    vi.useFakeTimers();
    const seen: ChatMessage[] = [];
    client.subscribe("s1", (m) => seen.push(m));
    client.send("s1", "hi");
    const before = seen.length;

    vi.advanceTimersByTime(1200);

    expect(seen).toHaveLength(before + 1);
    expect(seen[seen.length - 1].author).toBe("bob");
  });

  it("stops delivering after unsubscribe", () => {
    const seen: ChatMessage[] = [];
    const off = client.subscribe("s1", (m) => seen.push(m));
    off();
    const before = seen.length;

    client.send("s1", "nobody is listening");

    expect(seen).toHaveLength(before);
  });

  it("keeps streams separate", () => {
    const one: ChatMessage[] = [];
    const two: ChatMessage[] = [];
    client.subscribe("s1", (m) => one.push(m));
    client.subscribe("s2", (m) => two.push(m));

    client.send("s1", "only s1");

    expect(one[one.length - 1].text).toBe("only s1");
    expect(two.some((m) => m.text === "only s1")).toBe(false);
  });
});
