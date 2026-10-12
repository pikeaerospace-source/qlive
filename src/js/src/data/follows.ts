/**
 * QLive — followed-streamer store.
 *
 * A tiny `localStorage`-backed set of Qortal Names the viewer follows. Kept
 * dependency-free and fully offline (no QDN/host required) so follow state works
 * in mock mode and survives a reload. Components subscribe with
 * `useSyncExternalStore(subscribe, listFollowing, listFollowing)`; `listFollowing`
 * returns a stable snapshot that only changes on an actual follow/unfollow.
 */

const STORAGE_KEY = "qlive:follows";

let cache: Set<string> | undefined;
let snapshot: string[] | undefined;
const listeners = new Set<() => void>();

/** Read the followed-names set (cached; falls back to in-memory if storage is off). */
function read(): Set<string> {
  if (cache) return cache;
  try {
    const raw = globalThis.localStorage?.getItem(STORAGE_KEY);
    cache = new Set<string>(raw ? (JSON.parse(raw) as string[]) : []);
  } catch {
    // Private mode / storage unavailable: keep state in memory only.
    cache = new Set();
  }
  return cache;
}

/** Persist `next`, invalidate the snapshot, and notify subscribers. */
function commit(next: Set<string>): void {
  cache = next;
  snapshot = undefined;
  try {
    globalThis.localStorage?.setItem(STORAGE_KEY, JSON.stringify([...next]));
  } catch {
    // Ignore write failures; the in-memory set still reflects the change.
  }
  listeners.forEach((notify) => notify());
}

/** Current followed names, sorted (stable reference between changes). */
export function listFollowing(): string[] {
  if (!snapshot) snapshot = [...read()].sort();
  return snapshot;
}

/** Whether the viewer follows `name`. */
export function isFollowing(name: string): boolean {
  return read().has(name);
}

/** Toggle a follow; returns the resulting state (true = now following). */
export function toggleFollow(name: string): boolean {
  const next = new Set(read());
  const following = !next.has(name);
  if (following) next.add(name);
  else next.delete(name);
  commit(next);
  return following;
}

/** Subscribe to follow changes (for `useSyncExternalStore`). */
export function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Clear all follows (used by tests). */
export function clearFollows(): void {
  commit(new Set());
}
