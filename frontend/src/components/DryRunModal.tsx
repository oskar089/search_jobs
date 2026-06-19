import { Modal } from "./ui/Modal";

interface DryRunJob {
  title: string;
  company: string;
  location: string | null;
  description: string;
  url: string;
  salary_range: string | null;
  posted_at: string | null;
}

interface DryRunModalProps {
  isOpen: boolean;
  onClose: () => void;
  jobs: DryRunJob[];
  error?: string;
  isLoading: boolean;
}

export function DryRunModal({ isOpen, onClose, jobs, error, isLoading }: DryRunModalProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Dry Run Results">
      {isLoading ? (
        <div className="text-sm text-slate-400">Running dry-run...</div>
      ) : error ? (
        <div className="text-sm text-red-400">{error}</div>
      ) : jobs.length === 0 ? (
        <div className="text-sm text-slate-400">No jobs found.</div>
      ) : (
        <div className="space-y-4">
          <p className="text-sm text-slate-400">{jobs.length} job(s) found</p>
          {jobs.map((job, i) => (
            <div key={i} className="rounded-lg border border-slate-700 p-4">
              <h3 className="font-semibold text-white">{job.title}</h3>
              <p className="text-sm text-slate-300">
                {job.company}
                {job.location ? ` - ${job.location}` : ""}
              </p>
              {job.salary_range && (
                <p className="mt-1 text-xs text-green-400">{job.salary_range}</p>
              )}
              <p className="mt-2 text-xs text-slate-400 line-clamp-2">{job.description}</p>
              {job.url && (
                <a
                  href={job.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-2 inline-block text-xs text-blue-400 hover:underline"
                >
                  View Job
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </Modal>
  );
}
