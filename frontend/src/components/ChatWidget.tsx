import React, { useEffect, useRef, useState } from "react";

type Role = "user" | "assistant";

interface Message {
  id: string;
  role: Role;
  content: string;
  sourceUrl?: string;
  intentType?: string;
  refusal?: boolean;
}

interface ApiChatResponse {
  answer: string;
  source_url: string;
  intent_type: string;
  scheme_slug?: string | null;
  refusal: boolean;
}

const initialBotMessage =
  "Hi, I’m your Groww Mutual Fund FAQ assistant. I can answer factual questions about selected HDFC mutual fund schemes and mutual fund charges using information from Groww’s public pages.\n\nI cannot provide investment advice, opinions, or recommendations.";

export const ChatWidget: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: initialBotMessage,
    },
  ]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  const sendMessage = async () => {
    const trimmed = input.trim();
    if (!trimmed || isSending) return;

    setError(null);
    const userMessage: Message = {
      id: `msg-${Date.now()}-user`,
      role: "user",
      content: trimmed,
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsSending(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          session_id: null,
          messages: [
            ...messages.map((m) => ({ role: m.role, content: m.content })),
            { role: "user", content: trimmed },
          ],
        }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        const detail =
          (body && body.detail) ||
          "Unable to get a response from the assistant.";
        throw new Error(detail);
      }

      const data: ApiChatResponse = await res.json();
      const botMessage: Message = {
        id: `msg-${Date.now()}-bot`,
        role: "assistant",
        content: data.answer,
        sourceUrl: data.source_url,
        intentType: data.intent_type,
        refusal: data.refusal,
      };
      setMessages((prev) => [...prev, botMessage]);
    } catch (e: any) {
      setError(
        e.message || "Something went wrong while contacting the assistant.",
      );
    } finally {
      setIsSending(false);
    }
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void sendMessage();
    }
  };

  return (
    <div className="chat-shell">
      <div className="chat-card">
        <header className="chat-header">
          <div className="chat-header-main">
            <div className="chat-logo-wrap">
              <img
                className="chat-logo"
                src="https://groww.in/groww-logo-270.png"
                alt="Groww"
                loading="lazy"
              />
            </div>
            <div>
              <div className="chat-title">Groww Mutual Fund Assistant</div>
              <div className="chat-subtitle">
                Factual answers from Groww’s HDFC MF pages
              </div>
            </div>
          </div>
          <div className="chat-status-pill">
            <span className="chat-status-dot" /> Online
          </div>
        </header>

        <div className="chat-body">
          <div className="chat-hint-row">
            <div className="chat-hint-label">Try asking:</div>
            <div className="chat-hint-chips">
              <span className="chat-chip">
                Expense ratio of HDFC Mid Cap Fund
              </span>
              <span className="chat-chip">
                Exit load for HDFC Equity Fund
              </span>
              <span className="chat-chip">Charges for redeeming units</span>
            </div>
          </div>

          <div className="chat-messages">
            {messages.map((m) => (
              <div
                key={m.id}
                className={
                  m.role === "user"
                    ? "msg-row msg-row-user"
                    : "msg-row msg-row-assistant"
                }
              >
                <div
                  className={
                    m.role === "user"
                      ? "msg-bubble msg-bubble-user"
                      : "msg-bubble msg-bubble-assistant"
                  }
                >
                  <div className="msg-content">
                    {m.content.split("\n").map((line, i) => (
                      <p key={i}>{line}</p>
                    ))}
                  </div>
                  {m.role === "assistant" && m.sourceUrl && (
                    <div className="msg-meta">
                      <a
                        href={m.sourceUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="msg-source-link"
                      >
                        View source on Groww
                      </a>
                      {m.intentType && (
                        <span className="msg-intent-pill">
                          {m.intentType.replace(/_/g, " ").toLowerCase()}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {isSending && (
              <div className="msg-row msg-row-assistant">
                <div className="msg-bubble msg-bubble-assistant">
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        <footer className="chat-footer">
          {error && <div className="chat-error">{error}</div>}
          <div className="chat-input-row">
            <textarea
              className="chat-input"
              placeholder="Ask about HDFC mutual fund facts, charges, or definitions…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              rows={2}
            />
            <button
              className="chat-send-btn"
              onClick={() => void sendMessage()}
              disabled={isSending || !input.trim()}
            >
              {isSending ? "Sending..." : "Send"}
            </button>
          </div>
          <div className="chat-footer-note">
            Answers are factual summaries from Groww’s public pages and are{" "}
            <strong>not investment advice</strong>.
          </div>
        </footer>
      </div>
    </div>
  );
};

