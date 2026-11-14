"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, ChevronDown, CircleAlert, Loader2, Workflow } from "lucide-react";
import type { AgentTrace } from "@/types";
import { AGENT_LABELS, cn } from "@/utils/format";

const LIVE_STEPS = [
  "Detecting language",
  "Supervisor is classifying your request",
  "Specialist agents are searching BIS documents",
  "Verification agent is checking evidence",
  "Composing a source-grounded answer",
];

/** Animated progress shown while the multi-agent workflow runs. */
export function AgentProgress() {
  const [step, setStep] = useState(0);
  useEffect(() => {
    const timer = window.setInterval(() => setStep((s) => Math.min(s + 1, LIVE_STEPS.length - 1)), 2500);
    return () => window.clearInterval(timer);
  }, []);
  return (
    <div className="space-y-1.5" aria-live="polite">
      {LIVE_STEPS.map((label, i) => (
        <div key={label} className={cn("flex items-center gap-2 text-sm", i > step ? "text-slate-300" : "text-slate-600")}>
          {i < step ? (
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
          ) : i === step ? (
            <Loader2 className="h-4 w-4 animate-spin text-navy-600" />
          ) : (
            <span className="h-4 w-4 rounded-full border border-slate-200" />
          )}
          {label}
        </div>
      ))}
    </div>
  );
}

/** Collapsible record of which agents ran for an answer. */
export function AgentTraceView({ trace }: { trace?: AgentTrace[] }) {
  const [open, setOpen] = useState(false);
  if (!trace?.length) return null;
  return (
    <div className="text-xs">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-2 py-1 font-medium text-slate-600 hover:bg-slate-50"
        aria-expanded={open}
      >
        <Workflow className="h-3.5 w-3.5" />
        {trace.length} agents involved
        <ChevronDown className={cn("h-3.5 w-3.5 transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <ol className="mt-2 space-y-1.5 rounded-lg bg-slate-50 p-3">
          {trace.map((t, i) => (
            <li key={`${t.agent}-${i}`} className="flex items-start gap-2">
              {t.status === "completed" ? (
                <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-500" />
              ) : (
                <CircleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" />
              )}
              <div className="min-w-0">
                <span className="font-medium text-slate-700">{AGENT_LABELS[t.agent] ?? t.agent}</span>
                {t.duration_ms > 0 && <span className="ml-1 text-slate-400">{(t.duration_ms / 1000).toFixed(1)}s</span>}
                {t.summary && <p className="text-slate-500">{t.summary}</p>}
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
