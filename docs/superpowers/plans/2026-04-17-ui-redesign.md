# UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the backend visualizer to match the 5 frames in `screens.pen` — Live page with two-column top zone + Live Ops Column, God Mode as a full-page route, Console with structured trace log + KPI cards, Wiki with search/GRAPH LINKS/bottom bar.

**Architecture:** 4 independent workstreams touching disjoint component files. BehavioralKGPanel and StudentGraphPanel are **preserved as-is** (physics tuning, node identity, structural-diff-only reheating). Layout wrappers and new components change; graph internals don't.

**Tech Stack:** Next.js 16 + TypeScript + Tailwind CSS v4 + react-force-graph-2d (existing) + react-markdown (existing).

**Critical constraint:** Do NOT modify `BehavioralKGPanel.tsx` or `StudentGraphPanel.tsx` graph internals (physics, nodeObjRef, structural-diff logic, canvas rendering). Only their parent containers change size/position.

---

## Workstream A: Live page restructure

### Task A1: Create LiveOpsColumn component

**Files:**
- Create: `backend_visualizer/app/components/LiveOpsColumn.tsx`

- [ ] **Step 1: Write the component**

```tsx
"use client";
import { useEffect, useState } from "react";
import { api } from "../lib/api";

export function LiveOpsColumn() {
  const [status, setStatus] = useState<Record<string, string>>({});
  const [events, setEvents] = useState<any[]>([]);

  useEffect(() => {
    const tick = async () => {
      try {
        const [overview, curiosity] = await Promise.all([
          api.demoOverview() as Promise<{ runtime?: Record<string, string> }>,
          api.curiosityEvents(5),
        ]);
        setStatus(overview?.runtime || {});
        setEvents(curiosity?.events || []);
      } catch {}
    };
    tick();
    const i = setInterval(tick, 1500);
    return () => clearInterval(i);
  }, []);

  const stage = status.current_stage || "idle";
  const student = status.current_student || "—";

  return (
    <div className="w-[332px] shrink-0 rounded bg-zinc-900/80 border border-white/10 p-3 flex flex-col gap-4 overflow-y-auto">
      {/* CYCLE STAGE */}
      <section>
        <h3 className="text-[10px] font-mono text-white/50 uppercase tracking-wider mb-2">Cycle Stage</h3>
        <div className="text-sm font-semibold text-white">{stage.replace(/_/g, " ")}</div>
        <div className="text-xs text-white/60 mt-1">&gt; {student}</div>
        <div className="flex flex-wrap gap-1 mt-2">
          {["reassessing", "will_enrich", "generating_alert", "reset", "explore", "student", "notes"].map(k => (
            <span key={k} className={`text-[9px] px-1.5 py-0.5 rounded font-mono ${
              stage.includes(k) ? "bg-emerald-500/20 text-emerald-300" : "bg-white/5 text-white/30"
            }`}>{k}</span>
          ))}
        </div>
      </section>

      {/* STUDENT FOCUS */}
      <section>
        <h3 className="text-[10px] font-mono text-white/50 uppercase tracking-wider mb-2">Student Focus</h3>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
          <span className="text-sm text-white font-medium">{student}</span>
        </div>
      </section>

      {/* RESEARCH QUEUE */}
      <section>
        <h3 className="text-[10px] font-mono text-white/50 uppercase tracking-wider mb-2">Research Queue</h3>
        {events.length === 0 && (
          <div className="text-[10px] text-white/30 font-mono">no research queued</div>
        )}
        {events.map((ev, i) => (
          <div key={ev.id || i} className="flex items-center justify-between text-[10px] font-mono py-1 border-b border-white/5 last:border-0">
            <span className="text-white/70 truncate max-w-[200px]">{ev.node_slug}</span>
            <span className={`px-1.5 py-0.5 rounded ${
              ev.triggered_research ? "bg-emerald-500/20 text-emerald-300" : "bg-white/5 text-white/40"
            }`}>
              {ev.curiosity_score?.toFixed(2) || "—"}
            </span>
          </div>
        ))}
      </section>
    </div>
  );
}
```

