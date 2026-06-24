import { api } from "./api";

export interface PipelineRunResult {
  pipeline_run_id: string;
  portal_id: string;
  portal_name: string;
  status: string;
}

export interface PipelineRunResponse {
  message: string;
  runs: PipelineRunResult[];
}

export function runPipeline(): Promise<PipelineRunResponse> {
  return api<PipelineRunResponse>("/pipeline/run", { method: "POST" });
}

// --- Latest runs (for status polling) ---

export interface LatestRun {
  pipeline_run_id: string;
  portal_name: string;
  status: string;
  trigger: string;
  created_at: string;
  completed_at: string | null;
  error_step: string | null;
  error_msg: string | null;
}

export interface LatestPipelineResponse {
  runs: LatestRun[];
  has_active_runs: boolean;
}

export function getLatestPipelineRuns(): Promise<LatestPipelineResponse> {
  return api<LatestPipelineResponse>("/pipeline/latest");
}

// --- Cancel ---

export interface CancelResponse {
  status: string;
  pipeline_run_id: string;
}

export function cancelPipeline(runId: string): Promise<CancelResponse> {
  return api<CancelResponse>(`/pipeline/${runId}/cancel`, { method: "POST" });
}
