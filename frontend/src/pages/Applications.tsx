import { Card } from "../components/ui/Card";
import { Briefcase } from "lucide-react";

export default function ApplicationsPage() {
  return (
    <div>
      <h1 className="mb-1 text-2xl font-bold text-white">Applications</h1>
      <p className="mb-6 text-sm text-slate-400">
        Track your submitted job applications.
      </p>

      <Card>
        <div className="flex flex-col items-center justify-center py-16 text-slate-500">
          <Briefcase className="mb-3 h-12 w-12 opacity-40" />
          <p className="text-sm font-medium">No applications yet</p>
          <p className="mt-1 max-w-sm text-center text-xs text-slate-600">
            Applications will appear here once the pipeline runs and matches jobs to
            your profile.
          </p>
        </div>
      </Card>
    </div>
  );
}
