"use client";

import { StudentProfile } from "../lib/api";

const severityColor = {
  red: "bg-red-500",
  yellow: "bg-yellow-400",
  green: "bg-green-500",
};

const trendIcon = {
  improving: "\u2191",
  stable: "\u2192",
  declining: "\u2193",
};

export default function StudentSelector({
  students,
  selected,
  onSelect,
}: {
  students: StudentProfile[];
  selected: string | null;
  onSelect: (name: string) => void;
}) {
  return (
    <div className="space-y-1">
      <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">
        Students ({students.length})
      </h2>
      {students.map((s) => (
        <button
          key={s.student_name}
          onClick={() => onSelect(s.student_name)}
          className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left text-sm transition-colors ${
            selected === s.student_name
              ? "bg-gray-700 text-white"
              : "text-gray-300 hover:bg-gray-800"
          }`}
        >
          <span
            className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${severityColor[s.current_severity]}`}
          />
          <span className="flex-1 truncate">{s.student_name}</span>
          <span className="text-xs text-gray-500" title={s.trend}>
            {trendIcon[s.trend]}
          </span>
        </button>
      ))}
    </div>
  );
}
