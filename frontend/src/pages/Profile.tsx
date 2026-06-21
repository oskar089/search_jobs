import { useState, useEffect, type KeyboardEvent } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Linkedin, Globe, Plus, Trash2 } from "lucide-react";
import { cn } from "../lib/utils";
import { getMyProfile, updateMyProfile, importLinkedin, importInfojobs, previewSave } from "../lib/profiles";
import { Input } from "../components/ui/Input";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Modal } from "../components/ui/Modal";
import type { Profile, ImportedProfile, SkillItem, EducationItem, ExperienceItem } from "../types";

const EXPERIENCE_LEVELS = ["junior", "mid", "senior", "lead"];

const SKILL_LEVELS = [
  { value: "beginner", label: "Principiante" },
  { value: "intermediate", label: "Intermedio" },
  { value: "advanced", label: "Avanzado" },
  { value: "expert", label: "Experto" },
];

interface TagInputProps {
  label: string;
  tags: string[];
  onAdd: (tag: string) => void;
  onRemove: (index: number) => void;
  placeholder?: string;
}

function TagInput({ label, tags, onAdd, onRemove, placeholder }: TagInputProps) {
  const [input, setInput] = useState("");

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && input.trim()) {
      e.preventDefault();
      onAdd(input.trim());
      setInput("");
    }
  };

  return (
    <div className="space-y-1">
      <label className="block text-sm font-medium text-slate-300">{label}</label>
      <div className="flex flex-wrap gap-1.5 mb-2">
        {tags.map((tag, i) => (
          <Badge key={`${tag}-${i}`} variant="info">
            {tag}
            <button
              type="button"
              onClick={() => onRemove(i)}
              className="ml-1.5 text-blue-200 hover:text-white"
            >
              &times;
            </button>
          </Badge>
        ))}
      </div>
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder || "Type and press Enter to add"}
        className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
    </div>
  );
}

interface SkillTagInputProps {
  skills: SkillItem[];
  onAdd: (skill: SkillItem) => void;
  onRemove: (index: number) => void;
}

