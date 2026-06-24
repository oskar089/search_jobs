import { api } from "./api";
import type { Application } from "../types";

export function listApplications(statusFilter?: string): Promise<Application[]> {
  const params = statusFilter ? `?status_filter=${statusFilter}` : "";
  return api<Application[]>(`/applications${params}`);
}

export function getApplication(id: string): Promise<Application> {
  return api<Application>(`/applications/${id}`);
}
