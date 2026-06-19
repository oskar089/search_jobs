import { cn } from "../../lib/utils";
import type { InputHTMLAttributes } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
}

export function Input({ label, error, id, className, ...props }: InputProps) {
  const inputId = id || label.toLowerCase().replace(/\s+/g, "-");

  return (
    <div className="space-y-1">
      <label htmlFor={inputId} className="block text-sm font-medium text-slate-300">
        {label}
      </label>
      <input
        id={inputId}
        className={cn(
          "w-full rounded-lg border bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500",
          error ? "border-red-500" : "border-slate-600",
          className,
        )}
        {...props}
      />
      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  );
}
