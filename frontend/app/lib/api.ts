const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface StudentProfile {
  student_name: string;
  current_severity: "green" | "yellow" | "red";
  previous_severity: string | null;
  trend: "improving" | "stable" | "declining";
  assessment_count: number;
  latest_summary: string;
  latest_patterns: string;
  latest_suggestions: string;
  updated_at: string;
}

export interface Snapshot {
  id: number;
  note_id: number;
  snapshot_at: string;
  severity: "green" | "yellow" | "red";
  profile_summary: string;
  behavioral_patterns: string;
  suggestions: string;
}

export interface InsightsResponse {
  student_name: string;
  current_severity: string;
  previous_severity: string | null;
  trend: string;
  assessment_count: number;
  summary: string;
  behavioral_patterns: string;
}

export interface SuggestionsResponse {
  student_name: string;
  severity: string;
  trend: string;
  suggestions: string;
}

export async function fetchAllFlags(): Promise<StudentProfile[]> {
  const res = await fetch(`${API_BASE}/api/flags`);
  const data = await res.json();
  return data.students;
}

export async function fetchStudentFlags(name: string): Promise<{ profile: StudentProfile; snapshots: Snapshot[] }> {
  const res = await fetch(`${API_BASE}/api/flags/${encodeURIComponent(name)}`);
  return res.json();
}

export async function fetchInsights(name: string): Promise<InsightsResponse> {
  const res = await fetch(`${API_BASE}/api/insights/${encodeURIComponent(name)}`);
  return res.json();
}

export async function fetchSuggestions(name: string): Promise<SuggestionsResponse> {
  const res = await fetch(`${API_BASE}/api/suggestions/${encodeURIComponent(name)}`);
  return res.json();
}
