# Backend Visualizer Cleanup Plan

## Goal

Make the `backend_visualizer` behave like a deterministic live demo:

1. It should open in a clean pre-run state.
2. Starting the demo should visibly show note ingestion, reassessment, KG enrichment, and escalation as they happen.
3. Student graph filtering should be stable and should not fight the operator.

No implementation is included here yet. This is the execution plan for the approved cleanup pass.

---

## What I Investigated

### Frontend surface in use

The bugs you described match `backend_visualizer/app/page.tsx`, not the older `frontend/` dashboard.

### Relevant files

- `backend_visualizer/app/page.tsx`
- `backend_visualizer/app/globals.css`
- `intelligence/api/main.py`
- `intelligence/api/services/demo_runtime.py`
- `intelligence/api/services/self_improve.py`
- `intelligence/api/services/ghost_client.py`
- `agents/server.py`

---

## Findings

### 1. "Live Workflow" is not actually driven by live stage state

Current behavior:

- The UI renders a "Live Workflow" rail in `backend_visualizer/app/page.tsx`.
- That rail is inferred from the latest completed actions only:
  - `note_ingested`
  - `agent_cycle`
  - `cycle_summary`
- There is no backend concept of "current stage", "stage started", "stage completed", or "agent currently working on student X / note Y".
- As a result, the UI can only show the last known completed event, not the actual live step the agent is currently in.

Code evidence:

- `backend_visualizer/app/page.tsx:233-289` derives workflow steps from `latestAction(...)`.
- `intelligence/api/services/demo_runtime.py:84-97` only logs a coarse `cycle_summary`.
- `intelligence/api/services/self_improve.py:152-298` logs a single `agent_cycle` action after the work is already done.

Impact:

- The step rail is mostly a retrospective summary, not a live execution visualizer.
- Fast sub-steps can be missed entirely between 1s polls.
- Multiple steps can appear equally "active" because they share the same latest action timestamp.

### 2. "All students" in the Knowledge Graph does not persist

Current behavior:

- The Knowledge Graph owns its own `filter` state.
- But it also force-syncs that state back to the global `selectedStudent`.
- Because the page polls every second and the `nodes` array is refreshed every poll, that effect keeps re-running and re-applies the student filter.

Code evidence:

- `backend_visualizer/app/page.tsx:574-585`
- Specifically:
  - `filter` starts as `"all"`.
  - `useEffect(() => { if (selectedStudent && studentOptions.includes(selectedStudent)) setFilter(selectedStudent); }, [selectedStudent, studentOptions]);`

Impact:

- Clicking `All students` is temporary.
- The view jumps back to the previously selected student during later renders/polls.
- The KG filter is coupled to the Personality Graph selection, which are separate operator intents.

### 3. The demo autostarts and surfaces persistent stale state

Current behavior:

- Backend startup auto-bootstraps the demo runtime whenever notes are empty.
- The visualizer also calls `bootstrap(false)` on mount, which starts the threads immediately.
- The app uses persistent remote DB defaults if env vars are absent.
- That means the visualizer can load into an already-populated shared database state from previous runs.

Code evidence:

- `intelligence/api/main.py:52-57`
- `backend_visualizer/app/page.tsx:182-204`
- `intelligence/api/services/demo_runtime.py:114-134`
- `intelligence/api/services/ghost_client.py:26-43`

Impact:

- Opening the page is not a neutral action; it starts or continues the demo.
- If the shared DB already has rows, the visualizer immediately shows old notes, old profiles, old KG nodes, and old alerts.
- This breaks the intended story: "start from zero and watch the system build itself live."

### 4. The visualizer currently has no pre-demo state model

Current behavior:

- The page assumes the runtime should be bootstrapped as soon as it mounts.
- There is no distinct state for:
  - never started
  - ready to start
  - resetting
  - running
  - paused/stopped

Impact:

- There is no clean operator journey.
- The only main CTA is `Restart From Empty`, which presumes the demo is already live.
- The UX skips the most important step in the demo: the empty starting point.

### 5. The visualizer is tied to broad persisted tables instead of an isolated run/session

Current behavior:

- `get_demo_overview()` reads directly from the main notes, profile, alert, action, personality, and KG tables.
- Those tables are global for the chosen DB URLs.

Impact:

- The demo is not isolated from prior runs.
- Counts like "122 notes ingested" are believable symptoms of shared retained state, not a frontend-only rendering bug.
- Even if the UI is cleaned up, the demo will still be flaky unless startup/reset semantics are tightened.

---

## Recommended Fix Strategy

Implement this in three phases, in order.

---

## Phase 1: Make the demo start cleanly and deterministically

### Objective

Open the visualizer into a genuine pre-run empty state, and only start ingestion/agent execution when the operator explicitly starts the run.

### Backend changes

#### 1. Remove implicit runtime start from API startup

Change:

- Stop calling `bootstrap_demo(reset=False)` from `intelligence/api/main.py` startup.

Reason:

- Server boot should prepare tables, not mutate demo state.

#### 2. Split "overview" from "start/reset"

Change `demo_runtime.py` so these concerns are explicit:

- `get_demo_overview()` should be a read-only snapshot.
- `start_demo(reset: bool)` should start threads and optionally truncate state first.
- `reset_demo()` should stop threads and clear tables without implicitly restarting unless requested.
- Optional but recommended: add `stop_demo()` for operator control.

Reason:

- Right now `bootstrap_demo()` mixes reset, start, and readback into one call.
- The visualizer needs finer control for a clean lifecycle.

#### 3. Add explicit runtime mode to overview

Return fields like:

- `mode: "idle" | "resetting" | "running" | "stopped"`
- `started: boolean`
- `current_stage: string | null`
- `current_student: string | null`
- `current_note_id: number | null`
- `last_stage_started_at`
- `last_stage_completed_at`

Reason:

- The frontend should render from runtime truth, not infer everything from historical logs.

#### 4. Tighten DB configuration behavior

Recommended cleanup:

- Stop silently falling back to hardcoded remote DB URLs for demo runs, or at minimum gate those fallbacks behind an explicit env flag.
- If env is missing, fail loudly in demo mode instead of connecting to shared stale state by default.

Reason:

- Shared remote default state is the main source of "surprise old data".

Minimum acceptable fallback if we do not change DB wiring yet:

- Keep the current DB wiring for now.
- But require the visualizer start flow to call reset before first run.
- Do not display the stale tables before that reset happens.

### Frontend changes

#### 5. Replace auto-bootstrap on mount with read-only initialization

In `backend_visualizer/app/page.tsx`:

- Remove `bootstrap(false)` from the initial `useEffect`.
- Initial load should fetch lightweight runtime status or overview only.
- If runtime mode is `idle`, show the empty-state presentation instead of starting threads.

#### 6. Add a true empty-state hero

Before the run starts, the page should show:

- `0 notes`
- `0 profiles`
- `0 knowledge nodes`
- `0 alerts`
- a primary CTA such as `Start Live Demo`

Recommended behavior:

- `Start Live Demo` => reset tables, reset cursor/runtime, then start ingest/agent threads.

#### 7. Make "Restart From Empty" a second-stage action

Once running:

- keep `Restart From Empty`
- optionally add `Stop`

Reason:

- The initial action and the restart action are not the same thing semantically.

### Validation for Phase 1

Expected result:

1. Open the visualizer.
2. It shows an idle/ready state, not old rows.
3. Click `Start Live Demo`.
4. Counts begin at zero.
5. Notes, profiles, alerts, and KG nodes appear progressively.

---

## Phase 2: Make Live Workflow truly live

### Objective

Show the current agent step in real time instead of reconstructing it from the last completed event.

### Backend changes

#### 1. Introduce explicit stage tracking in the runtime state

Add stage transitions during the loop, for example:

- `waiting_for_note`
- `note_ingested`
- `reassessing_student`
- `updating_profile`
- `enriching_knowledge`
- `writing_alert`
- `cycle_complete`

Track at least:

- `current_stage`
- `current_student`
- `current_note_id`
- `stage_started_at`
- `stage_message`

Implementation point:

- Update runtime state from inside:
  - `_ingest_worker()` in `demo_runtime.py`
  - `run_agent_cycle()` in `self_improve.py`

#### 2. Log stage transitions as first-class actions

Recommended action kinds:

- `stage_enter`
- `stage_exit`

Payload example:

- `stage`
- `student_name`
- `note_id`
- `queries`
- `new_nodes_created`

Reason:

- The trace panel and workflow rail then share the same stage semantics.

#### 3. Expose a dedicated current-stage payload in `/api/demo/overview`

Return a normalized structure like:

```json
{
  "runtime": {
    "mode": "running",
    "current_stage": "enriching_knowledge",
    "current_student": "Aarav Patel",
    "current_note_id": 14,
    "stage_started_at": "..."
  }
}
```

Reason:

- The frontend should not need to reverse-engineer current state from event logs.

### Frontend changes

#### 4. Rebuild the workflow rail from runtime stage, not `latestAction()`

Current code to replace:

- `backend_visualizer/app/page.tsx:233-289`

New model:

- exactly one step is `active`
- prior completed steps are `ready`
- future steps are `idle`

The focus card should also use:

- current stage message
- current student
- current note preview
- current query list if enrichment is active

#### 5. Add stage-specific copy

Examples:

- `Ingest`: "Inserting note for Aarav Patel"
- `Reassess`: "Rebuilding cumulative profile from 4 notes"
- `Enrich`: "Querying OpenAlex for dysregulation / de-escalation interventions"
- `Escalate`: "Writing high-severity alert with recommended actions"

#### 6. Keep the trace panel raw, but make it match the same stage model

Trace can still show:

- note ingests
- stage transitions
- cycle summaries
- agent outputs

Reason:

- The operator surface should have one truth source for current stage and one detailed log for auditing.

### Validation for Phase 2

Expected result:

1. Start the demo.
2. Watch the workflow rail move step-by-step.
3. During enrichment, the Enrich card is the only active step.
4. During alert writing, Escalate becomes active.
5. Trace entries align with what the rail shows.

---

## Phase 3: Fix Knowledge Graph tab/filter behavior

### Objective