- [ ] **Step 2: Verify build**
```bash
cd backend_visualizer && npm run build
```

- [ ] **Step 3: Commit**
```bash
git add backend_visualizer/app/components/LiveOpsColumn.tsx
git commit -m "redesign: add LiveOpsColumn (cycle stage, student focus, research queue)

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

### Task A2: Restructure Live page layout (two-column top zone)

**Files:**
- Modify: `backend_visualizer/app/page.tsx`

- [ ] **Step 1: Update page.tsx**

Replace the body of `LivePage` to use a two-column top zone:

```tsx
"use client";
import { useState } from "react";
import { BehavioralKGPanel } from "./components/BehavioralKGPanel";
import { LiveOpsColumn } from "./components/LiveOpsColumn";
import { StageRail } from "./components/StageRail";
import { StudentTimeline } from "./components/StudentTimeline";
import { IncidentDrawer } from "./components/IncidentDrawer";
import type { StudentIncident } from "./lib/api";

export default function LivePage() {
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [openIncident, setOpenIncident] = useState<StudentIncident | null>(null);

  return (
    <div className="h-[calc(100vh-3rem)] flex flex-col gap-1.5 p-1.5">
      {/* Top Zone: two columns */}
      <div className="flex gap-1.5" style={{ height: 540 }}>
        <div className="flex-1 min-w-0 rounded overflow-hidden">
          <BehavioralKGPanel selectedSlug={selectedSlug} onSelectNode={setSelectedSlug} />
        </div>
        <LiveOpsColumn />
      </div>
      {/* Stage Rail */}
      <StageRail />
      {/* Bottom Zone */}
      <div className="flex-1 min-h-0">
        <StudentTimeline
          highlightSlug={selectedSlug}
          onOpenIncident={setOpenIncident}
          onSelectBehavioralNode={setSelectedSlug}
        />
      </div>
      <IncidentDrawer
        incident={openIncident}
        onClose={() => setOpenIncident(null)}
        onSelectBehavioralNode={setSelectedSlug}
      />
    </div>
  );
}
```

- [ ] **Step 2: Remove the old floating God Mode button from page.tsx** (God Mode is now a route, not an overlay). Remove the `<GodModePanel />` import and JSX.

- [ ] **Step 3: Verify build**
```bash
cd backend_visualizer && npm run build
```

- [ ] **Step 4: Commit**
```bash
git commit backend_visualizer/app/page.tsx -m "redesign: two-column Live layout with LiveOpsColumn sidebar

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

### Task A3: Redesign incident cards with colored left border

**Files:**
- Modify: `backend_visualizer/app/components/StudentTimeline.tsx`

- [ ] **Step 1: Update the incident card JSX** inside the timeline `.map()`. Replace the existing card with:

Each card should have:
- A 4px left border colored by severity (red/yellow/green).
- A **title** line (bold, white, 12px) — show the note slug or a short summary.
- A **description** (muted, 11px, 2-3 lines, overflow hidden).
- Behavioral type chips at bottom.
- Remove the old severity dot in the corner (the left border replaces it).

Severity border colors: `border-l-rose-500` (red), `border-l-amber-400` (yellow), `border-l-emerald-500` (green).

- [ ] **Step 2: Verify build + commit**

### Task A4: Narrow the IncidentDrawer to 280px + type-colored pills

**Files:**
- Modify: `backend_visualizer/app/components/IncidentDrawer.tsx`

- [ ] **Step 1: Change drawer width** from `w-[720px]` to `w-[280px]`.

- [ ] **Step 2: Update behavioral node pills** to use type-specific colors instead of uniform white/10. Use the same `TYPE_COLORS` mapping from BehavioralKGPanel (import or duplicate the palette).

- [ ] **Step 3: Verify build + commit**

### Task A5: Update TopAppBar nav to include God Mode route link

**Files:**
- Modify: `backend_visualizer/app/components/TopAppBar.tsx`

