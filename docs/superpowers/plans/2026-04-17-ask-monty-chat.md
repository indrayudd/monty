# Ask Monty Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a docs-native conversational query interface ("Ask Monty") to the `/wiki` page — persistent bottom input bar that expands into a right-side chat panel, backed by a streaming LLM endpoint that uses wiki content + behavioral KG as context.

**Architecture:** Backend `POST /api/chat` endpoint reads wiki pages + behavioral nodes from SQLite, builds a context-aware prompt, and streams a response via OpenAI (gpt-5.4-nano). Frontend adds a bottom input bar to the wiki page that expands into a right-side panel replacing the backlinks pane. The LLM distinguishes between general behavioral questions (answered from the anonymized KG) and student-specific questions (answered from student wiki pages).

**Tech Stack:** Python (FastAPI streaming response, OpenAI SDK), Next.js + TypeScript + Tailwind (frontend components).

**Key behavioral rule:** The chat MUST NOT volunteer student-specific information (e.g., "Mira behaved like this...") unless the user asks about a specific student. General questions should be answered from the anonymized behavioral knowledge graph only.

---

## File Structure

### Backend
- Create: `intelligence/api/services/chat_service.py` — context gathering + LLM prompt + streaming
- Modify: `intelligence/api/main.py` — add `POST /api/chat` streaming endpoint

### Frontend
- Create: `backend_visualizer/app/components/WikiChatBar.tsx` — persistent bottom input bar
- Create: `backend_visualizer/app/components/WikiChatPanel.tsx` — right-side conversation panel
- Modify: `backend_visualizer/app/wiki/page.tsx` — integrate chat bar + panel, replace backlinks when panel is open

---

## Task 1: Backend chat service

**Files:**
- Create: `intelligence/api/services/chat_service.py`

- [ ] **Step 1: Write the chat service**

The service should:
1. Accept a question, optional current_page_path, optional selected_text, and conversation history
2. Gather context from the wiki:
   - Read the current page's markdown (if path provided)
   - Search behavioral_nodes for relevant nodes (keyword match on title/summary)
   - If the question mentions a student name, load that student's profile + recent incidents
   - If the question is general (no student name), only use anonymized behavioral KG data
3. Build a system prompt that instructs the LLM:
   - Answer from the wiki/KG context
   - Do NOT mention student names unless the user explicitly asked about a specific student
   - Be informative, direct, technically credible
   - Cite wiki page paths when referencing specific pages
4. Stream the response via OpenAI's streaming API

