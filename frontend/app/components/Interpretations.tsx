"use client";

import { InsightsResponse, Snapshot } from "../lib/api";

const severityLabel = {
  red: { text: "Critical", color: "text-red-400" },
  yellow: { text: "Monitor", color: "text-yellow-400" },
  green: { text: "On Track", color: "text-green-400" },
};

const trendLabel = {
  improving: { text: "Improving", color: "text-green-400", icon: "\u2191" },
  stable: { text: "Stable", color: "text-gray-400", icon: "\u2192" },
  declining: { text: "Declining", color: "text-red-400", icon: "\u2193" },
};

export default function Interpretations({
  insights,
  snapshots,
}: {
  insights: InsightsResponse;
  snapshots: Snapshot[];
}) {
  const sev = severityLabel[insights.current_severity as keyof typeof severityLabel] || severityLabel.green;
  const trend = trendLabel[insights.trend as keyof typeof trendLabel] || trendLabel.stable;

  const severityTimeline = snapshots.map((s) => s.severity);

  return (
    <div className="h-full flex flex-col">
      <h2 className="text-lg font-semibold text-white mb-4">Interpretations</h2>

      <div className="flex gap-4 mb-4">
        <div className="bg-gray-800/60 border border-gray-700 rounded-lg px-4 py-3 flex-1">
          <div className="text-xs text-gray-500 mb-1">Current Status</div>
          <div className={`text-xl font-bold ${sev.color}`}>{sev.text}</div>
        </div>
        <div className="bg-gray-800/60 border border-gray-700 rounded-lg px-4 py-3 flex-1">
          <div className="text-xs text-gray-500 mb-1">Trend</div>
          <div className={`text-xl font-bold ${trend.color}`}>
            {trend.icon} {trend.text}
          </div>
        </div>
        <div className="bg-gray-800/60 border border-gray-700 rounded-lg px-4 py-3 flex-1">
          <div className="text-xs text-gray-500 mb-1">Assessments</div>
          <div className="text-xl font-bold text-white">{insights.assessment_count}</div>
        </div>
      </div>

      <div className="mb-4">
        <div className="text-xs text-gray-500 mb-2">Severity Timeline</div>
        <div className="flex gap-1">
          {severityTimeline.map((s, i) => (
            <div
              key={i}
              className={`h-6 flex-1 rounded ${
                s === "red"
                  ? "bg-red-500"
                  : s === "yellow"
                  ? "bg-yellow-400"
                  : "bg-green-500"
              }`}
              title={`Note ${i + 1}: ${s}`}
            />
          ))}
        </div>
      </div>

      <div className="bg-gray-800/60 border border-gray-700 rounded-lg p-4 mb-4">
        <div className="text-xs text-gray-500 mb-2">Latest Assessment</div>
        <p className="text-sm text-gray-200 leading-relaxed">{insights.summary}</p>
      </div>

      <div className="bg-gray-800/60 border border-gray-700 rounded-lg p-4">
        <div className="text-xs text-gray-500 mb-2">Behavioral Patterns</div>
        <div className="flex flex-wrap gap-2">
          {insights.behavioral_patterns.split(",").map((p, i) => (
            <span
              key={i}
              className="text-xs bg-gray-700 text-gray-300 px-2 py-1 rounded"
            >
              {p.trim()}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
