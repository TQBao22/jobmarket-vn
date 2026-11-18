// Kiểu phản ánh docs/api.md.
export interface Health { status: string; jobs: number; ollama: boolean; cv_model: string }
export interface SkillCount { skill: string; jd_count: number; share: number }
export interface TopSkills { months: string[]; jd_total: number; skills: SkillCount[] }
export interface Job {
  url: string; title: string; company: string;
  date_posted: string | null; valid_through: string | null; skills: string[];
}
export interface Jobs { total: number; jobs: Job[] }
export interface Match {
  url: string; title: string; company: string; score: number; matched: string[]; missing: string[];
}
export interface MatchResult { model: string; cv_skills: string[]; matches: Match[] }

async function call<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    let detail: unknown = `Lỗi ${res.status}`;
    try { detail = (await res.json()).detail ?? detail; } catch { /* body không phải JSON */ }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json() as Promise<T>;
}

export const getHealth = () => call<Health>("/api/health");

export const getTopSkills = (month?: string) =>
  call<TopSkills>(`/api/skills/top${month ? `?month=${encodeURIComponent(month)}` : ""}`);

export function getJobs(skill: string, openOnly: boolean) {
  const q = new URLSearchParams();
  if (skill) q.set("skill", skill);
  q.set("open_only", String(openOnly));
  return call<Jobs>(`/api/jobs?${q}`);
}

export function postMatch(file: File, topK: number) {
  const f = new FormData();
  f.append("file", file);
  f.append("top_k", String(topK));
  return call<MatchResult>("/api/match", { method: "POST", body: f });
}
