import { api } from "./api";
import type { Notification, NotificationPreferences } from "../types";

export function listNotifications(): Promise<Notification[]> {
  return api<Notification[]>("/notifications");
}

export function markNotificationRead(id: string): Promise<void> {
  return api<void>(`/notifications/${id}/read`, { method: "PATCH" });
}

export function getNotificationPreferences(): Promise<NotificationPreferences> {
  return api<NotificationPreferences>("/notifications/preferences");
}

export function updateNotificationPreferences(
  data: NotificationPreferences,
): Promise<NotificationPreferences> {
  return api<NotificationPreferences>("/notifications/preferences", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}
