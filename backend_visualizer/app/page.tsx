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