- [ ] **Step 1: Add "God Mode" link** to the nav alongside Live/Wiki/Console. Style it with gold text (`text-amber-400`) when active.

- [ ] **Step 2: Change branding** from "monty" to "MONTY OPS" (uppercase, Inter 14px bold).

- [ ] **Step 3: Add UTC clock** to the right zone (formatted as HH:MM:SS UTC, updated every second).

- [ ] **Step 4: Verify build + commit**

---

## Workstream B: God Mode full-page route

### Task B1: Create `/god-mode/page.tsx` with two-column layout

**Files:**
- Create: `backend_visualizer/app/god-mode/page.tsx`
- Create: `backend_visualizer/app/components/GodModeLiveFeed.tsx`

Move the persona cards, presets, curiosity tuning, manual research, and demo lifecycle from the old `GodModePanel.tsx` slide-in into a full-page two-column layout.

**Left column (480px):** God Mode Controls — header ("God Mode Control" + active count + LIVE badge), story presets, 5 persona cards.

**Right column (fill):** Context Panel — live event feed (monospace scrollable), curiosity weight sliders, manual research trigger, demo lifecycle buttons.

- [ ] **Step 1: Create `GodModeLiveFeed.tsx`** — a scrollable monospace div that polls a new endpoint or `/api/agent/status` for recent actions and renders them as color-coded log lines.

- [ ] **Step 2: Create `god-mode/page.tsx`** composing left/right columns with existing components (`PersonaCard`, `StoryPresetRow`, `CuriosityTuning`, `ManualResearchTrigger`) + new `GodModeLiveFeed`.

- [ ] **Step 3: Verify build + commit**

---

## Workstream C: Console redesign

### Task C1: Create KPI status cards + structured trace log

**Files:**
- Modify: `backend_visualizer/app/console/page.tsx`
- Create: `backend_visualizer/app/components/TraceLog.tsx`
- Create: `backend_visualizer/app/components/StatusCards.tsx`

- [ ] **Step 1: Create `StatusCards.tsx`** — 3 horizontal cards (cycle state, graph state, throughput) with colored left borders. Data from `/api/agent/status` + `/api/behavioral-graph` counts.

- [ ] **Step 2: Create `TraceLog.tsx`** — monospace scrollable log with color-coded rows by category. Category filter chips at top (all/assessment/graph/curiosity/research). For now, this can render from `agent_actions` or just display the raw agent status updates. The visual style should match the Pencil frame (JetBrains Mono 11px, category-colored text).

- [ ] **Step 3: Rewrite `console/page.tsx`** to compose StatusCards + TraceLog + existing CuriosityEventsStream. Add bottom bar with route nav + filter input.

- [ ] **Step 4: Verify build + commit**

---

## Workstream D: Wiki polish

### Task D1: Add search bar, GRAPH LINKS header, bottom bar

**Files:**
- Modify: `backend_visualizer/app/wiki/page.tsx`
- Modify: `backend_visualizer/app/components/WikiBacklinks.tsx`
- Modify: `backend_visualizer/app/components/WikiFileTree.tsx`

- [ ] **Step 1: Left pane** — add "FILES" header (10px, uppercase, tracking-wider). Width from 240px to 300px.

- [ ] **Step 2: Right pane** — rename header from "Linked from" to "GRAPH LINKS" (same style as FILES). Add "Outgoing" and "Legend" sections below backlinks. Width from 280px to 320px.

- [ ] **Step 3: Bottom bar** — add a fixed footer with route tabs (Live/Wiki/Console/God Mode) + action buttons (Raw markdown, Backlinks, Graph view).

- [ ] **Step 4: Verify build + commit**

---

## Validation

After all 4 workstreams complete:

```bash
cd backend_visualizer && npm run build
```

All 5 routes must compile: `/`, `/wiki`, `/console`, `/god-mode`, `/_not-found`.

Manual check: open each route in browser, verify layout matches `screens.pen` frames.
