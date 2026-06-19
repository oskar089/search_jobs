import { api } from "./api";
import type { Portal, PortalCreate } from "../types";

export function listPortals(): Promise<Portal[]> {
  return api<Portal[]>("/portals");
}

export function createPortal(data: PortalCreate): Promise<Portal> {
  return api<Portal>("/portals", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function getPortal(id: string): Promise<Portal> {
  return api<Portal>(`/portals/${id}`);
}

export function updatePortal(id: string, data: PortalCreate): Promise<Portal> {
  return api<Portal>(`/portals/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function deletePortal(id: string): Promise<void> {
  return api<void>(`/portals/${id}`, { method: "DELETE" });
}

export function togglePortal(id: string): Promise<Portal> {
  return api<Portal>(`/portals/${id}/toggle`, { method: "PATCH" });
}

export function dryRunPortal(
  id: string,
  testUrl?: string,
): Promise<{
  status: string;
  jobs: Array<{
    title: string;
    company: string;
    location: string | null;
    description: string;
    url: string;
    salary_range: string | null;
    posted_at: string | null;
  }>;
  error?: string;
}> {
  const query = testUrl ? `?test_url=${encodeURIComponent(testUrl)}` : "";
  return api(`/portals/${id}/dry-run${query}`, { method: "POST" });
}
