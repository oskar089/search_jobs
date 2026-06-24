import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listNotifications,
  markNotificationRead,
  getNotificationPreferences,
  updateNotificationPreferences,
} from "../lib/notifications";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Toggle } from "../components/ui/Toggle";
import { Bell, CheckCircle, Check } from "lucide-react";
import type { NotificationPreferences } from "../types";

function timeAgo(dateStr: string): string {
  const now = Date.now();
  const date = new Date(dateStr).getTime();
  const diffSec = Math.floor((now - date) / 1000);
  if (diffSec < 60) return "just now";
  const mins = Math.floor(diffSec / 60);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString();
}

const typeVariants: Record<string, "default" | "success" | "warning" | "danger" | "info"> = {
  match: "success",
  error: "danger",
  info: "info",
  warning: "warning",
};

const PREFERENCE_LABELS: { key: keyof NotificationPreferences; label: string; description: string }[] = [
  {
    key: "in_app",
    label: "In-app notifications",
    description: "Receive notifications inside the application",
  },
  {
    key: "email",
    label: "Email notifications",
    description: "Receive notifications via email",
  },
  {
    key: "on_submit",
    label: "Successful submissions",
    description: "Notify when an application is submitted successfully",
  },
  {
    key: "on_fail",
    label: "Failed applications",
    description: "Notify when an application fails",
  },
  {
    key: "on_match",
    label: "New job matches",
    description: "Notify when new jobs match your profile",
  },
];

export default function NotificationsPage() {
  const queryClient = useQueryClient();
  const [showSaved, setShowSaved] = useState(false);

  const { data: notifications, isLoading } = useQuery({
    queryKey: ["notifications"],
    queryFn: listNotifications,
  });

  const { data: preferences } = useQuery({
    queryKey: ["notification-preferences"],
    queryFn: getNotificationPreferences,
  });

  const markReadMutation = useMutation({
    mutationFn: markNotificationRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const updatePrefsMutation = useMutation({
    mutationFn: updateNotificationPreferences,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notification-preferences"] });
      setShowSaved(true);
      setTimeout(() => setShowSaved(false), 2500);
    },
  });

  const handleToggle = (key: keyof NotificationPreferences) => {
    if (!preferences) return;
    updatePrefsMutation.mutate({
      ...preferences,
      [key]: !preferences[key],
    });
  };

  if (isLoading) {
    return <div className="text-sm text-slate-400">Loading notifications...</div>;
  }

  const sorted = notifications
    ? [...notifications].sort(
        (a, b) => new Date(b.sent_at).getTime() - new Date(a.sent_at).getTime(),
      )
    : [];

  return (
    <div>
      <h1 className="mb-1 text-2xl font-bold text-white">Notifications</h1>
      <p className="mb-6 text-sm text-slate-400">
        Stay updated on your applications and matches.
      </p>

      {/* Notification Preferences */}
      <Card className="mb-8">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-white">Notification Preferences</h2>
          {showSaved && (
            <span className="flex items-center gap-1 text-xs text-green-400">
              <Check className="h-3.5 w-3.5" />
              Preferences saved
            </span>
          )}
        </div>
        <p className="mb-4 mt-1 text-xs text-slate-400">
          Choose which notification types and channels you want to receive.
        </p>
        <div className="space-y-3">
          {PREFERENCE_LABELS.map(({ key, label, description }) => (
            <div key={key} className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-200">{label}</p>
                <p className="text-xs text-slate-500">{description}</p>
              </div>
              <Toggle
                checked={preferences?.[key] ?? false}
                onChange={() => handleToggle(key)}
                disabled={updatePrefsMutation.isPending}
              />
            </div>
          ))}
        </div>
      </Card>

      {/* Notifications List */}
      {sorted.length === 0 ? (
        <Card>
          <div className="flex flex-col items-center justify-center py-16 text-slate-500">
            <Bell className="mb-3 h-12 w-12 opacity-40" />
            <p className="text-sm font-medium">No notifications yet</p>
            <p className="mt-1 text-xs text-slate-600">
              You'll get notified when new jobs match your profile
            </p>
          </div>
        </Card>
      ) : (
        <div className="space-y-3">
          {sorted.map((notification) => (
            <div
              key={notification.id}
              className={`cursor-pointer rounded-lg border p-4 transition-colors ${
                notification.is_read
                  ? "border-slate-700 bg-slate-800/50"
                  : "border-blue-700/50 bg-slate-800"
              }`}
              onClick={() => {
                if (!notification.is_read) {
                  markReadMutation.mutate(notification.id);
                }
              }}
            >
              <div className="flex items-start gap-3">
                <div
                  className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${
                    notification.is_read ? "bg-slate-600" : "bg-blue-500"
                  }`}
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <h3
                      className={`truncate text-sm font-medium ${
                        notification.is_read ? "text-slate-400" : "text-white"
                      }`}
                    >
                      {notification.title}
                    </h3>
                    <Badge variant={typeVariants[notification.type] || "default"}>
                      {notification.type}
                    </Badge>
                    {notification.is_read && (
                      <CheckCircle className="h-3.5 w-3.5 shrink-0 text-green-400" />
                    )}
                  </div>
                  <p
                    className={`mt-1 line-clamp-2 text-xs ${
                      notification.is_read ? "text-slate-500" : "text-slate-400"
                    }`}
                  >
                    {notification.body}
                  </p>
                  <p className="mt-1.5 text-xs text-slate-600">
                    {timeAgo(notification.sent_at)}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
