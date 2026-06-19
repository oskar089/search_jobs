import { api } from "./api";
import type { Notification } from "../types";

export function listNotifications(): Promise<Notification[]> {
  return api<Notification[]>("/notifications");
}

export function markNotificationRead(id: string): Promise<void> {
  return api<void>(`/notifications/${id}/read`, { method: "PATCH" });
}
