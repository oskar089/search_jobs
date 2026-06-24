import { api } from "./api";

export interface StoredJob {
  id: string;
  title: string;
  company: string;
  location: string | null;
  url: string;
  salary_range: string | null;
  posted_at: string | null;
  scraped_at: string;
  language: string;
  portal_name: string;
  match_score: number | null;
}

export function listJobs(limit = 20): Promise<StoredJob[]> {
  return api<StoredJob[]>(`/jobs?limit=${limit}`);
}

export function clearJobs(): Promise<{ deleted: number }> {
  return api<{ deleted: number }>("/jobs", { method: "DELETE" });
}
