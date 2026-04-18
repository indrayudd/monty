"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Message = {
  role: "user" | "assistant";
  content: string;
};

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export function WikiChatPanel({
  currentPagePath,
  onClose,
  initialQuestion,
  initialSelectedText,
}: {
  currentPagePath: string | null;
  onClose: () => void;
  initialQuestion?: string;
  initialSelectedText?: string;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [selectedText, setSelectedText] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const didSendInitial = useRef(false);

  // Capture text selection when user focuses the input
  const handleInputFocus = useCallback(() => {
    const sel = window.getSelection()?.toString()?.trim();
    if (sel && sel.length > 0) {
      setSelectedText(sel);
    }
  }, []);

  // Auto-scroll on new content
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
      inputRef.current.style.height = Math.min(inputRef.current.scrollHeight, 100) + "px";
    }
  }, [input]);

  const submit = useCallback(async (question?: string, selText?: string) => {
    const q = (question || input).trim();
    if (!q || streaming) return;
    setInput("");
    const usedSelection = selText ?? selectedText;
    setSelectedText(null);

    const userMsg: Message = { role: "user", content: q };
    const assistantMsg: Message = { role: "assistant", content: "" };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setStreaming(true);

    try {
      const resp = await fetch(`${BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: q,
          history: messages.slice(-10).map((m) => ({ role: m.role, content: m.content })),
          current_page_path: currentPagePath,
          selected_text: usedSelection,
        }),
      });

      if (!resp.ok || !resp.body) {
        setMessages((prev) => {
          const next = [...prev];
          next[next.length - 1] = { role: "assistant", content: "_Error: could not reach Ask Monty._" };
          return next;
        });
        setStreaming(false);
        return;
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let accumulated = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        accumulated += decoder.decode(value, { stream: true });
        const content = accumulated;
        setMessages((prev) => {
          const next = [...prev];
          next[next.length - 1] = { role: "assistant", content };
          return next;
        });
      }
    } catch (e) {
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = { role: "assistant", content: `_Error: ${e}_` };
        return next;
      });
    } finally {
      setStreaming(false);
    }
  }, [input, streaming, selectedText, messages, currentPagePath]);

  // Send initial question on mount (once)
  useEffect(() => {
    if (initialQuestion && !didSendInitial.current) {
      didSendInitial.current = true;
      submit(initialQuestion, initialSelectedText);
    }
  }, [initialQuestion, initialSelectedText, submit]);

  return (
    <aside className="w-[380px] shrink-0 border-l border-white/10 bg-zinc-950 flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-white/10">
        <span className="text-xs font-mono text-white/50">Ask Monty</span>
        <button onClick={onClose} className="text-white/30 hover:text-white text-xs">&#x2715;</button>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.length === 0 && (
          <div className="text-center text-white/25 text-xs font-mono mt-8">
            Ask a question about the wiki
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`text-sm ${m.role === "user" ? "text-right" : ""}`}>
            {m.role === "user" ? (
              <div className="inline-block bg-white/10 rounded-lg px-3 py-2 text-white/90 text-left max-w-[90%]">
                {m.content}
              </div>
            ) : (
              <div className="prose prose-invert prose-sm max-w-none text-white/80">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content || "\u2026"}</ReactMarkdown>
              </div>
            )}
          </div>
        ))}
        {streaming && (
          <div className="text-[10px] text-white/30 font-mono">streaming...</div>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-white/10 p-2">
        {selectedText && (
          <div className="mb-1 flex items-center gap-1">
            <span className="text-[9px] font-mono bg-white/5 border border-white/10 rounded px-1.5 py-0.5 text-white/40 truncate max-w-[280px]">
              Using selection: {selectedText.slice(0, 50)}{selectedText.length > 50 ? "\u2026" : ""}
            </span>
            <button onClick={() => setSelectedText(null)} className="text-white/30 text-[9px]">&#x2715;</button>
          </div>
        )}
        <div className="flex items-end gap-1">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onFocus={handleInputFocus}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            placeholder="Ask Monty"
            rows={1}
            disabled={streaming}
            className="flex-1 bg-zinc-900 border border-white/10 rounded px-2 py-1.5 text-xs text-white placeholder-white/30 resize-none focus:outline-none focus:border-white/30 font-mono disabled:opacity-50"
          />
          <button
            onClick={() => submit()}
            disabled={!input.trim() || streaming}
            className="px-2 py-1.5 rounded bg-white/10 hover:bg-white/20 text-white/60 text-xs disabled:opacity-30"
          >
            ↑
          </button>
        </div>
      </div>
    </aside>
  );
}
