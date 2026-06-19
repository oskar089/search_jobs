import { cn } from "../../lib/utils";
import type { ReactNode, HTMLAttributes } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
}

export function Card({ children, className, ...props }: CardProps) {
  return (
    <div className={cn("rounded-lg border border-slate-700 bg-slate-800 p-4", className)} {...props}>
      {children}
    </div>
  );
}
