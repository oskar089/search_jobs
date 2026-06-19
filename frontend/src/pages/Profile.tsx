import { useState, useEffect, type KeyboardEvent } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getMyProfile, updateMyProfile } from "../lib/profiles";
import { Input } from "../components/ui/Input";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import type { Profile } from "../types";

const EXPERIENCE_LEVELS = ["junior", "mid", "senior", "lead"];

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
        placeholder={placeholder || `Type and press Enter to add`}
        className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
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

        <div className="flex justify-end">
          <Button type="submit" variant="primary" isLoading={mutation.isPending}>
            Save Profile
          </Button>
        </div>
      </form>
    </div>
  );
}
