"use client";
import { useState, useCallback } from "react";
import Link from "next/link";
import { WikiFileTree } from "../components/WikiFileTree";
import { WikiPageRenderer } from "../components/WikiPageRenderer";
import { WikiBacklinks } from "../components/WikiBacklinks";
import { WikiChatBar } from "../components/WikiChatBar";
import { WikiChatPanel } from "../components/WikiChatPanel";

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

  // Track text selection from the wiki renderer area
  const handleSelectionCapture = useCallback(() => {
    const sel = window.getSelection()?.toString()?.trim();
    if (sel && sel.length > 0) {
      setSelectedText(sel);
    }
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
          />
        ) : (
          <WikiBacklinks path={path} />
        )}
      </div>

      {/* Bottom bar: chat input when panel is closed, nav footer always */}
      {!chatOpen && (
        <WikiChatBar onSubmit={handleChatSubmit} selectedText={selectedText} />
      )}
      <footer className="shrink-0 flex items-center justify-between px-3 py-1.5 border-t border-white/10 bg-zinc-950">
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

        {/* Action buttons */}
        <div className="flex items-center gap-1">
          {ACTION_BUTTONS.map((label) => (
            <button
              key={label}
              className="text-[10px] px-2.5 py-1 rounded-full font-mono bg-white/5 text-white/50 hover:text-white hover:bg-white/10 transition-colors"
            >
              {label}
            </button>
          ))}
        </div>
      </footer>
    </div>
  );
}