function SkillTagInput({ skills, onAdd, onRemove }: SkillTagInputProps) {
  const [name, setName] = useState("");
  const [level, setLevel] = useState("intermediate");

  const handleAdd = () => {
    if (name.trim()) {
      onAdd({ name: name.trim(), level });
      setName("");
      setLevel("intermediate");
    }
  };

  return (
    <div className="space-y-1">
      <label className="block text-sm font-medium text-slate-300">Habilidades</label>
      <div className="flex flex-wrap gap-1.5 mb-2">
        {skills.map((skill, i) => (
          <Badge key={`${skill.name}-${i}`} variant="info">
            {skill.name} ({skill.level})
            <button
              type="button"
              onClick={() => onRemove(i)}
              className="ml-1.5 text-blue-200 hover:text-white"
            >
              &times;
            </button>
          </Badge>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Nombre de la habilidad"
          className="flex-1 rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <select
          value={level}
          onChange={(e) => setLevel(e.target.value)}
          className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {SKILL_LEVELS.map((sl) => (
            <option key={sl.value} value={sl.value}>
              {sl.label}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={handleAdd}
          className="rounded-lg bg-blue-600 px-3 py-2 text-white hover:bg-blue-700"
        >
          <Plus className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

export default function ProfilePage() {
  const queryClient = useQueryClient();
  const [success, setSuccess] = useState("");
  const [form, setForm] = useState<Profile>({
    id: "",
    user_id: "",
    target_roles: [],
    tech_stack: [],
    experience_level: "mid",
    min_salary: null,
    max_salary: null,
    locations: [],
    remote_only: false,
    languages: [],
    is_active: true,
  });

  // Import section state
  const [provider, setProvider] = useState<"linkedin" | "infojobs">("linkedin");
  const [importUrl, setImportUrl] = useState("");
  const [importError, setImportError] = useState("");
  const [isImporting, setIsImporting] = useState(false);
  const [editData, setEditData] = useState<ImportedProfile | null>(null);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [saveError, setSaveError] = useState("");

  const { data: profile, isLoading: profileLoading } = useQuery({
    queryKey: ["my-profile"],
    queryFn: getMyProfile,
  });

  useEffect(() => {
    if (profile) {
      setForm(profile);
    }
  }, [profile]);

  const mutation = useMutation({
    mutationFn: updateMyProfile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["my-profile"] });
      setSuccess("Profile saved successfully");
      setTimeout(() => setSuccess(""), 3000);
    },
  });

  const previewMutation = useMutation({
    mutationFn: previewSave,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["my-profile"] });
      setIsPreviewOpen(false);
      setEditData(null);
      setImportUrl("");
      setSuccess("Perfil importado correctamente");
      setTimeout(() => setSuccess(""), 3000);
    },
    onError: (err: Error) => {
      setSaveError(`Error al guardar: ${err.message}`);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSuccess("");
    mutation.mutate({
      target_roles: form.target_roles,
      tech_stack: form.tech_stack,
      experience_level: form.experience_level,
      min_salary: form.min_salary,
      max_salary: form.max_salary,
      locations: form.locations,
      remote_only: form.remote_only,
      languages: form.languages,
      is_active: form.is_active,
    });
  };

  const handleImport = async () => {
    if (!importUrl.trim()) {
      setImportError("La URL no puede estar vacía");
      return;
    }
    setImportError("");
    setIsImporting(true);
    try {
      const data = provider === "linkedin"
        ? await importLinkedin(importUrl.trim())
        : await importInfojobs(importUrl.trim());
      setEditData(data);
      setIsPreviewOpen(true);
      setSaveError("");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Error al importar perfil";
      setImportError(message);
    } finally {
      setIsImporting(false);
    }
  };

  const handlePreviewSave = () => {
    if (!editData) return;
    setSaveError("");
    previewMutation.mutate({ preview_data: editData, strategy: "fill-empty" });
  };

  // Generic updater for top-level edit fields
  const updateEditField = <K extends keyof ImportedProfile>(key: K, value: ImportedProfile[K]) => {
    setEditData((prev) => (prev ? { ...prev, [key]: value } : prev));
  };

  const updateEducation = (index: number, field: keyof EducationItem, value: string | boolean | null) => {
    setEditData((prev) => {
      if (!prev) return prev;
      const education = prev.education.map((item, i) =>
        i === index ? { ...item, [field]: value } : item,
      );
      return { ...prev, education };
    });
  };

  const addEducation = () => {
    setEditData((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        education: [
          ...prev.education,
          {
            institution: "",
            degree: "",
            field: null,
            start_date: "",
            end_date: null,
            description: null,
          },
        ],
      };
    });
  };

  const removeEducation = (index: number) => {
    setEditData((prev) => {
      if (!prev) return prev;
      return { ...prev, education: prev.education.filter((_, i) => i !== index) };
    });
  };

  const updateExperience = (index: number, field: keyof ExperienceItem, value: string | boolean | null) => {
    setEditData((prev) => {
      if (!prev) return prev;
      const work_experience = prev.work_experience.map((item, i) =>
        i === index ? { ...item, [field]: value } : item,
      );
      return { ...prev, work_experience };
    });
  };

  const addExperience = () => {
    setEditData((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        work_experience: [
          ...prev.work_experience,
          {
            company: "",
            role: "",
            start_date: "",
            end_date: null,
            description: null,
            current: false,
          },
        ],
      };
    });
  };

  const removeExperience = (index: number) => {
    setEditData((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        work_experience: prev.work_experience.filter((_, i) => i !== index),
      };
    });
  };

  if (profileLoading) {
    return <div className="text-slate-400 text-sm">Loading profile...</div>;
  }

  const addTag = (field: keyof Pick<Profile, "target_roles" | "tech_stack" | "locations" | "languages">) => (tag: string) => {
    setForm((prev) => ({ ...prev, [field]: [...prev[field], tag] }));
  };

  const removeTag = (field: keyof Pick<Profile, "target_roles" | "tech_stack" | "locations" | "languages">) => (index: number) => {
    setForm((prev) => ({ ...prev, [field]: prev[field].filter((_, i) => i !== index) }));
  };

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-white mb-1">Profile</h1>
      <p className="text-slate-400 text-sm mb-6">Manage your job search profile and preferences.</p>

      {success && (
        <div className="mb-4 rounded-lg bg-green-900/40 border border-green-700 px-4 py-2 text-sm text-green-300">
          {success}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <Card>
          <h2 className="text-lg font-semibold text-white mb-4">Target Preferences</h2>
          <div className="space-y-4">
            <TagInput
              label="Target Roles"
              tags={form.target_roles}
              onAdd={addTag("target_roles")}
              onRemove={removeTag("target_roles")}
              placeholder="e.g. Frontend Developer"
            />
            <TagInput
              label="Tech Stack"
              tags={form.tech_stack}
              onAdd={addTag("tech_stack")}
              onRemove={removeTag("tech_stack")}
              placeholder="e.g. React, TypeScript"
            />

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Experience Level</label>
              <select
                value={form.experience_level}
                onChange={(e) => setForm((prev) => ({ ...prev, experience_level: e.target.value }))}
                className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {EXPERIENCE_LEVELS.map((level) => (
                  <option key={level} value={level}>
                    {level.charAt(0).toUpperCase() + level.slice(1)}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </Card>

        <Card>
          <h2 className="text-lg font-semibold text-white mb-4">Salary & Location</h2>
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Min Salary"
              type="number"
              value={form.min_salary ?? ""}
              onChange={(e) => setForm((prev) => ({ ...prev, min_salary: e.target.value ? Number(e.target.value) : null }))}
              placeholder="50000"
            />
            <Input
              label="Max Salary"
              type="number"
              value={form.max_salary ?? ""}
              onChange={(e) => setForm((prev) => ({ ...prev, max_salary: e.target.value ? Number(e.target.value) : null }))}
              placeholder="120000"
            />
          </div>

          <div className="mt-4">
            <TagInput
              label="Locations"
              tags={form.locations}
              onAdd={addTag("locations")}
              onRemove={removeTag("locations")}
              placeholder="e.g. New York, Remote"
            />
          </div>

          <div className="mt-4">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={form.remote_only}
                onChange={(e) => setForm((prev) => ({ ...prev, remote_only: e.target.checked }))}
                className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-slate-300">Remote only</span>
            </label>
          </div>
        </Card>

        <Card>
          <h2 className="text-lg font-semibold text-white mb-4">Languages & Status</h2>
          <div className="space-y-4">
            <TagInput
              label="Languages"
              tags={form.languages}
              onAdd={addTag("languages")}
              onRemove={removeTag("languages")}
              placeholder="e.g. English, Spanish"
            />

            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) => setForm((prev) => ({ ...prev, is_active: e.target.checked }))}
                className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-slate-300">
                Active — include my profile in job matching
              </span>
            </label>
          </div>
        </Card>

        {/* Importar perfil section */}
        <Card>
          <h2 className="text-lg font-semibold text-white mb-4">Importar perfil</h2>
          <div className="space-y-4">
            {/* Provider selector */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Proveedor</label>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setProvider("linkedin")}
                  className={cn(
                    "flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors",
                    provider === "linkedin"
                      ? "bg-blue-600 text-white"
                      : "bg-slate-700 text-slate-300 hover:bg-slate-600",
                  )}
                >
                  <Linkedin className="h-4 w-4" />
                  LinkedIn
                </button>
                <button
                  type="button"
                  onClick={() => setProvider("infojobs")}
                  className={cn(
                    "flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors",
                    provider === "infojobs"
                      ? "bg-blue-600 text-white"
                      : "bg-slate-700 text-slate-300 hover:bg-slate-600",
                  )}
                >
                  <Globe className="h-4 w-4" />
                  Infojobs
                </button>
              </div>
            </div>

            {/* URL input */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">URL del perfil</label>
              <input
                type="url"
                value={importUrl}
                onChange={(e) => {
                  setImportUrl(e.target.value);
                  if (importError) setImportError("");
                }}
                placeholder={
                  provider === "linkedin"
                    ? "https://linkedin.com/in/tu-perfil"
                    : "https://infojobs.net/tu-perfil"
                }
                className={cn(
                  "w-full rounded-lg border bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500",
                  importError ? "border-red-500" : "border-slate-600",
                )}
              />
              {importError && <p className="mt-1 text-xs text-red-400">{importError}</p>}
            </div>

            {/* Import button */}
            <Button type="button" variant="primary" isLoading={isImporting} onClick={handleImport}>
              Importar
            </Button>
          </div>
        </Card>

        <div className="flex justify-end">
          <Button type="submit" variant="primary" isLoading={mutation.isPending}>
            Save Profile
          </Button>
        </div>
      </form>

      {/* Preview modal */}
      <Modal isOpen={isPreviewOpen} onClose={() => setIsPreviewOpen(false)} title="Vista previa — Importar perfil">
        {editData && (
          <div className="space-y-6">
            {/* Headline */}
            <Input
              label="Título profesional"
              value={editData.headline ?? ""}
              onChange={(e) => updateEditField("headline", e.target.value || null)}
            />

            {/* Summary */}
            <div className="space-y-1">
              <label className="block text-sm font-medium text-slate-300">Resumen</label>
              <textarea
                value={editData.summary ?? ""}
                onChange={(e) => updateEditField("summary", e.target.value || null)}
                rows={4}
                className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Skills */}
            <SkillTagInput
              skills={editData.skills}
              onAdd={(skill) => updateEditField("skills", [...editData.skills, skill])}
              onRemove={(index) =>
                updateEditField(
                  "skills",
                  editData.skills.filter((_, i) => i !== index),
                )
              }
            />

            {/* Education */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="block text-sm font-medium text-slate-300">Educación</label>
                <button
                  type="button"
                  onClick={addEducation}
                  className="flex items-center gap-1 text-sm text-blue-400 hover:text-blue-300"
                >
                  <Plus className="h-3.5 w-3.5" />
                  Agregar educación
                </button>
              </div>
              {editData.education.map((item, i) => (
                <Card key={i} className="relative">
                  <button
                    type="button"
                    onClick={() => removeEducation(i)}
                    className="absolute top-2 right-2 text-slate-400 hover:text-red-400"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                  <div className="grid grid-cols-2 gap-3 pr-6">
                    <Input
                      label="Institución"
                      value={item.institution}
                      onChange={(e) => updateEducation(i, "institution", e.target.value)}
                    />
                    <Input
                      label="Título"
                      value={item.degree}
                      onChange={(e) => updateEducation(i, "degree", e.target.value)}
                    />
                    <Input
                      label="Campo"
                      value={item.field ?? ""}
                      onChange={(e) => updateEducation(i, "field", e.target.value || null)}
                    />
                    <Input
                      label="Fecha inicio"
                      type="text"
                      value={item.start_date}
                      onChange={(e) => updateEducation(i, "start_date", e.target.value)}
                    />
                    <Input
                      label="Fecha fin"
                      type="text"
                      value={item.end_date ?? ""}
                      onChange={(e) => updateEducation(i, "end_date", e.target.value || null)}
                    />
                  </div>
                  <div className="mt-3">
                    <label className="block text-sm font-medium text-slate-300 mb-1">
                      Descripción
                    </label>
                    <textarea
                      value={item.description ?? ""}
                      onChange={(e) => updateEducation(i, "description", e.target.value || null)}
                      rows={2}
                      className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </Card>
              ))}
            </div>

            {/* Work Experience */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="block text-sm font-medium text-slate-300">
                  Experiencia laboral
                </label>
                <button
                  type="button"
                  onClick={addExperience}
                  className="flex items-center gap-1 text-sm text-blue-400 hover:text-blue-300"
                >
                  <Plus className="h-3.5 w-3.5" />
                  Agregar experiencia
                </button>
              </div>
              {editData.work_experience.map((item, i) => (
                <Card key={i} className="relative">
                  <button
                    type="button"
                    onClick={() => removeExperience(i)}
                    className="absolute top-2 right-2 text-slate-400 hover:text-red-400"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                  <div className="grid grid-cols-2 gap-3 pr-6">
                    <Input
                      label="Empresa"
                      value={item.company}
                      onChange={(e) => updateExperience(i, "company", e.target.value)}
                    />
                    <Input
                      label="Cargo"
                      value={item.role}
                      onChange={(e) => updateExperience(i, "role", e.target.value)}
                    />
                    <Input
                      label="Fecha inicio"
                      type="text"
                      value={item.start_date}
                      onChange={(e) => updateExperience(i, "start_date", e.target.value)}
                    />
                    <Input
                      label="Fecha fin"
                      type="text"
                      value={item.end_date ?? ""}
                      onChange={(e) => updateExperience(i, "end_date", e.target.value || null)}
                    />
                  </div>
                  <div className="mt-3 space-y-3">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={item.current}
                        onChange={(e) => updateExperience(i, "current", e.target.checked)}
                        className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="text-sm text-slate-300">Trabajo actual</span>
                    </label>
                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-1">
                        Descripción
                      </label>
                      <textarea
                        value={item.description ?? ""}
                        onChange={(e) => updateExperience(i, "description", e.target.value || null)}
                        rows={2}
                        className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>
                </Card>
              ))}
            </div>

            {/* Save error */}
            {saveError && (
              <div className="rounded-lg bg-red-900/40 border border-red-700 px-4 py-2 text-sm text-red-300">
                {saveError}
              </div>
            )}

            {/* Modal footer buttons */}
            <div className="flex justify-end gap-3 pt-4 border-t border-slate-700">
              <Button type="button" variant="secondary" onClick={() => setIsPreviewOpen(false)}>
                Cancelar
              </Button>
              <Button
                type="button"
                variant="primary"
                isLoading={previewMutation.isPending}
                onClick={handlePreviewSave}
              >
                Guardar
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
