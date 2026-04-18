"use client";
import { useState, useRef, useEffect } from "react";

export function WikiChatBar({
  onSubmit,
  selectedText,
}: {
  onSubmit: (question: string, selectedText?: string) => void;
  selectedText: string | null;
}) {
  const [value, setValue] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
      inputRef.current.style.height = Math.min(inputRef.current.scrollHeight, 120) + "px";
    }
  }, [value]);

  const submit = () => {
    const q = value.trim();
    if (!q) return;
    onSubmit(q, selectedText || undefined);
    setValue("");
  };

  return (
    <div className="border-t border-white/10 bg-zinc-950 px-4 py-2">
      {selectedText && (
        <div className="mb-1 flex items-center gap-2">
          <span className="text-[9px] font-mono bg-white/5 border border-white/10 rounded px-2 py-0.5 text-white/50 truncate max-w-[300px]">
            Using selection: {selectedText.slice(0, 60)}{selectedText.length > 60 ? "\u2026" : ""}
          </span>
        </div>
      )}
      <div className="flex items-end gap-2">
        <textarea
          ref={inputRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          placeholder="Ask Monty"
          rows={1}
          className="flex-1 bg-zinc-900 border border-white/10 rounded px-3 py-2 text-sm text-white placeholder-white/30 resize-none focus:outline-none focus:border-white/30 font-mono"
        />
        <button
          onClick={submit}
          disabled={!value.trim()}
          className="px-3 py-2 rounded bg-white/10 hover:bg-white/20 text-white/70 text-sm disabled:opacity-30 transition-colors"
        >
          ↑
        </button>
      </div>
    </div>
  );
}
