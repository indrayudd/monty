"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  fetchAllFlags,
  fetchStudentFlags,
  fetchInsights,
  fetchSuggestions,
  StudentProfile,
  Snapshot,
  InsightsResponse,
  SuggestionsResponse,
} from "../../lib/api";
import StudentSelector from "../../components/StudentSelector";
import FlagAlerts from "../../components/FlagAlerts";
import Interpretations from "../../components/Interpretations";
import Suggestions from "../../components/Suggestions";

export default function StudentDetail() {
  const params = useParams();
  const studentName = decodeURIComponent(params.name as string);

  const [students, setStudents] = useState<StudentProfile[]>([]);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [insights, setInsights] = useState<InsightsResponse | null>(null);
  const [suggestions, setSuggestions] = useState<SuggestionsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(true);

  useEffect(() => {
    fetchAllFlags().then((data) => {
      setStudents(data);
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    if (!studentName) return;
    setDetailLoading(true);
    Promise.all([
      fetchStudentFlags(studentName),
      fetchInsights(studentName),
      fetchSuggestions(studentName),
    ]).then(([flagsData, insightsData, suggestionsData]) => {
      setSnapshots(flagsData.snapshots);
      setInsights(insightsData);
      setSuggestions(suggestionsData);
      setDetailLoading(false);
    });
  }, [studentName]);

  const selectedProfile = students.find((s) => s.student_name === studentName);

  return (
    <div className="flex h-screen bg-gray-950 text-gray-100">
      {/* Sidebar */}
      <aside className="w-64 border-r border-gray-800 bg-gray-900/50 p-4 overflow-y-auto flex-shrink-0">
        <a href="/" className="text-xs text-gray-500 hover:text-gray-300 mb-3 block">
          &larr; Back to Dashboard
        </a>
        <h1 className="text-lg font-bold text-white mb-1">Monty</h1>
        <p className="text-xs text-gray-500 mb-6">Student Detail</p>
        {!loading && (
          <StudentSelector
            students={students}
            selected={studentName}
            onSelect={(name) => {
              window.location.href = `/student/${encodeURIComponent(name)}`;
            }}
          />
        )}
      </aside>

      {/* Main content — 3 panels */}
      <main className="flex-1 flex overflow-hidden">
        {detailLoading || !insights || !suggestions ? (
          <div className="flex-1 flex items-center justify-center text-gray-500">
            Loading...
          </div>
        ) : (
          <>
            <section className="flex-1 border-r border-gray-800 p-5 overflow-y-auto">
              <FlagAlerts
                snapshots={snapshots}
                studentName={studentName}
                trend={selectedProfile?.trend || "stable"}
              />
            </section>

            <section className="flex-1 border-r border-gray-800 p-5 overflow-y-auto">
              <Interpretations insights={insights} snapshots={snapshots} />
            </section>

            <section className="flex-1 p-5 overflow-y-auto">
              <Suggestions data={suggestions} />
            </section>
          </>
        )}
      </main>
    </div>
  );
}
