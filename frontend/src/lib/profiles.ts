import { api, API_BASE, ApiError } from "./api";
import type {
  Profile,
  ProfileUpdate,
  ImportedProfile,
  CVParseResult,
  MergeRequest,
} from "../types";

export async function getMyProfile(): Promise<Profile> {
  return api<Profile>("/profiles");
}

export async function updateMyProfile(data: ProfileUpdate): Promise<Profile> {
  return api<Profile>("/profiles", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

// ---------------------------------------------------------------------------
// Import / CV API methods
// ---------------------------------------------------------------------------

export async function importLinkedin(url: string): Promise<ImportedProfile> {
  return api<ImportedProfile>("/profiles/import/linkedin", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

export async function importInfojobs(url: string): Promise<ImportedProfile> {
  return api<ImportedProfile>("/profiles/import/infojobs", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

export async function previewSave(data: MergeRequest): Promise<Profile> {
  return api<Profile>("/profiles/import/preview-save", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function uploadCv(file: File): Promise<CVParseResult> {
  const token = localStorage.getItem("token");
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/profiles/cv/upload`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(error.detail || "Upload failed", res.status);
  }
  return res.json();
}

export async function downloadCv(cvId: string): Promise<Blob> {
  const token = localStorage.getItem("token");
  const res = await fetch(`${API_BASE}/profiles/cv/download/${cvId}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new ApiError("Download failed", res.status);
  return res.blob();
}

export async function deleteCv(cvId: string): Promise<void> {
  return api<void>(`/profiles/cv/${cvId}`, { method: "DELETE" });
}
