"use client";

import { AlertCircle, CheckCircle2, Info, Loader2, TriangleAlert, X } from "lucide-react";
import { forwardRef } from "react";
import { cn } from "@/utils/format";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
type ButtonSize = "sm" | "md" | "lg";

const buttonVariants: Record<ButtonVariant, string> = {
  primary: "bg-navy-900 text-white hover:bg-navy-800 disabled:bg-navy-300",
  secondary: "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 disabled:text-slate-400",
  ghost: "text-slate-600 hover:bg-slate-100 disabled:text-slate-300",
  danger: "bg-red-600 text-white hover:bg-red-700 disabled:bg-red-300",
};
const buttonSizes: Record<ButtonSize, string> = {
  sm: "h-8 px-3 text-sm gap-1.5",
  md: "h-10 px-4 text-sm gap-2",
  lg: "h-11 px-5 text-[15px] gap-2",
};

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", loading, className, children, disabled, ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={cn(
        "inline-flex items-center justify-center rounded-lg font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-navy-400 disabled:cursor-not-allowed",
        buttonVariants[variant],
        buttonSizes[size],
        className,
      )}
      {...props}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
});

export function Card({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("rounded-xl border border-slate-200 bg-white shadow-sm", className)} {...props}>
      {children}
    </div>
  );
}

export function CardHeader({ title, description, action, icon }: {
  title: string;
  description?: string;
  action?: React.ReactNode;
  icon?: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-slate-100 px-5 py-4">
      <div className="flex items-start gap-3">
        {icon && <div className="mt-0.5 text-navy-700">{icon}</div>}
        <div>
          <h3 className="text-[15px] font-semibold text-slate-900">{title}</h3>
          {description && <p className="mt-0.5 text-sm text-slate-500">{description}</p>}
        </div>
      </div>
      {action}
    </div>
  );
}

const fieldBase =
  "w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-800 placeholder:text-slate-400 focus:border-navy-400 focus:outline-none focus:ring-2 focus:ring-navy-100 disabled:bg-slate-50";

export const Input = forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(function Input(
  { className, ...props },
  ref,
) {
  return <input ref={ref} className={cn(fieldBase, "h-10", className)} {...props} />;
});

export const Textarea = forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  function Textarea({ className, ...props }, ref) {
    return <textarea ref={ref} className={cn(fieldBase, "py-2", className)} {...props} />;
  },
);

export const Select = forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(function Select(
  { className, children, ...props },
  ref,
) {
  return (
    <select ref={ref} className={cn(fieldBase, "h-10 pr-8", className)} {...props}>
      {children}
    </select>
  );
});

export function Field({ label, hint, required, children, htmlFor }: {
  label: string;
  hint?: string;
  required?: boolean;
  children: React.ReactNode;
  htmlFor?: string;
}) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={htmlFor} className="block text-sm font-medium text-slate-700">
        {label}
        {required && <span className="ml-0.5 text-red-500">*</span>}
      </label>
      {children}
      {hint && <p className="text-xs text-slate-500">{hint}</p>}
    </div>
  );
}

type BadgeTone = "neutral" | "navy" | "green" | "amber" | "red" | "blue";
const badgeTones: Record<BadgeTone, string> = {
  neutral: "bg-slate-100 text-slate-700",
  navy: "bg-navy-50 text-navy-800",
  green: "bg-emerald-50 text-emerald-700",
  amber: "bg-amber-50 text-amber-700",
  red: "bg-red-50 text-red-700",
  blue: "bg-sky-50 text-sky-700",
};

export function Badge({ tone = "neutral", className, children }: { tone?: BadgeTone; className?: string; children: React.ReactNode }) {
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium", badgeTones[tone], className)}>
      {children}
    </span>
  );
}

export function statusTone(status: string | null | undefined): BadgeTone {
  switch (status) {
    case "current":
    case "indexed":
    case "meets":
    case "SUFFICIENT":
    case "completed":
      return "green";
    case "superseded":
    case "processing":
    case "pending":
    case "missing_information":
    case "PARTIAL":
      return "amber";
    case "withdrawn":
    case "failed":
    case "does_not_meet":
    case "INSUFFICIENT":
    case "timeout":
      return "red";
    default:
      return "neutral";
  }
}

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={cn("h-5 w-5 animate-spin text-navy-600", className)} />;
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-md bg-slate-200/70", className)} />;
}

export function SkeletonList({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="space-y-2">
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="h-3 w-1/2" />
        </div>
      ))}
    </div>
  );
}

type AlertTone = "info" | "success" | "warning" | "error";
const alertStyles: Record<AlertTone, { box: string; icon: React.ReactNode }> = {
  info: { box: "border-sky-200 bg-sky-50 text-sky-800", icon: <Info className="h-4 w-4" /> },
  success: { box: "border-emerald-200 bg-emerald-50 text-emerald-800", icon: <CheckCircle2 className="h-4 w-4" /> },
  warning: { box: "border-amber-200 bg-amber-50 text-amber-800", icon: <TriangleAlert className="h-4 w-4" /> },
  error: { box: "border-red-200 bg-red-50 text-red-800", icon: <AlertCircle className="h-4 w-4" /> },
};

export function Alert({ tone = "info", title, children, onClose, className }: {
  tone?: AlertTone;
  title?: string;
  children?: React.ReactNode;
  onClose?: () => void;
  className?: string;
}) {
  const style = alertStyles[tone];
  return (
    <div role={tone === "error" ? "alert" : "status"} className={cn("flex gap-2.5 rounded-lg border px-3.5 py-3 text-sm", style.box, className)}>
      <div className="mt-0.5 shrink-0">{style.icon}</div>
      <div className="min-w-0 flex-1">
        {title && <p className="font-medium">{title}</p>}
        {children && <div className={cn(title && "mt-0.5", "opacity-90")}>{children}</div>}
      </div>
      {onClose && (
        <button onClick={onClose} aria-label="Dismiss" className="shrink-0 opacity-60 hover:opacity-100">
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}

export function EmptyState({ icon, title, description, action }: {
  icon: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-12 text-center">
      <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-navy-50 text-navy-700">{icon}</div>
      <p className="font-medium text-slate-800">{title}</p>
      {description && <p className="mt-1 max-w-md text-sm text-slate-500">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function PageHeader({ title, description, icon, action }: {
  title: string;
  description?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div className="flex items-start gap-3">
        {icon && <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-navy-900 text-white">{icon}</div>}
        <div>
          <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">{title}</h1>
          {description && <p className="mt-1 text-sm text-slate-500">{description}</p>}
        </div>
      </div>
      {action}
    </div>
  );
}

export function Modal({ open, onClose, title, children, wide }: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  wide?: boolean;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={cn("max-h-[90vh] w-full overflow-y-auto rounded-xl bg-white shadow-xl", wide ? "max-w-4xl" : "max-w-lg")}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 flex items-center justify-between border-b border-slate-100 bg-white px-5 py-4">
          <h2 className="font-semibold text-slate-900">{title}</h2>
          <button onClick={onClose} aria-label="Close" className="rounded-md p-1 text-slate-500 hover:bg-slate-100">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}
