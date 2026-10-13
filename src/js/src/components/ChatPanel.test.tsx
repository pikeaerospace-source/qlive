/**
 * Tests for the live chat panel.
 *
 * The chat client (`../data/chat`) is mocked, so these run offline and assert
 * the panel's rendering plus its send/subscribe wiring.
 */

import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ChatMessage } from "../data/chat";
import ChatPanel from "./ChatPanel";

const mocks = vi.hoisted(() => ({ subscribe: vi.fn(), send: vi.fn() }));

vi.mock("../data/chat", () => ({
  createChatClient: () => ({ subscribe: mocks.subscribe, send: mocks.send }),
}));

const message = (author: string, text: string): ChatMessage => ({
  id: `${author}-${text}`,
  author,
  text,
  at: 1,
});

describe("ChatPanel", () => {
  beforeEach(() => {
    mocks.subscribe.mockReset();
    mocks.subscribe.mockReturnValue(() => {});
    mocks.send.mockReset();
  });

  const input = () => screen.getByLabelText("Chat message") as HTMLInputElement;
  const send = () => screen.getByRole("button", { name: "Send" });

  it("renders the messages delivered by the client", async () => {
    mocks.subscribe.mockImplementation((_id, cb: (m: ChatMessage) => void) => {
      cb(message("bob", "hello there"));
      return () => {};
    });

    render(<ChatPanel streamId="s1" />);

    expect(await screen.findByText("hello there")).toBeInTheDocument();
    expect(screen.getByText("bob")).toBeInTheDocument();
    expect(mocks.subscribe).toHaveBeenCalledWith("s1", expect.any(Function));
  });

  it("appends messages pushed after subscription", async () => {
    let push: ((m: ChatMessage) => void) | undefined;
    mocks.subscribe.mockImplementation((_id, cb: (m: ChatMessage) => void) => {
      push = cb;
      return () => {};
    });
    render(<ChatPanel streamId="s1" />);

    act(() => push?.(message("carol", "incoming")));

    expect(await screen.findByText("incoming")).toBeInTheDocument();
  });

  it("sends the trimmed draft and clears the box", async () => {
    render(<ChatPanel streamId="s1" />);

    fireEvent.change(input(), { target: { value: "  hi there  " } });
    fireEvent.click(send());

    expect(mocks.send).toHaveBeenCalledWith("s1", "  hi there  ", "you");
    expect(input().value).toBe("");
  });

  it("disables Send until the draft has content", () => {
    render(<ChatPanel streamId="s1" />);

    expect(send()).toBeDisabled();
    fireEvent.change(input(), { target: { value: "   " } });
    expect(send()).toBeDisabled();
    fireEvent.change(input(), { target: { value: "ok" } });
    expect(send()).toBeEnabled();
  });

  it("uses a custom author handle when provided", () => {
    render(<ChatPanel streamId="s1" author="alice" />);

    fireEvent.change(input(), { target: { value: "hey" } });
    fireEvent.click(send());

    expect(mocks.send).toHaveBeenCalledWith("s1", "hey", "alice");
  });

  it("resubscribes when the stream changes", () => {
    const { rerender } = render(<ChatPanel streamId="s1" />);
    rerender(<ChatPanel streamId="s2" />);

    expect(mocks.subscribe).toHaveBeenCalledWith("s1", expect.any(Function));
    expect(mocks.subscribe).toHaveBeenCalledWith("s2", expect.any(Function));
  });
});
