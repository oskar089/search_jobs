import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listApplications } from "../lib/applications";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Modal } from "../components/ui/Modal";
import { Briefcase, ExternalLink, FileText, XCircle, CheckCircle, Loader2 } from "lucide-react";
import type { Application } from "../types";

const STATUS_LABELS: Record<string, { label: string; variant: "default" | "success" | "warning" | "danger" | "info" }> = {
  pending: { label: "Pendiente", variant: "default" },
  applying: { label: "Aplicando", variant: "info" },
  submitted: { label: "Enviada", variant: "success" },
  failed: { label: "Falló", variant: "danger" },
};

const FILTERS = [
  { value: "", label: "Todas" },
  { value: "pending", label: "Pendientes" },
  { value: "submitted", label: "Enviadas" },
  { value: "failed", label: "Fallidas" },
];

export default function ApplicationsPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [selectedApp, setSelectedApp] = useState<Application | null>(null);

  const { data: applications = [], isLoading } = useQuery({
    queryKey: ["applications", statusFilter],
    queryFn: () => listApplications(statusFilter || undefined),
    refetchInterval: 15_000,
  });

  const submitted = applications.filter((a) => a.status === "submitted").length;
  const failed = applications.filter((a) => a.status === "failed").length;
  const pending = applications.filter((a) => a.status === "pending" || a.status === "applying").length;

  return (
    <div>
      <h1 className="mb-1 text-2xl font-bold text-white">Applications</h1>
      <p className="mb-6 text-sm text-slate-400">
        Track your submitted job applications.
      </p>

      {/* Stats */}
      <div className="mb-6 grid grid-cols-3 gap-4">
        <Card>
          <p className="text-xs text-slate-400">Enviadas</p>
          <p className="text-2xl font-bold text-green-400">{submitted}</p>
        </Card>
        <Card>
          <p className="text-xs text-slate-400">Pendientes</p>
          <p className="text-2xl font-bold text-amber-400">{pending}</p>
        </Card>
        <Card>
          <p className="text-xs text-slate-400">Fallidas</p>
          <p className="text-2xl font-bold text-red-400">{failed}</p>
        </Card>
      </div>

      {/* Filters */}
      <div className="mb-4 flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setStatusFilter(f.value)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
              statusFilter === f.value
                ? "bg-blue-600 text-white"
                : "bg-slate-700 text-slate-300 hover:bg-slate-600"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Loading */}
      {isLoading ? (
        <Card>
          <div className="flex items-center justify-center py-16 text-slate-500">
            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
            <span className="text-sm">Loading applications...</span>
          </div>
        </Card>
      ) : applications.length === 0 ? (
        /* Empty state */
        <Card>
          <div className="flex flex-col items-center justify-center py-16 text-slate-500">
            <Briefcase className="mb-3 h-12 w-12 opacity-40" />
            <p className="text-sm font-medium">No applications yet</p>
            <p className="mt-1 max-w-sm text-center text-xs text-slate-600">
              Applications will appear here once the pipeline runs and matches jobs to your profile.
            </p>
          </div>
        </Card>
      ) : (
        /* Table */
        <div className="overflow-x-auto rounded-lg border border-slate-700">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700 bg-slate-800/50 text-left text-slate-400">
                <th className="px-4 py-3 font-medium">Puesto</th>
                <th className="px-4 py-3 font-medium">Empresa</th>
                <th className="hidden px-4 py-3 font-medium sm:table-cell">Portal</th>
                <th className="px-4 py-3 font-medium">Match</th>
                <th className="px-4 py-3 font-medium">Estado</th>
                <th className="hidden px-4 py-3 font-medium md:table-cell">CV</th>
                <th className="px-4 py-3 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {applications.map((app) => {
                const statusInfo = STATUS_LABELS[app.status] || { label: app.status, variant: "default" as const };
                return (
                  <tr
                    key={app.id}
                    className="cursor-pointer border-b border-slate-800 text-white transition-colors hover:bg-slate-800/50"
                    onClick={() => setSelectedApp(app)}
                  >
                    <td className="max-w-56 truncate px-4 py-3">{app.job_title}</td>
                    <td className="max-w-36 truncate px-4 py-3 text-slate-300">{app.company}</td>
                    <td className="hidden px-4 py-3 sm:table-cell">
                      <Badge variant="info" className="text-[10px]">{app.portal_name}</Badge>
                    </td>
                    <td className="px-4 py-3">
                      {app.match_score != null ? (
                        <span
                          className={`inline-flex items-center gap-1 text-xs font-medium ${
                            app.match_score >= 70
                              ? "text-green-400"
                              : app.match_score >= 40
                                ? "text-amber-400"
                                : "text-slate-500"
                          }`}
                        >
                          {Math.round(app.match_score)}%
                        </span>
                      ) : (
                        <span className="text-xs text-slate-600">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={statusInfo.variant}>{statusInfo.label}</Badge>
                    </td>
                    <td className="hidden px-4 py-3 md:table-cell">
                      {app.cover_letter_generated ? (
                        <CheckCircle className="h-4 w-4 text-green-400" />
                      ) : (
                        <XCircle className="h-4 w-4 text-slate-600" />
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {app.job_url && (
                        <a
                          href={app.job_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="inline-flex items-center gap-1 text-blue-400 hover:text-blue-300 transition-colors"
                        >
                          <ExternalLink className="h-3.5 w-3.5" />
                        </a>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Detail Modal */}
      <Modal
        isOpen={!!selectedApp}
        onClose={() => setSelectedApp(null)}
        title={selectedApp?.job_title || "Application Detail"}
      >
        {selectedApp && (
          <div className="space-y-4">
            {/* Header info */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-slate-400">Company</p>
                <p className="text-sm font-medium text-white">{selectedApp.company}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400">Portal</p>
                <p className="text-sm text-white">{selectedApp.portal_name}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400">Match Score</p>
                <p className="text-sm font-medium text-white">
                  {selectedApp.match_score != null ? `${Math.round(selectedApp.match_score)}%` : "—"}
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-400">Status</p>
                <Badge variant={STATUS_LABELS[selectedApp.status]?.variant || "default"}>
                  {STATUS_LABELS[selectedApp.status]?.label || selectedApp.status}
                </Badge>
              </div>
              <div>
                <p className="text-xs text-slate-400">Created</p>
                <p className="text-sm text-white">{new Date(selectedApp.created_at).toLocaleDateString()}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400">Submitted</p>
                <p className="text-sm text-white">
                  {selectedApp.submitted_at ? new Date(selectedApp.submitted_at).toLocaleDateString() : "—"}
                </p>
              </div>
            </div>

            {/* Cover letter */}
            {selectedApp.cover_letter_generated && selectedApp.cover_letter_text && (
              <div>
                <p className="mb-1 text-xs font-medium text-slate-400">Cover Letter</p>
                <div className="max-h-48 overflow-y-auto rounded-lg bg-slate-800 p-3 text-xs text-slate-300 whitespace-pre-wrap">
                  {selectedApp.cover_letter_text}
                </div>
              </div>
            )}

            {/* Error message */}
            {selectedApp.error_message && (
              <div>
                <p className="mb-1 text-xs font-medium text-red-400">Error</p>
                <div className="rounded-lg bg-red-900/20 border border-red-700/50 p-3 text-xs text-red-300">
                  {selectedApp.error_message}
                </div>
              </div>
            )}

            {/* Job link */}
            {selectedApp.job_url && (
              <a
                href={selectedApp.job_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-500 w-fit"
              >
                <ExternalLink className="h-4 w-4" />
                View Job Posting
              </a>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
