import { useState, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { runPipeline, getLatestPipelineRuns, cancelPipeline } from "../lib/pipeline";
import { listJobs, clearJobs } from "../lib/jobs";
import type { LatestRun } from "../lib/pipeline";
import type { StoredJob } from "../lib/jobs";
import { FileText, Globe, TrendingUp, CheckCircle, Play, Loader2, AlertCircle, XCircle, Square, ExternalLink } from "lucide-react";

// -- Status helpers --
const STATUS_LABELS: Record<string, string> = {
  pending: "Pendiente",
  queued: "En cola",
  scraping: "Scrapeando",
  matching: "Matcheando",
  applying: "Aplicando",
  notifying: "Notificando",
  completed: "Completado",
  failed: "Falló",
  cancelled: "Cancelado",
  dispatch_failed: "Error de envío",
};

const STATUS_BADGE: Record<string, "default" | "success" | "warning" | "danger" | "info"> = {
  pending: "default",
  queued: "info",
  scraping: "info",
  matching: "warning",
  applying: "warning",
  notifying: "info",
  completed: "success",
  failed: "danger",
  cancelled: "default",
  dispatch_failed: "danger",
};

function isActive(status: string): boolean {
  return ["pending", "queued", "scraping", "matching", "applying", "notifying"].includes(status);
}

function isCancellable(status: string): boolean {
  return ["pending", "queued", "scraping", "matching", "applying", "notifying"].includes(status);
}

const ACTIVE_PORTALS_COUNT = 4; // all built-in portals

export default function Dashboard() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [isRunning, setIsRunning] = useState(false);
  const [result, setResult] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Poll pipeline status every 5s when there are active runs
  const { data: pipelineStatus } = useQuery({
    queryKey: ["pipeline-latest"],
    queryFn: getLatestPipelineRuns,
    refetchInterval: (query) => {
      const data = query.state.data;
      return data?.has_active_runs ? 5_000 : false;
    },
  });

  const [cancelling, setCancelling] = useState<Set<string>>(new Set());
  const [showPipelineStatus, setShowPipelineStatus] = useState(true);
  const [clearingJobs, setClearingJobs] = useState(false);

  const activeCount = pipelineStatus?.runs.filter((r) => isActive(r.status)).length ?? 0;
  const totalDisplayed = pipelineStatus?.runs.length ?? 0;

  // Stored jobs
  const { data: storedJobs = [] } = useQuery({
    queryKey: ["stored-jobs"],
    queryFn: () => listJobs(20),
    refetchInterval: 30_000,
  });

  const handleRunPipeline = useCallback(async () => {
    setIsRunning(true);
    setResult(null);
    setShowPipelineStatus(true);
    try {
      const res = await runPipeline();
      setResult({ type: "success", message: res.message });
      queryClient.invalidateQueries({ queryKey: ["applications"] });
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      queryClient.invalidateQueries({ queryKey: ["pipeline-latest"] });
      queryClient.invalidateQueries({ queryKey: ["stored-jobs"] });
    } catch (err) {
      setResult({
        type: "error",
        message: err instanceof Error ? err.message : "Error al iniciar la búsqueda",
      });
    } finally {
      setIsRunning(false);
    }
  }, [queryClient]);

  const handleCancel = useCallback(async (runId: string) => {
    setCancelling((prev) => new Set(prev).add(runId));
    try {
      await cancelPipeline(runId);
      queryClient.invalidateQueries({ queryKey: ["pipeline-latest"] });
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    } catch (err) {
      setResult({
        type: "error",
        message: err instanceof Error ? err.message : "Error al cancelar la búsqueda",
      });
    } finally {
      setCancelling((prev) => {
        const next = new Set(prev);
        next.delete(runId);
        return next;
      });
    }
  }, [queryClient]);

  const handleDismissPipeline = useCallback(() => {
    queryClient.removeQueries({ queryKey: ["pipeline-latest"] });
    setShowPipelineStatus(false);
    setResult(null);
  }, [queryClient]);

  const handleClearJobs = useCallback(async () => {
    setClearingJobs(true);
    try {
      await clearJobs();
      queryClient.invalidateQueries({ queryKey: ["stored-jobs"] });
    } catch (err) {
      setResult({
        type: "error",
        message: err instanceof Error ? err.message : "Error al limpiar los trabajos",
      });
    } finally {
      setClearingJobs(false);
    }
  }, [queryClient]);

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">
            Welcome, {user?.name || user?.email}
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Overview of your job search activity.
          </p>
        </div>
        <button
          onClick={handleRunPipeline}
          disabled={isRunning}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isRunning ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Play className="h-4 w-4" />
          )}
          {isRunning ? "Buscando..." : "Iniciar búsqueda"}
        </button>
      </div>

      {/* Success / error banner */}
      {result && (
        <div
          className={`mb-6 flex items-center gap-2 rounded-lg border px-4 py-3 text-sm ${
            result.type === "success"
              ? "border-green-700/50 bg-green-900/20 text-green-400"
              : "border-red-700/50 bg-red-900/20 text-red-400"
          }`}
        >
          {result.type === "success" ? (
            <CheckCircle className="h-4 w-4 shrink-0" />
          ) : (
            <AlertCircle className="h-4 w-4 shrink-0" />
          )}
          {result.message}
        </div>
      )}

      {/* Live pipeline status */}
      {pipelineStatus && (pipelineStatus.has_active_runs || totalDisplayed > 0) && showPipelineStatus && (
        <Card className="mb-6">
          <div className="flex items-center gap-2 mb-4">
            {pipelineStatus.has_active_runs ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin text-blue-400" />
                <h2 className="text-sm font-semibold text-white">Búsqueda en progreso</h2>
                <span className="text-xs text-slate-500">
                  ({activeCount} activo{activeCount !== 1 ? "s" : ""})
                </span>
              </>
            ) : (
              <>
                <CheckCircle className="h-4 w-4 text-green-400" />
                <h2 className="text-sm font-semibold text-white">Última búsqueda</h2>
              </>
            )}
            <button
              onClick={handleDismissPipeline}
              className="ml-auto flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-slate-500 transition-colors hover:bg-slate-700 hover:text-white"
              title="Descartar historial"
            >
              <XCircle className="h-3 w-3" />
              Limpiar
            </button>
          </div>

          <div className="space-y-2">
            {pipelineStatus.runs.map((run: LatestRun) => (
              <div
                key={run.pipeline_run_id}
                className="flex items-center justify-between rounded-lg bg-slate-800/50 px-3 py-2"
              >
                <div className="flex items-center gap-2 min-w-0">
                  {isActive(run.status) ? (
                    <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-blue-400" />
                  ) : run.status === "cancelled" ? (
                    <Square className="h-3.5 w-3.5 shrink-0 text-slate-400" />
                  ) : run.status === "failed" || run.status === "dispatch_failed" ? (
                    <XCircle className="h-3.5 w-3.5 shrink-0 text-red-400" />
                  ) : (
                    <CheckCircle className="h-3.5 w-3.5 shrink-0 text-green-400" />
                  )}
                  <span className="truncate text-sm text-white">{run.portal_name}</span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {run.status === "failed" && run.error_msg && (
                    <span className="hidden sm:block max-w-48 truncate text-xs text-red-400" title={run.error_msg}>
                      {run.error_msg}
                    </span>
                  )}
                  <Badge variant={STATUS_BADGE[run.status] || "default"}>
                    {STATUS_LABELS[run.status] || run.status}
                  </Badge>
                  {isCancellable(run.status) && (
                    <button
                      onClick={() => handleCancel(run.pipeline_run_id)}
                      disabled={cancelling.has(run.pipeline_run_id)}
                      className="flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-slate-400 transition-colors hover:bg-slate-700 hover:text-red-400 disabled:opacity-50"
                      title="Cancelar búsqueda"
                    >
                      {cancelling.has(run.pipeline_run_id) ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        <XCircle className="h-3 w-3" />
                      )}
                      Cancelar
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Stats */}
      {(() => {
        const completed = pipelineStatus?.runs.filter((r) => r.status === "completed").length ?? 0;
        const total = pipelineStatus?.runs.length ?? 0;
        const jobsFound = storedJobs.length;
        const stats = [
          { label: "Trabajos encontrados", value: String(jobsFound), icon: FileText, color: "text-blue-500" },
          { label: "Portales activos", value: String(ACTIVE_PORTALS_COUNT), icon: Globe, color: "text-green-500" },
          {
            label: "Búsquedas",
            value: total > 0 ? `${completed}/${total}` : "--",
            icon: TrendingUp,
            color: "text-purple-500",
          },
          { label: "Match Average", value: "--", icon: CheckCircle, color: "text-amber-500" },
        ];
        return (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            {stats.map((stat) => {
              const Icon = stat.icon;
              return (
                <Card key={stat.label}>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-slate-400">{stat.label}</p>
                      <p className="text-2xl font-bold text-white mt-1">{stat.value}</p>
                    </div>
                    <Icon className={`w-8 h-8 ${stat.color} opacity-80`} />
                  </div>
                </Card>
              );
            })}
          </div>
        );
      })()}

      {/* Found Jobs */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">Trabajos encontrados</h2>
          <div className="flex items-center gap-2">
            {storedJobs.length > 0 && (
              <span className="text-xs text-slate-500">{storedJobs.length} trabajo(s)</span>
            )}
            {storedJobs.length > 0 && (
              <button
                onClick={handleClearJobs}
                disabled={clearingJobs}
                className="flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-slate-500 transition-colors hover:bg-slate-700 hover:text-red-400 disabled:opacity-50"
                title="Limpiar todos los trabajos guardados"
              >
                {clearingJobs ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <XCircle className="h-3 w-3" />
                )}
                Limpiar
              </button>
            )}
          </div>
        </div>

        {storedJobs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-slate-500">
            <FileText className="w-12 h-12 mb-3 opacity-40" />
            <p className="text-sm font-medium">Todavía no hay trabajos</p>
            <p className="text-xs mt-1 text-slate-600">
              Hacé clic en "Iniciar búsqueda" para empezar a buscar ofertas de tus portales habilitados
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700 text-left text-slate-400">
                  <th className="pb-2 pr-4 font-medium">Puesto</th>
                  <th className="pb-2 pr-4 font-medium">Empresa</th>
                  <th className="pb-2 pr-4 font-medium hidden sm:table-cell">Portal</th>
                  <th className="pb-2 pr-4 font-medium hidden md:table-cell">Ubicación</th>
                  <th className="pb-2 pr-4 font-medium">Match</th>
                  <th className="pb-2 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {[...storedJobs]
                  .sort((a, b) => {
                    const sa = a.match_score ?? -1;
                    const sb = b.match_score ?? -1;
                    return sb - sa;
                  })
                  .slice(0, 10)
                  .map((job: StoredJob) => (
                  <tr key={job.id} className="border-b border-slate-800 text-white hover:bg-slate-800/50">
                    <td className="py-2.5 pr-4 max-w-56 truncate">{job.title}</td>
                    <td className="py-2.5 pr-4 text-slate-300 max-w-36 truncate">{job.company}</td>
                    <td className="py-2.5 pr-4 hidden sm:table-cell">
                      <Badge variant="info" className="text-[10px]">{job.portal_name}</Badge>
                    </td>
                    <td className="py-2.5 pr-4 hidden md:table-cell text-slate-400">{job.location || "—"}</td>
                    <td className="py-2.5 pr-4">
                      {job.match_score != null ? (
                        <span
                          className={`inline-flex items-center gap-1 text-xs font-medium ${
                            job.match_score >= 70
                              ? "text-green-400"
                              : job.match_score >= 40
                                ? "text-amber-400"
                                : "text-slate-500"
                          }`}
                        >
                          {Math.round(job.match_score)}%
                        </span>
                      ) : (
                        <span className="text-xs text-slate-600">—</span>
                      )}
                    </td>
                    <td className="py-2.5">
                      {job.url ? (
                        <a
                          href={job.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-blue-400 hover:text-blue-300 transition-colors"
                        >
                          <ExternalLink className="h-3.5 w-3.5" />
                        </a>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
