"use client";

import { useEffect, useState } from "react";
import {
  fetchAllFlags,
  fetchStudentFlags,
  fetchInsights,
  fetchSuggestions,
  StudentProfile,
  Snapshot,
  InsightsResponse,
  SuggestionsResponse,
} from "./lib/api";
import StudentSelector from "./components/StudentSelector";
import FlagAlerts from "./components/FlagAlerts";
import Interpretations from "./components/Interpretations";
import Suggestions from "./components/Suggestions";

export default function Dashboard() {
  const [students, setStudents] = useState<StudentProfile[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [insights, setInsights] = useState<InsightsResponse | null>(null);
  const [suggestions, setSuggestions] = useState<SuggestionsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    fetchAllFlags().then((data) => {
      setStudents(data);
      setLoading(false);
      if (data.length > 0) {
        setSelected(data[0].student_name);
      }
    });
  }, []);

  useEffect(() => {
    if (!selected) return;
    setDetailLoading(true);
    Promise.all([
      fetchStudentFlags(selected),
      fetchInsights(selected),
      fetchSuggestions(selected),
    ]).then(([flagsData, insightsData, suggestionsData]) => {
      setSnapshots(flagsData.snapshots);
      setInsights(insightsData);
      setSuggestions(suggestionsData);
      setDetailLoading(false);
    });
  }, [selected]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-950 text-gray-400">
        Loading students...
      </div>
    );
  }

  const selectedProfile = students.find((s) => s.student_name === selected);

  return (
    <div className="flex h-screen bg-gray-950 text-gray-100">
      {/* Sidebar */}
      <aside className="w-64 border-r border-gray-800 bg-gray-900/50 p-4 overflow-y-auto flex-shrink-0">
        <h1 className="text-lg font-bold text-white mb-1">PEP OS</h1>
        <p className="text-xs text-gray-500 mb-6">Student Intelligence Dashboard</p>
        <StudentSelector
          students={students}
          selected={selected}
          onSelect={setSelected}
        />
      </aside>

      {/* Main content — 3 panels */}
      <main className="flex-1 flex overflow-hidden">
        {detailLoading || !insights || !suggestions ? (
          <div className="flex-1 flex items-center justify-center text-gray-500">
            {selected ? "Loading..." : "Select a student"}
          </div>
        ) : (
          <>
            {/* Panel 1: Flag Alerts */}
            <section className="flex-1 border-r border-gray-800 p-5 overflow-y-auto">
              <FlagAlerts
                snapshots={snapshots}
                studentName={selected || ""}
                trend={selectedProfile?.trend || "stable"}
              />
            </section>

            {/* Panel 2: Interpretations */}
            <section className="flex-1 border-r border-gray-800 p-5 overflow-y-auto">
              <Interpretations insights={insights} snapshots={snapshots} />
            </section>

            {/* Panel 3: Suggestions */}
            <section className="flex-1 p-5 overflow-y-auto">
              <Suggestions data={suggestions} />
            </section>
          </>
        )}
      </main>
    </div>
  );
}
