"use client";
import { useState } from "react";
import { BehavioralKGPanel } from "./components/BehavioralKGPanel";
import { StageRail } from "./components/StageRail";
import { StudentTimeline } from "./components/StudentTimeline";
import { IncidentDrawer } from "./components/IncidentDrawer";
import { GodModePanel } from "./components/GodModePanel";
import type { StudentIncident } from "./lib/api";

export default function LivePage() {
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [openIncident, setOpenIncident] = useState<StudentIncident | null>(
    null,
  );

  return (
    <div className="h-[calc(100vh-3rem)] flex flex-col">
      <div className="flex-[1.1] min-h-0">
        <BehavioralKGPanel
          selectedSlug={selectedSlug}
          onSelectNode={setSelectedSlug}
        />
      </div>
      <StageRail />
      <div className="flex-1 min-h-0">
        <StudentTimeline
          highlightSlug={selectedSlug}
          onOpenIncident={setOpenIncident}
        />
      </div>
      <IncidentDrawer
        incident={openIncident}
        onClose={() => setOpenIncident(null)}
        onSelectBehavioralNode={setSelectedSlug}
      />
      <GodModePanel />
    </div>
  );
}
