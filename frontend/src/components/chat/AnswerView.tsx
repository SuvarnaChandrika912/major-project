"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";
import type { Citation, Verification } from "@/types";
import { CitationList } from "./CitationList";
import { Markdown } from "./Markdown";
import { VerificationBadge } from "./VerificationBadge";

export function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      onClick={async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        window.setTimeout(() => setCopied(false), 1500);
      }}
      className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-slate-500 hover:bg-slate-100 hover:text-slate-700"
      aria-label="Copy answer"
    >
      {copied ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

/** Answer with clickable citations, verification status and expandable sources. */
export function AnswerView({ answer, citations, verification, actions }: {
  answer: string;
  citations: Citation[];
  verification?: Verification;
  actions?: React.ReactNode;
}) {
  const [active, setActive] = useState<number | null>(null);
  return (
    <div className="space-y-4">
      <Markdown content={answer} onCitationClick={setActive} />
      <div className="flex flex-wrap items-center gap-2">
        <VerificationBadge verification={verification} />
        <CopyButton text={answer} />
        {actions}
      </div>
      <CitationList citations={citations} active={active} onToggle={setActive} />
    </div>
  );
}
