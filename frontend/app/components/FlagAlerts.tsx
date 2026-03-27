"use client";

import { Snapshot } from "../lib/api";

const severityBadge = {
  red: "bg-red-900/50 text-red-300 border-red-700",
  yellow: "bg-yellow-900/50 text-yellow-300 border-yellow-700",
  green: "bg-green-900/50 text-green-300 border-green-700",
};

export default function FlagAlerts({
  snapshots,
  studentName,
  trend,
}: {
  snapshots: Snapshot[];
  studentName: string;
  trend: string;
}) {
  const sorted = [...snapshots].reverse();

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-white">Flag Alerts</h2>
        <span className="text-xs text-gray-400">
          {snapshots.length} observations
        </span>
      </div>
      <div className="flex-1 overflow-y-auto space-y-3 pr-1">
        {sorted.map((snap) => (
          <div
            key={snap.id}
            className="bg-gray-800/60 border border-gray-700 rounded-lg p-3"
          >
            <div className="flex items-center gap-2 mb-2">
              <span
                className={`text-xs px-2 py-0.5 rounded border ${severityBadge[snap.severity]}`}
              >
                {snap.severity.toUpperCase()}
              </span>
              <span className="text-xs text-gray-500">
                Note #{snap.note_id}
              </span>
              <span className="text-xs text-gray-600 ml-auto">
                {new Date(snap.snapshot_at).toLocaleDateString()}
              </span>
            </div>
            <p className="text-sm text-gray-300 leading-relaxed">
              {snap.profile_summary}
            </p>
            <div className="mt-2">
              <span className="text-xs text-gray-500">Patterns: </span>
              <span className="text-xs text-gray-400">
                {snap.behavioral_patterns}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
