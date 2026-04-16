const BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json() as Promise<T>;
}
async function post<T>(path: string, body?: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json() as Promise<T>;
}
async function patch<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json() as Promise<T>;
}

export type BehavioralNode = {
  slug: string;
  type: string;
  title: string;
  summary: string;
  support_count: number;
  students_count: number;
  literature_refs: number;
  curiosity_score: number;
  curiosity_factors: Record<string, number>;
  last_observed_at: string | null;
  last_research_fetched_at: string | null;
  created_at: string;
  file_path: string;
};
export type BehavioralEdge = {
  src_slug: string;
  rel: string;
  dst_slug: string;
  support_count: number;
  students_count: number;
  first_observed_at: string;
  last_observed_at: string;
};
export type StudentIncident = {
  id: number;
  student_name: string;
  note_id: number;
  severity: string;
  ingested_at: string;
  file_path: string;
  behavioral_ref_slugs: string[];
};
export type Persona = {
  name: string;
  age_band: string;
  temperament_axes: Record<string, string>;
  dysfunction_flavor: string;
  recurring_companions: string[];
  narrative: string;
  file_path: string;
};
export type CuriosityEvent = {
  id: number;
  node_slug: string;
  fired_at: string;
  curiosity_score: number;
  factors: Record<string, number>;
  triggered_research: boolean;
  paper_count: number;
};
export type WikiTreeFile = { path: string; mtime: number };
export type WikiPage = {
  path: string;
  frontmatter: Record<string, unknown>;
  body: string;
  raw: string;
};

export const api = {
  behavioralGraph: (minSupport = 1) =>
    get<{ nodes: BehavioralNode[]; edges: BehavioralEdge[] }>(
      `/api/behavioral-graph?min_support=${minSupport}`,
    ),
  studentGraph: (name: string) =>
    get<{ student_name: string; incidents: StudentIncident[] }>(
      `/api/student-graph/${encodeURIComponent(name)}`,
    ),
  studentResearch: (name: string) =>
    get<{ student_name: string; papers: unknown[] }>(
      `/api/student-graph/${encodeURIComponent(name)}/research`,
    ),
  personas: () =>
    get<{
      personas: Persona[];
      overrides: Record<string, unknown>;
      stub?: boolean;
    }>("/api/personas"),
  updatePersona: (
    name: string,
    body: {
      slider?: number;
      flavor_override?: string;
      activity_weight?: number;
    },
  ) => patch(`/api/personas/${encodeURIComponent(name)}`, body),
  injectPersona: (name: string, flavor: string) =>
    post(`/api/personas/${encodeURIComponent(name)}/inject`, { flavor }),
  interactPersonas: (a: string, b: string, scene_hint?: string) =>
    post(`/api/personas/interact`, { a, b, scene_hint }),
  curiosityEvents: (limit = 50) =>
    get<{ events: CuriosityEvent[] }>(`/api/curiosity/events?limit=${limit}`),
  curiosityWeights: (weights: Record<string, number>) =>
    patch(`/api/runtime/curiosity-weights`, weights),
  curiosityInvestigate: (slug: string) =>
    post<{ fire?: boolean; score?: number; reason?: string }>(
      `/api/curiosity/investigate/${encodeURIComponent(slug)}`,
    ),
  wikiTree: () =>
    get<{ root: string; files: WikiTreeFile[] }>("/api/wiki/tree"),
  wikiPage: (path: string) =>
    get<WikiPage>(`/api/wiki/page?path=${encodeURIComponent(path)}`),
  wikiReindex: () =>
    post<{
      nodes: number;
      edges: number;
      incidents: number;
      profiles: number;
    }>("/api/wiki/reindex"),
  demoOverview: () => get<Record<string, unknown>>("/api/demo/overview"),
  demoStart: () => post<Record<string, unknown>>("/api/demo/start"),
  demoStop: () => post<Record<string, unknown>>("/api/demo/stop"),
  demoReset: () => post<Record<string, unknown>>("/api/demo/reset"),
};
