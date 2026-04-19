"use client";
import { useState, useCallback, useEffect } from "react";
import Link from "next/link";
import { WikiFileTree } from "../components/WikiFileTree";
import { WikiPageRenderer } from "../components/WikiPageRenderer";
import { WikiBacklinks } from "../components/WikiBacklinks";
import { WikiChatBar } from "../components/WikiChatBar";
import { WikiChatPanel, type ChatMessage } from "../components/WikiChatPanel";

const NAV_TABS = [
  { label: "Live", href: "/" },
  { label: "Wiki", href: "/wiki" },
  { label: "Console", href: "/console" },
  { label: "God Mode", href: "/god-mode" },
];

const ACTION_BUTTONS = ["Raw markdown", "Backlinks", "Graph view"];

export default function WikiPage() {
  const [path, setPath] = useState<string | null>("index.md");
  const [chatOpen, setChatOpen] = useState(false);
  const [selectedText, setSelectedText] = useState<string | null>(null);
  const [pendingQuestion, setPendingQuestion] = useState<string | undefined>();
  const [pendingSelection, setPendingSelection] = useState<string | undefined>();
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  // Track text selection from the wiki renderer area
  const handleSelectionCapture = useCallback(() => {
    const sel = window.getSelection()?.toString()?.trim();
    if (sel && sel.length > 0) {
      setSelectedText(sel);
    }
  }, []);

  // Clear selection pill when user deselects text
  useEffect(() => {
    const onSelectionChange = () => {
      const sel = window.getSelection()?.toString()?.trim();
      if (!sel) setSelectedText(null);
    };
    document.addEventListener("selectionchange", onSelectionChange);
    return () => document.removeEventListener("selectionchange", onSelectionChange);
  }, []);

  // When the bottom bar submits, open the panel with the question
  const handleChatSubmit = useCallback((question: string, selText?: string) => {
    setPendingQuestion(question);
    setPendingSelection(selText);
    setChatOpen(true);
    setSelectedText(null);
  }, []);

  const handleChatClose = useCallback(() => {
    setChatOpen(false);
    setPendingQuestion(undefined);
    setPendingSelection(undefined);
  }, []);

  const handleClearChat = useCallback(() => {
    setMessages([]);
  }, []);

  return (
    <div className="h-[calc(100vh-3rem)] flex flex-col">
      {/* Main pane area */}
      <div className="flex flex-1 min-h-0" onMouseUp={handleSelectionCapture}>
        <WikiFileTree selected={path} onSelect={setPath} />
        <WikiPageRenderer path={path} onNavigate={setPath} />
        {chatOpen ? (
          <WikiChatPanel
            currentPagePath={path}
            onClose={handleChatClose}
            initialQuestion={pendingQuestion}
            initialSelectedText={pendingSelection}
            messages={messages}
            setMessages={setMessages}
            onClear={handleClearChat}
          />
        ) : (
          <WikiBacklinks path={path} />
        )}
      </div>

      {/* Bottom bar: chat input when panel is closed, nav footer always */}
      <div className="shrink-0 flex items-center justify-between px-3 py-1.5 border-t border-white/10 bg-zinc-950">
        {/* Route tabs */}
        <div className="flex items-center gap-1">
          {NAV_TABS.map(({ label, href }) => {
            const isActive = label === "Wiki";
            return (
              <Link
                key={label}
                href={href}
                className={`text-[10px] px-2.5 py-1 rounded-full font-mono transition-colors ${
                  isActive
                    ? "bg-violet-600 text-white"
                    : "bg-white/5 text-white/50 hover:text-white hover:bg-white/10"
                }`}
              >
                {label}
              </Link>
            );
          })}
        </div>

        {/* Action buttons + chat toggle */}
        <div className="flex items-center gap-1">
          {!chatOpen && (
            <WikiChatBar onSubmit={handleChatSubmit} selectedText={selectedText} />
          )}
          <button
            onClick={() => {
              if (chatOpen) {
                handleChatClose();
              } else {
                setChatOpen(true);
              }
            }}
            className={`text-[10px] px-2.5 py-1 rounded-full font-mono transition-colors flex items-center gap-1 ${
              chatOpen
                ? "bg-violet-600/30 text-violet-300 border border-violet-500/30"
                : messages.length > 0
                  ? "bg-violet-600/20 text-violet-300 hover:bg-violet-600/30"
                  : "bg-white/5 text-white/50 hover:text-white hover:bg-white/10"
            }`}
            title={chatOpen ? "Close chat" : "Open Ask Monty"}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
            {messages.length > 0 && (
              <span className="text-[8px] opacity-60">{messages.filter(m => m.role === "user").length}</span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
