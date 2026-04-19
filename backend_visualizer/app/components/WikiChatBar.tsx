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
  const inputRef = useRef<HTMLInputElement>(null);

  const submit = () => {
    const q = value.trim();
    if (!q) return;
    onSubmit(q, selectedText || undefined);
    setValue("");
  };

  return (
    <div className="flex items-center gap-1.5 flex-1 mr-2">
      {selectedText && (
        <span className="text-[8px] font-mono bg-white/5 border border-white/10 rounded px-1.5 py-0.5 text-white/40 truncate max-w-[160px] shrink-0">
          Selection: {selectedText.slice(0, 30)}{selectedText.length > 30 ? "\u2026" : ""}
        </span>
      )}
      <input
        ref={inputRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            submit();
          }
        }}
        placeholder="Ask Monty"
        className="flex-1 bg-zinc-900 border border-white/10 rounded px-2.5 py-1 text-[11px] text-white placeholder-white/30 focus:outline-none focus:border-white/30 font-mono min-w-[120px]"
      />
      <button
        onClick={submit}
        disabled={!value.trim()}
        className="px-1.5 py-1 rounded bg-white/10 hover:bg-white/20 text-white/60 text-[10px] disabled:opacity-30 transition-colors"
      >
        ↑
      </button>
    </div>
  );
}
