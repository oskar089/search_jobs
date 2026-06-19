import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listPortals, createPortal, updatePortal, deletePortal, togglePortal, dryRunPortal } from "../lib/portals";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { PortalEditor } from "./PortalEditor";
import { DryRunModal } from "../components/DryRunModal";
import type { Portal, PortalCreate } from "../types";
import { Globe, Plus, Pencil, Trash2, Power, PowerOff, Play } from "lucide-react";

export default function PortalsPage() {
  const queryClient = useQueryClient();
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingPortal, setEditingPortal] = useState<Portal | undefined>(undefined);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [dryRunId, setDryRunId] = useState<string | null>(null);
  const [dryRunResult, setDryRunResult] = useState<{
    jobs: Array<{
      title: string;
      company: string;
      location: string | null;
      description: string;
      url: string;
      salary_range: string | null;
      posted_at: string | null;
    }>;
    error?: string;
  } | null>(null);
  const [dryRunLoading, setDryRunLoading] = useState(false);

  const { data: portals, isLoading } = useQuery({
    queryKey: ["portals"],
    queryFn: listPortals,
  });

  const createMutation = useMutation({
    mutationFn: createPortal,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["portals"] });
      setEditorOpen(false);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: PortalCreate }) =>
      updatePortal(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["portals"] });
      setEditorOpen(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deletePortal,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["portals"] });
      setDeletingId(null);
    },
  });

  const toggleMutation = useMutation({
    mutationFn: togglePortal,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["portals"] });
    },
  });

  const handleSave = (data: PortalCreate) => {
    if (editingPortal) {
      updateMutation.mutate({ id: editingPortal.id, data });
    } else {
      createMutation.mutate(data);
    }
  };

  const openEditor = (portal?: Portal) => {
    setEditingPortal(portal);
    setEditorOpen(true);
  };

  const closeEditor = () => {
    setEditorOpen(false);
    setEditingPortal(undefined);
  };

  const handleDryRun = async (id: string) => {
    setDryRunId(id);
    setDryRunLoading(true);
    setDryRunResult(null);
    try {
      const result = await dryRunPortal(id);
      setDryRunResult(result);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Dry-run failed";
      setDryRunResult({ jobs: [], error: message });
    } finally {
      setDryRunLoading(false);
    }
  };

  const closeDryRun = () => {
    setDryRunId(null);
    setDryRunResult(null);
  };

  if (isLoading) {
    return <div className="text-sm text-slate-400">Loading portals...</div>;
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Portals</h1>
          <p className="mt-1 text-sm text-slate-400">
            Configure job portal scraping sources.
          </p>
        </div>
        <Button onClick={() => openEditor()}>
          <Plus className="h-4 w-4" />
          Add Portal
        </Button>
      </div>

      {portals && portals.length === 0 ? (
        <Card>
          <div className="flex flex-col items-center justify-center py-16 text-slate-500">
            <Globe className="mb-3 h-12 w-12 opacity-40" />
            <p className="text-sm font-medium">No portals configured</p>
            <p className="mt-1 text-xs text-slate-600">
              Add a portal to start scraping job listings
            </p>
          </div>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {portals?.map((portal) => (
            <Card key={portal.id}>
              <div className="mb-3 flex items-start justify-between">
                <div className="min-w-0">
                  <h3 className="font-semibold text-white">{portal.name}</h3>
                  <p className="mt-0.5 truncate text-xs text-slate-400">
                    {portal.base_url}
                  </p>
                </div>
                <div className="flex shrink-0 gap-1.5">
                  {portal.is_builtin && <Badge variant="info">Built-in</Badge>}
                  <Badge variant={portal.is_enabled ? "success" : "default"}>
                    {portal.is_enabled ? "Enabled" : "Disabled"}
                  </Badge>
                </div>
              </div>

              <p className="mb-3 text-xs text-slate-500">
                Interval: every {portal.scrape_interval_min} min
              </p>

              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  onClick={() => toggleMutation.mutate(portal.id)}
                  title={portal.is_enabled ? "Disable" : "Enable"}
                >
                  {portal.is_enabled ? (
                    <PowerOff className="h-4 w-4" />
                  ) : (
                    <Power className="h-4 w-4" />
                  )}
                </Button>
                {!portal.is_builtin && (
                  <>
                    <Button
                      variant="ghost"
                      onClick={() => openEditor(portal)}
                      title="Edit"
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      onClick={() => setDeletingId(portal.id)}
                      title="Delete"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </>
                )}
                <Button
                  variant="secondary"
                  onClick={() => handleDryRun(portal.id)}
                  isLoading={dryRunLoading && dryRunId === portal.id}
                  title="Test Scrape"
                >
                  <Play className="h-4 w-4" />
                  Test
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      {deletingId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="mx-4 w-full max-w-sm rounded-lg border border-slate-700 bg-slate-800 p-6">
            <h3 className="mb-2 text-lg font-semibold text-white">Delete Portal</h3>
            <p className="mb-4 text-sm text-slate-400">
              Are you sure you want to delete this portal? This action cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
              <Button variant="ghost" onClick={() => setDeletingId(null)}>
                Cancel
              </Button>
              <Button
                variant="danger"
                onClick={() => deleteMutation.mutate(deletingId)}
                isLoading={deleteMutation.isPending}
              >
                Delete
              </Button>
            </div>
          </div>
        </div>
      )}

      <PortalEditor
        isOpen={editorOpen}
        onClose={closeEditor}
        onSave={handleSave}
        portal={editingPortal}
        isLoading={createMutation.isPending || updateMutation.isPending}
      />

      <DryRunModal
        isOpen={!!dryRunId}
        onClose={closeDryRun}
        jobs={dryRunResult?.jobs ?? []}
        error={dryRunResult?.error}
        isLoading={dryRunLoading}
      />
    </div>
  );
}
