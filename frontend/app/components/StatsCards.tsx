"use client";

import { StudentProfile } from "../lib/api";

export default function StatsCards({ students }: { students: StudentProfile[] }) {
  const red = students.filter((s) => s.current_severity === "red");
  const yellow = students.filter((s) => s.current_severity === "yellow");
  const green = students.filter((s) => s.current_severity === "green");
  const improving = students.filter((s) => s.trend === "improving").length;
  const declining = students.filter((s) => s.trend === "declining").length;
  const stable = students.filter((s) => s.trend === "stable").length;

  const total = students.length;
  const redPct = total ? (red.length / total) * 100 : 0;
  const yellowPct = total ? (yellow.length / total) * 100 : 0;
  const greenPct = total ? (green.length / total) * 100 : 0;

  return (
    <div className="space-y-6">
      {/* Stats row */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-gray-800/60 border border-gray-700 rounded-xl p-5">
          <div className="text-sm text-gray-400 mb-1">Total Students</div>
          <div className="text-3xl font-bold text-white">{total}</div>
        </div>
        <div className="bg-gray-800/60 border border-red-900/50 rounded-xl p-5">
          <div className="text-sm text-red-400 mb-1">Critical</div>
          <div className="text-3xl font-bold text-red-400">{red.length}</div>
          <div className="text-xs text-gray-500 mt-1 truncate">
            {red.map((s) => s.student_name.split(" ")[0]).join(", ") || "None"}
          </div>
        </div>
        <div className="bg-gray-800/60 border border-yellow-900/50 rounded-xl p-5">
          <div className="text-sm text-yellow-400 mb-1">Monitor</div>
          <div className="text-3xl font-bold text-yellow-400">{yellow.length}</div>
        </div>
        <div className="bg-gray-800/60 border border-green-900/50 rounded-xl p-5">
          <div className="text-sm text-green-400 mb-1">On Track</div>
          <div className="text-3xl font-bold text-green-400">{green.length}</div>
        </div>
      </div>

      {/* Severity distribution bar */}
      <div>
        <div className="flex items-center justify-between text-xs text-gray-500 mb-2">
          <span>Severity Distribution</span>
          <span>
            {improving > 0 && <span className="text-green-400 mr-3">{improving} improving</span>}
            {stable > 0 && <span className="text-gray-400 mr-3">{stable} stable</span>}
            {declining > 0 && <span className="text-red-400">{declining} declining</span>}
          </span>
        </div>
        <div className="flex h-4 rounded-full overflow-hidden gap-0.5">
          {redPct > 0 && (
            <div className="bg-red-500 rounded-l-full" style={{ width: `${redPct}%` }} />
          )}
          {yellowPct > 0 && (
            <div className="bg-yellow-400" style={{ width: `${yellowPct}%` }} />
          )}
          {greenPct > 0 && (
            <div className="bg-green-500 rounded-r-full" style={{ width: `${greenPct}%` }} />
          )}
        </div>
      </div>
    </div>
  );
}
