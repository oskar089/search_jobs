import type { Application } from "../types";

// Stub until backend implements GET /api/applications
export async function listApplications(): Promise<Application[]> {
  await new Promise((r) => setTimeout(r, 300));
  return [];
}
