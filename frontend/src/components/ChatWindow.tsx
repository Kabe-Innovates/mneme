import { useState, useRef, useEffect } from "react";
import { Send, Loader2 } from "lucide-react";
import { sendMessage } from "../api";
import { MessageBubble } from "./MessageBubble";
import type { Message } from "../types";
import { clsx } from "clsx";

const WELCOME_MESSAGE: Message = {
  id: "welcome",
  role: "assistant",
  content:
    "Hello! I'm **Mneme**, your healthcare operations assistant. I can help you:\n\n" +
    "• Answer questions about hospital policies and procedures\n" +
    "• Guide you through step-by-step operational workflows\n" +
    "• Route requests that require human review to the right team\n\n" +
    "Select your role in the sidebar and ask me anything about hospital operations.",
  timestamp: new Date(),
};

const SUGGESTIONS = [
  "What is the visitor policy for ICU patients?",
  "Patient has MRI tomorrow, insurance authorization is pending",
  "I need to process a billing correction of $2000",
  "How do I request medical records release?",
];

interface Props {
  role: string;
  sessionId: string;
}

export function ChatWindow({ role, sessionId }: Props) {
  const [messages, setMessages] = useState<Message[]>([WELCOME_MESSAGE]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (text?: string) => {
    const query = (text || input).trim();
    if (!query || loading) return;

    setInput("");
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

  return (
    <div className="flex h-full flex-col">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 scrollbar-thin">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} sessionId={sessionId} />
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="flex items-center gap-2 rounded-2xl rounded-tl-sm bg-white px-4 py-3 shadow-sm ring-1 ring-slate-100">
              <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
              <span className="text-sm text-slate-500">Mneme is thinking...</span>
            </div>
          </div>
        )}

        {error && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Suggestions (show only at start) */}
      {messages.length === 1 && !loading && (
        <div className="px-4 pb-3">
          <p className="mb-2 text-xs font-medium text-slate-400">Try asking:</p>
          <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => handleSend(s)}
                className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 transition-colors"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="border-t border-slate-100 bg-white px-4 py-3">
        <div className="flex items-end gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 focus-within:border-blue-400 focus-within:ring-1 focus-within:ring-blue-400">
          <textarea
            ref={inputRef}
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Ask a question as ${role}...`}
            className="flex-1 resize-none bg-transparent text-sm text-slate-700 placeholder-slate-400 focus:outline-none"
            style={{ maxHeight: "120px" }}
          />
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || loading}
            className={clsx(
              "shrink-0 rounded-lg p-1.5 transition-colors",
              input.trim() && !loading
                ? "bg-blue-600 text-white hover:bg-blue-700"
                : "bg-slate-200 text-slate-400 cursor-not-allowed"
            )}
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </button>
        </div>
        <p className="mt-1 text-center text-xs text-slate-400">
          Mneme provides operational guidance only. Not a substitute for medical judgment.
        </p>
      </div>
    </div>
  );
}
