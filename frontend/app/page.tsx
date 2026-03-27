"use client";

import { useEffect, useState } from "react";
import { fetchAllFlags, StudentProfile } from "./lib/api";
import StatsCards from "./components/StatsCards";
import StudentsTable from "./components/StudentsTable";

export default function AdminDashboard() {
  const [students, setStudents] = useState<StudentProfile[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAllFlags().then((data) => {
      setStudents(data);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-950 text-gray-400">
        Loading dashboard...
      </div>
    );
  }

  const needsAttention = students.filter(
    (s) => s.current_severity === "red" || s.trend === "declining"
  );

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="border-b border-gray-800 px-8 py-5">
        <h1 className="text-2xl font-bold text-white">Monty</h1>
        <p className="text-sm text-gray-500">Admin Dashboard</p>
      </header>

      <div className="max-w-7xl mx-auto px-8 py-8 space-y-8">
        {/* Stats */}
        <StatsCards students={students} />

        {/* Needs Attention */}
        {needsAttention.length > 0 && (
          <div>
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">
              Needs Attention
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
              {needsAttention.map((s) => (
                <a
                  key={s.student_name}
                  href={`/student/${encodeURIComponent(s.student_name)}`}
                  className="bg-gray-800/60 border border-gray-700 rounded-lg p-4 hover:border-gray-600 transition-colors"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <span
                      className={`w-2.5 h-2.5 rounded-full ${
                        s.current_severity === "red" ? "bg-red-500" : s.current_severity === "yellow" ? "bg-yellow-400" : "bg-green-500"
                      }`}
                    />
                    <span className="text-sm font-medium text-white">{s.student_name}</span>
                  </div>
                  <p className="text-xs text-gray-500 line-clamp-2">{s.latest_summary}</p>
                  <div className="mt-2 text-xs">
                    <span className={s.trend === "declining" ? "text-red-400" : "text-gray-400"}>
                      {s.trend === "declining" ? "\u2193 Declining" : s.trend === "improving" ? "\u2191 Improving" : "\u2192 Stable"}
                    </span>
                  </div>
                </a>
              ))}
            </div>
          </div>
        )}

        {/* All Students Table */}
        <div>
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">
            All Students
          </h2>
          <StudentsTable students={students} />
        </div>
      </div>
    </div>
  );
}
