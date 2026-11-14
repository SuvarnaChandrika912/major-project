"use client";

import { useState } from "react";
import { ShieldAlert, ShieldCheck, ShieldQuestion } from "lucide-react";
import type { Verification } from "@/types";
import { cn } from "@/utils/format";

const STYLES = {
  SUFFICIENT: { label: "Evidence verified", icon: ShieldCheck, cls: "border-emerald-200 bg-emerald-50 text-emerald-700" },
  PARTIAL: { label: "Partially supported", icon: ShieldQuestion, cls: "border-amber-200 bg-amber-50 text-amber-700" },
  INSUFFICIENT: { label: "Insufficient evidence", icon: ShieldAlert, cls: "border-red-200 bg-red-50 text-red-700" },
} as const;

export function VerificationBadge({ verification }: { verification?: Verification }) {
  const [open, setOpen] = useState(false);
  if (!verification) return null;
  const style = STYLES[verification.evidence_status] ?? STYLES.INSUFFICIENT;
  const Icon = style.icon;
  const notes = [...verification.warnings];
  if (verification.unsupported_claims.length) {
    notes.push(`${verification.unsupported_claims.length} unsupported statement(s) were removed from the answer.`);
  }

  return (
    <div className="text-xs">
      <button
        type="button"
        onClick={() => notes.length && setOpen((v) => !v)}
        className={cn("inline-flex items-center gap-1.5 rounded-md border px-2 py-1 font-medium", style.cls, !notes.length && "cursor-default")}
        aria-expanded={open}
      >
        <Icon className="h-3.5 w-3.5" />
        {style.label} · {Math.round(verification.confidence * 100)}% confidence
        {notes.length > 0 && <span className="opacity-70">({notes.length} note{notes.length > 1 ? "s" : ""})</span>}
      </button>
      {open && (
        <ul className="mt-2 list-disc space-y-1 rounded-lg bg-slate-50 py-2 pl-7 pr-3 text-slate-600">
          {notes.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
