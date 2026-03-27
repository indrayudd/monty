"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { StudentProfile } from "../lib/api";

const sevBadge = {
  red: "bg-red-900/50 text-red-300 border-red-700",
  yellow: "bg-yellow-900/50 text-yellow-300 border-yellow-700",
  green: "bg-green-900/50 text-green-300 border-green-700",
};

const trendIcon: Record<string, { icon: string; color: string }> = {
  improving: { icon: "\u2191", color: "text-green-400" },
  stable: { icon: "\u2192", color: "text-gray-400" },
  declining: { icon: "\u2193", color: "text-red-400" },
};

type SortKey = "student_name" | "current_severity" | "trend" | "assessment_count";

const sevOrder = { red: 0, yellow: 1, green: 2 };
const trendOrder = { declining: 0, stable: 1, improving: 2 };

export default function StudentsTable({ students }: { students: StudentProfile[] }) {
  const router = useRouter();
  const [sortKey, setSortKey] = useState<SortKey>("current_severity");
  const [asc, setAsc] = useState(true);

  const sorted = [...students].sort((a, b) => {
    let cmp = 0;
    if (sortKey === "current_severity") {
      cmp = sevOrder[a.current_severity] - sevOrder[b.current_severity];
    } else if (sortKey === "trend") {
      cmp = trendOrder[a.trend] - trendOrder[b.trend];
    } else if (sortKey === "assessment_count") {
      cmp = a.assessment_count - b.assessment_count;
    } else {
      cmp = a.student_name.localeCompare(b.student_name);
    }
    return asc ? cmp : -cmp;
  });

  function toggleSort(key: SortKey) {
    if (sortKey === key) setAsc(!asc);
    else { setSortKey(key); setAsc(true); }
  }

  const Header = ({ label, k }: { label: string; k: SortKey }) => (
    <th
      className="text-left text-xs font-medium text-gray-400 uppercase tracking-wide px-4 py-3 cursor-pointer hover:text-gray-200 select-none"
      onClick={() => toggleSort(k)}
    >
      {label} {sortKey === k ? (asc ? "\u25B2" : "\u25BC") : ""}
    </th>
  );

  return (
    <div className="bg-gray-800/40 border border-gray-700 rounded-xl overflow-hidden">
      <table className="w-full">
        <thead className="border-b border-gray-700">
          <tr>
            <Header label="Student" k="student_name" />
            <Header label="Severity" k="current_severity" />
            <Header label="Trend" k="trend" />
            <Header label="Assessments" k="assessment_count" />
            <th className="text-left text-xs font-medium text-gray-400 uppercase tracking-wide px-4 py-3">
              Latest Summary
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((s) => {
            const t = trendIcon[s.trend] || trendIcon.stable;
            return (
              <tr
                key={s.student_name}
                onClick={() => router.push(`/student/${encodeURIComponent(s.student_name)}`)}
                className="border-b border-gray-800 hover:bg-gray-800/60 cursor-pointer transition-colors"
              >
                <td className="px-4 py-3 text-sm text-gray-100 font-medium">
                  {s.student_name}
                </td>
                <td className="px-4 py-3">
                  <span className={`text-xs px-2 py-0.5 rounded border ${sevBadge[s.current_severity]}`}>
                    {s.current_severity.toUpperCase()}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className={`text-sm ${t.color}`}>
                    {t.icon} {s.trend}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm text-gray-400">{s.assessment_count}</td>
                <td className="px-4 py-3 text-sm text-gray-500 max-w-xs truncate">
                  {s.latest_summary}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
