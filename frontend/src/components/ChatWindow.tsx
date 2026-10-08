import { useState, useRef, useEffect } from "react";
import { Send, Loader2 } from "lucide-react";
import { sendMessage } from "../api";
import { MessageBubble } from "./MessageBubble";
import type { Message } from "../types";
import { clsx } from "clsx";


interface Props {
  username: string;
  role: string;
  sessionId: string;
  onViewQueue?: () => void;
}

export function ChatWindow({ username, role, sessionId, onViewQueue }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const isLanding = messages.length === 0 && !loading;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px";
  };

  const handleSend = async (text?: string) => {
    const query = (text || input).trim();
    if (!query || loading) return;

    setInput("");
    if (inputRef.current) inputRef.current.style.height = "auto";
    setError(null);

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: query,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const res = await sendMessage(query, role, sessionId);
      const assistantMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: res.message,
        response: res,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reach Mneme server. Ensure the backend is running.");
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const CapsuleBar = ({ centered }: { centered?: boolean }) => (
    <div className={clsx(centered ? "w-full max-w-2xl" : "w-full max-w-3xl", "mx-auto")}>
      <div className="flex items-end gap-3 rounded-full bg-dark-surface px-5 py-3 shadow-lg ring-1 ring-dark-border focus-within:ring-brand-600 transition-all">
        <textarea
          ref={inputRef}
          rows={1}
          value={input}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder={`Ask anything as ${role}…`}
          className="flex-1 resize-none bg-transparent text-sm text-dark-text placeholder-dark-muted focus:outline-none"
          style={{ maxHeight: "120px", overflowY: "hidden" }}
        />
        <button
          onClick={() => handleSend()}
          disabled={!input.trim() || loading}
          className={clsx(
            "shrink-0 rounded-full p-2 transition-colors",
            input.trim() && !loading
              ? "bg-brand-600 text-white hover:bg-brand-700"
              : "bg-dark-hover text-dark-muted cursor-not-allowed"
          )}
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </button>
      </div>
    </div>
  );

  if (isLanding) {
    return (
      <div className="flex h-full flex-col items-center justify-center gradient-aura px-4 font-sans">
        {/* Greeting */}
        <h1 className="font-display mb-3 text-center text-4xl sm:text-5xl font-semibold tracking-tight text-dark-text">
          Hi <span className="bg-gradient-to-r from-brand-300 to-brand-500 bg-clip-text text-transparent">{username}</span>, how can I help?
        </h1>
        <p className="font-sans mb-10 text-center text-xs uppercase tracking-[0.22em] text-dark-muted font-medium">
          Deterministic Second Brain for Hospital Operations
        </p>

        {/* Capsule prompt */}
        <div className="w-full flex justify-center">
          <CapsuleBar centered />
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Messages */}
      <div className="chat-bg flex-1 overflow-y-auto scrollbar-thin">
        <div className="mx-auto max-w-3xl space-y-4 px-4 py-4">
          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} sessionId={sessionId} onViewQueue={onViewQueue} />
          ))}

          {loading && (
            <div className="flex animate-message-in justify-start">
              <div className="max-w-[60%] space-y-2 rounded-2xl rounded-tl-sm bg-dark-surface px-4 py-3 ring-1 ring-dark-border">
                <div className="h-2.5 w-3/4 animate-pulse rounded-full bg-dark-hover" />
                <div className="h-2.5 w-1/2 animate-pulse rounded-full bg-dark-hover" />
                <div className="flex items-center gap-2 pt-1">
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-brand-500" />
                  <span className="text-xs text-dark-muted">Analyzing your request…</span>
                </div>
              </div>
            </div>
          )}

          {error && (
            <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
              {error}
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      {/* Bottom capsule bar */}
      <div className="border-t border-dark-border bg-dark-bg px-4 py-3">
        <CapsuleBar />
        <p className="mt-2 text-center text-xs text-dark-muted/60">
          Mneme provides operational guidance only. Not a substitute for medical judgment.
        </p>
      </div>
    </div>
  );
}
