/**
 * Tests for the offline followed-streamer store.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  clearFollows,
  isFollowing,
  listFollowing,
  subscribe,
  toggleFollow,
} from "./follows";

describe("follows store", () => {
  beforeEach(() => {
    clearFollows();
  });

  it("toggles a follow and reports the resulting state", () => {
    expect(isFollowing("alice")).toBe(false);

    expect(toggleFollow("alice")).toBe(true);
    expect(isFollowing("alice")).toBe(true);
    expect(listFollowing()).toContain("alice");

    expect(toggleFollow("alice")).toBe(false);
    expect(isFollowing("alice")).toBe(false);
  });

  it("returns a stable snapshot until a change occurs", () => {
    const first = listFollowing();
    expect(listFollowing()).toBe(first); // same reference

    toggleFollow("bob");
    expect(listFollowing()).not.toBe(first); // invalidated on change
  });

  it("keeps the followed names sorted", () => {
    toggleFollow("carol");
    toggleFollow("alice");
    expect(listFollowing()).toEqual(["alice", "carol"]);
  });

  it("persists follows to localStorage", () => {
    toggleFollow("alice");

    const raw = globalThis.localStorage.getItem("qlive:follows");
    expect(JSON.parse(raw ?? "[]")).toEqual(["alice"]);
  });

  it("notifies subscribers on change and stops after unsubscribe", () => {
    const listener = vi.fn();
    const off = subscribe(listener);

    toggleFollow("alice");
    expect(listener).toHaveBeenCalledTimes(1);

    off();
    toggleFollow("bob");
    expect(listener).toHaveBeenCalledTimes(1);
  });

  it("clears all follows", () => {
    toggleFollow("alice");
    clearFollows();
    expect(listFollowing()).toEqual([]);
  });
});
