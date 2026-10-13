/**
 * QLive — live chat panel for a stream.
 *
 * Renders the ephemeral, stream-scoped chat (see `data/chat.ts`) with a compose
 * box. The client is the single source of truth: a sent message is echoed back
 * through the subscription, so the panel renders the same way for the author and
 * everyone else.
 */

import { type FormEvent, useEffect, useState } from "react";

import { createChatClient, type ChatMessage } from "../data/chat";

export default function ChatPanel({
  streamId,
  author = "you",
}: {
  streamId: string;
  /** Display name for the local viewer's messages. */
  author?: string;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");

  useEffect(() => {
    setMessages([]);
    return createChatClient().subscribe(streamId, (message) =>
      setMessages((previous) => [...previous, message]),
    );
  }, [streamId]);

  const canSend = draft.trim().length > 0;

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!canSend) return;
    createChatClient().send(streamId, draft, author);
    setDraft("");
  }

  return (
    <section className="card chat" aria-label="Live chat">
      <h2 className="section-title">Live chat</h2>
      <p className="page-subtitle">
        Ephemeral — messages vanish with the stream.
      </p>

      <ul className="chat__log" aria-live="polite" data-testid="chat-log">
        {messages.map((message) => (
          <li key={message.id} className="chat__message">
            <span className="chat__author">{message.author}</span>
            <span className="chat__text">{message.text}</span>
          </li>
        ))}
      </ul>

      <form className="chat__form" onSubmit={submit}>
        <input
          className="search"
          aria-label="Chat message"
          placeholder="Say something…"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
        />
        <button type="submit" className="btn" disabled={!canSend}>
          Send
        </button>
      </form>
    </section>
  );
}