```python
"""Ask Monty chat service — context-aware conversational query over the wiki."""
from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

from openai import OpenAI

from intelligence.api.services.ghost_client import _conn
from intelligence.api.services.wiki_paths import WIKI_ROOT


STUDENT_NAMES = ["Arjun Nair", "Diya Malhotra", "Kiaan Gupta", "Mira Shah", "Saanvi Verma"]

SYSTEM_PROMPT = """You are Ask Monty, an informative assistant embedded in a Montessori early-childhood behavioral knowledge wiki. You answer questions using the wiki's behavioral knowledge graph and student observation data.

CRITICAL RULES:
1. For GENERAL behavioral questions (e.g., "What triggers emotional outbursts?", "How does self-regulation develop?"), answer ONLY from the anonymized behavioral knowledge graph. Do NOT mention any student by name. Use phrases like "children in the classroom", "a child", "some children".
2. For STUDENT-SPECIFIC questions (e.g., "How is Mira doing?", "Tell me about Arjun's patterns"), you MAY reference that specific student's data.
3. Never volunteer student names unprompted. If the user asks a general question, keep it general.
4. Cite wiki page paths in brackets like [behavioral/antecedents/peer-disruption] when referencing specific knowledge.
5. Be informative, direct, calm, and technically credible. Not overly conversational.
6. If you can't answer from the available context, say so clearly and suggest what wiki pages might help.

You have access to the following context from the wiki:"""


def _openai_client() -> OpenAI | None:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        return None
    return OpenAI(api_key=key)


def _detect_student_query(question: str) -> str | None:
    """Return the student name if the question asks about a specific student."""
    q_lower = question.lower()
    for name in STUDENT_NAMES:
        if name.lower() in q_lower or name.split()[0].lower() in q_lower:
            return name
    return None


def _gather_context(
    question: str,
    current_page_path: str | None = None,
    selected_text: str | None = None,
) -> str:
    """Build context string from wiki content + behavioral KG."""
    parts: list[str] = []

    # 1. Current page content (if provided)
    if current_page_path:
        full_path = WIKI_ROOT / current_page_path
        if full_path.exists() and full_path.is_file():
            content = full_path.read_text(encoding="utf-8")[:3000]
            parts.append(f"## Currently viewing: {current_page_path}\n{content}")

    # 2. Selected text
    if selected_text:
        parts.append(f"## User's selected text:\n{selected_text[:500]}")

    # 3. Check if student-specific
    student = _detect_student_query(question)

    if student:
        # Load student profile + recent incidents
        student_dir = WIKI_ROOT / "students" / student.replace(" ", "_")
        profile = student_dir / "profile.md"
        if profile.exists():
            parts.append(f"## Student profile: {student}\n{profile.read_text(encoding='utf-8')[:2000]}")
        patterns = student_dir / "patterns.md"
        if patterns.exists():
            parts.append(f"## Student patterns: {student}\n{patterns.read_text(encoding='utf-8')[:1500]}")
        # Recent incidents
        incidents_dir = student_dir / "incidents"
        if incidents_dir.exists():
            incident_files = sorted(incidents_dir.glob("*.md"))[-5:]  # last 5
            for f in incident_files:
                parts.append(f"## Incident: {f.name}\n{f.read_text(encoding='utf-8')[:800]}")
    else:
        # General query — use anonymized behavioral KG only
        parts.append("## Behavioral Knowledge Graph (anonymized, no student names)")
        conn = _conn()
        try:
            cur = conn.cursor()
            # Find relevant behavioral nodes by keyword matching
            keywords = [w for w in question.lower().split() if len(w) > 3]
            if keywords:
                like_clauses = " OR ".join(["title LIKE ? OR summary LIKE ?"] * len(keywords))
                params = []
                for kw in keywords:
                    params.extend([f"%{kw}%", f"%{kw}%"])
                cur.execute(
                    f"SELECT slug, type, title, summary, support_count, students_count "
                    f"FROM behavioral_nodes WHERE {like_clauses} "
                    f"ORDER BY support_count DESC LIMIT 15",
                    params,
                )
                rows = cur.fetchall()
                if rows:
                    for r in rows:
                        parts.append(
                            f"- [{r[1]}] {r[2]} (slug: {r[0]}, "
                            f"support: {r[4]}, students: {r[5]})"
                            f"{': ' + r[3] if r[3] else ''}"
                        )

            # Also include the wiki index for navigation help
            index_path = WIKI_ROOT / "index.md"
            if index_path.exists():
                parts.append(f"## Wiki index (for navigation)\n{index_path.read_text(encoding='utf-8')[:2000]}")
        finally:
            conn.close()

    return "\n\n".join(parts)


def stream_chat(
    question: str,
    history: list[dict] | None = None,
    current_page_path: str | None = None,
    selected_text: str | None = None,
) -> Generator[str, None, None]:
    """Stream a chat response. Yields text chunks."""
    client = _openai_client()
    if client is None:
        yield "Ask Monty requires an OpenAI API key. Set OPENAI_API_KEY in your environment."
        return

    context = _gather_context(question, current_page_path, selected_text)

    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + context},
    ]

    # Add conversation history (last 10 turns)
    if history:
        for h in history[-10:]:
            messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})

    messages.append({"role": "user", "content": question})

    try:
        stream = client.chat.completions.create(
            model="gpt-5.4-nano",
            messages=messages,
            temperature=0.3,
            max_tokens=800,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content
    except Exception as e:
        yield f"\n\n_Error: {e}_"
```

- [ ] **Step 2: Syntax check**
```bash
python3 -m py_compile intelligence/api/services/chat_service.py
```

- [ ] **Step 3: Commit**
```bash
git add intelligence/api/services/chat_service.py
git commit -m "feat: add chat_service with wiki/KG context gathering and streaming

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Chat API endpoint

**Files:**
- Modify: `intelligence/api/main.py`

- [ ] **Step 1: Add the streaming chat endpoint**

Add to `main.py`:

```python
from fastapi.responses import StreamingResponse

class ChatRequest(BaseModel):
    question: str
    history: list[dict] | None = None
    current_page_path: str | None = None
    selected_text: str | None = None