Make KG filtering stable and intentional.

### Root cause to fix

The KG local filter is being overwritten by global student selection.

Current problematic code:

- `backend_visualizer/app/page.tsx:581-585`

### Recommended frontend changes

#### 1. Decouple KG filter from the Personality Graph selection

Recommended state split:

- `selectedStudent` = personality graph / student summary focus
- `kgFilter` = `"all"` or one student name

Rule:

- Selecting a student in the personality area must not forcibly overwrite a manually chosen KG filter.

#### 2. Only seed KG filter once

Allowed behavior:

- On first load, if there is a selected student and no user interaction yet, default KG filter to that student.

After that:

- user choice wins
- polling/data refresh must not overwrite it

Implementation options:

- add `kgFilterTouched` boolean
- or initialize `kgFilter` from props once and never sync via effect again

Recommended choice:

- `kgFilterTouched`
- It preserves good defaults while respecting user intent.

#### 3. Preserve node selection when possible

Current code already tries to keep `selectedNodeId` valid.

Keep this behavior, but ensure:

- switching between `all` and a student does not unnecessarily reset the inspector if the node is still visible

#### 4. Consider explicit sync affordance instead of implicit sync

Optional enhancement:

- add a small button like `Match personality focus`

Reason:

- This makes synchronization a deliberate operator choice.

### Validation for Phase 3

Expected result:

1. Pick student `A`.
2. In KG, click `All students`.
3. Wait through multiple polling intervals.
4. KG remains on `All students`.
5. Change personality focus to student `B`.
6. KG still remains on `All students` unless manually changed.

---

## Supporting Cleanup

### 1. Clarify demo copy

Update UI text so it matches the actual operator flow:

- Before start: "Ready to simulate live ingestion"
- During run: "Live"
- After stop: "Paused"

### 2. Make metrics respect the idle state

Before demo start:

- show zeroed metrics, not stale persisted metrics

This is important even if tables still contain old data somewhere behind the scenes.

### 3. Keep restart behavior safe

If `Restart From Empty` truncates shared DB tables, the UI should make that explicit.

At minimum:

- confirm restart intent
- prevent accidental double-click

### 4. Keep polling stable

The current 1s polling is acceptable for now.

No need to introduce SSE/WebSockets in the first cleanup pass unless:

- the stage updates feel too coarse after explicit runtime stage tracking

Recommended scope for now:

- keep polling
- improve the backend payload

---

## Suggested File-Level Work Plan

### `intelligence/api/services/demo_runtime.py`

- Split read/start/reset responsibilities
- Track explicit runtime mode
- Track current stage metadata
- Expose cleaner overview payload

### `intelligence/api/services/self_improve.py`

- Emit stage transitions throughout the cycle
- Update runtime current stage/student/note metadata
- Keep final cycle summary logging

### `intelligence/api/main.py`

- Remove startup auto-bootstrap
- Replace the current demo bootstrap route with clearer lifecycle endpoints if needed

### `intelligence/api/services/ghost_client.py`

- Add helpers for runtime stage writes/reads if needed
- Potentially tighten DB env behavior

### `backend_visualizer/app/page.tsx`

- Remove mount-time autostart
- Add idle/start/reset lifecycle UI
- Rebuild workflow rail against runtime stage payload
- Decouple KG filter from selected student

### `backend_visualizer/app/globals.css`

- Add any styles needed for:
  - idle shell
  - active stage emphasis
  - paused/resetting states
  - updated button hierarchy

---

## Testing Checklist

### Functional

1. Fresh page load shows idle/empty state.
2. Starting the demo begins from zero notes.
3. Note counter increments over time.
4. Profiles appear only after reassessment runs.
5. KG nodes appear only after enrichment runs.
6. Alerts appear only when agent logic creates them.
7. Live Workflow highlights the current stage, not just the most recent finished event.
8. `All students` filter persists across polling.
9. Restart resets notes, profiles, KG nodes, alerts, and runtime state.

### Regression

1. Personality graph still switches students correctly.
2. KG node inspector still opens the clicked node.
3. Agent Trace still shows recent actions.
4. Repeated polling does not cause visual jumps.
5. No duplicate threads are started by repeated start actions.

### Demo narrative

1. Open page.
2. See clean empty shell.
3. Click start.
4. Watch note ingestion.
5. Watch reassessment.
6. Watch KG enrichment.
7. Watch alerts and student state evolve live.

If that sequence is smooth, the visualizer matches the intended hackathon story.

---

## Recommended Execution Order

1. Fix demo lifecycle and empty start.
2. Add explicit runtime stage tracking.
3. Rewire the Live Workflow UI to stage data.
4. Decouple KG filter state from selected student.
5. Polish idle/running/resetting UI states.
6. Run a full live walkthrough from empty.

---

## Out of Scope for This Cleanup Pass

These are related but should stay out unless they block the fixes above:

- migrating the visualizer to SSE/WebSockets
- redesigning the whole graph layout engine
- replacing the polling model entirely
- changing the core assessment or KG logic

---

## Approval Trigger

Once approved, I’ll implement this cleanup in the order above and keep the dirty worktree intact outside the touched paths.