@app.post("/api/chat")
def chat(request: ChatRequest):
    from intelligence.api.services.chat_service import stream_chat

    def generate():
        for chunk in stream_chat(
            question=request.question,
            history=request.history,
            current_page_path=request.current_page_path,
            selected_text=request.selected_text,
        ):
            yield chunk

    return StreamingResponse(generate(), media_type="text/plain")
```

- [ ] **Step 2: Syntax check + quick test**
```bash
python3 -m py_compile intelligence/api/main.py
# With API running:
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What behavioral patterns are most common?"}' \
  --no-buffer
```

- [ ] **Step 3: Commit**
```bash
git commit intelligence/api/main.py -m "feat: add POST /api/chat streaming endpoint

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: WikiChatBar component (persistent bottom input)

**Files:**
- Create: `backend_visualizer/app/components/WikiChatBar.tsx`

- [ ] **Step 1: Write the component**

A persistent bottom bar pinned to the wiki page. Multiline input with "Ask Monty" placeholder and a send button. When the user submits, it calls `onSubmit(question)` which the parent uses to open the panel.

```tsx
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
            Using selection: {selectedText.slice(0, 60)}{selectedText.length > 60 ? "…" : ""}
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
```

- [ ] **Step 2: Build**
```bash
cd backend_visualizer && npm run build
```

- [ ] **Step 3: Commit**

---

## Task 4: WikiChatPanel component (right-side conversation)

**Files:**
- Create: `backend_visualizer/app/components/WikiChatPanel.tsx`

- [ ] **Step 1: Write the component**

Right-side panel that shows the conversation thread. Messages stream in. Input stays anchored at bottom. Close button (×) to collapse back to backlinks view.

The panel calls `POST /api/chat` with the question, current page path, selected text, and conversation history. It reads the streaming response and appends chunks to the current assistant message.

```tsx
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
}: {
  currentPagePath: string | null;
  onClose: () => void;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [selectedText, setSelectedText] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

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

  const submit = async (question?: string) => {
    const q = (question || input).trim();
    if (!q || streaming) return;
    setInput("");
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
          selected_text: selectedText,
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
  };

  return (
    <aside className="w-[380px] shrink-0 border-l border-white/10 bg-zinc-950 flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-white/10">
        <span className="text-xs font-mono text-white/50">Ask Monty</span>
        <button onClick={onClose} className="text-white/30 hover:text-white text-xs">✕</button>
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
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content || "…"}</ReactMarkdown>
              </div>
            )}
          </div>
        ))}
        {streaming && (
          <div className="text-[10px] text-white/30 font-mono">streaming…</div>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-white/10 p-2">
        {selectedText && (
          <div className="mb-1 flex items-center gap-1">
            <span className="text-[9px] font-mono bg-white/5 border border-white/10 rounded px-1.5 py-0.5 text-white/40 truncate max-w-[280px]">
              Using selection: {selectedText.slice(0, 50)}{selectedText.length > 50 ? "…" : ""}
            </span>
            <button onClick={() => setSelectedText(null)} className="text-white/30 text-[9px]">✕</button>
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
```

- [ ] **Step 2: Build**
- [ ] **Step 3: Commit**

---

## Task 5: Integrate chat into wiki page

**Files:**
- Modify: `backend_visualizer/app/wiki/page.tsx`

- [ ] **Step 1: Add state for chat panel visibility**

The wiki page needs:
- `chatOpen` state (boolean) — when true, replace the WikiBacklinks pane with WikiChatPanel
- A persistent bottom bar (WikiChatBar) that, when the user submits, sets `chatOpen = true` and sends the question to the panel
- Pass `currentPagePath` (the currently viewed wiki page path) to the chat panel

When `chatOpen` is false: show the normal three-pane layout (FileTree | Renderer | Backlinks).
When `chatOpen` is true: show FileTree | Renderer | ChatPanel (backlinks hidden).

The bottom WikiChatBar is replaced by the panel's own input when the panel is open.

- [ ] **Step 2: Build**
```bash
cd backend_visualizer && npm run build
```

- [ ] **Step 3: Commit**

---

## Validation

After all tasks:
1. `python3 -m py_compile intelligence/api/services/chat_service.py intelligence/api/main.py`
2. `cd backend_visualizer && npm run build`
3. Open `/wiki`, verify bottom bar is visible, type a question, verify panel opens with streaming response.
4. Test general question: "What behavioral patterns are most common?" — response should NOT mention any student by name.
5. Test student question: "How is Mira doing?" — response should reference Mira's data specifically.
