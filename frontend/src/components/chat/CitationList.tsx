"use client";

import { useEffect, useRef } from "react";
import { ChevronDown, ExternalLink, FileText } from "lucide-react";
import { Badge, statusTone } from "@/components/ui";
import type { Citation } from "@/types";
import { cn, DOCUMENT_TYPE_LABELS } from "@/utils/format";

export function citationTitle(c: Citation): string {
  const parts = [c.standard_number || c.standard_title || "Source document"];
  if (c.clause_number) parts.push(`Clause ${c.clause_number}`);
  if (c.page_number) parts.push(`p. ${c.page_number}`);
  return parts.join(" · ");
}

export function CitationList({ citations, active, onToggle }: {
  citations: Citation[];
  active: number | null;
  onToggle: (index: number | null) => void;
}) {
  const refs = useRef<Record<number, HTMLDivElement | null>>({});

  useEffect(() => {
    if (active !== null) refs.current[active]?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [active]);

  if (!citations.length) return null;
  return (
    <div className="space-y-1.5">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Sources ({citations.length})</p>
      {citations.map((c) => {
        const open = active === c.index;
        return (
          <div
            key={`${c.chunk_id}-${c.index}`}
            ref={(el) => {
              refs.current[c.index] = el;
            }}
            className={cn("rounded-lg border bg-white transition-colors", open ? "border-navy-300" : "border-slate-200")}
          >
            <button
              type="button"
              onClick={() => onToggle(open ? null : c.index)}
              className="flex w-full items-center gap-2.5 px-3 py-2 text-left"
              aria-expanded={open}
            >
              <span className="flex h-5 min-w-5 items-center justify-center rounded bg-navy-50 px-1 text-[11px] font-semibold text-navy-700">
                {c.index}
              </span>
              <FileText className="h-4 w-4 shrink-0 text-slate-400" />
              <span className="min-w-0 flex-1 truncate text-sm font-medium text-slate-700">{citationTitle(c)}</span>
              {c.document_status && c.document_status !== "current" && (
                <Badge tone={statusTone(c.document_status)}>{c.document_status}</Badge>
              )}
              <ChevronDown className={cn("h-4 w-4 shrink-0 text-slate-400 transition-transform", open && "rotate-180")} />
            </button>
            {open && (
              <div className="space-y-2 border-t border-slate-100 px-3 py-3 text-sm">
                {c.standard_title && <p className="font-medium text-slate-800">{c.standard_title}</p>}
                <div className="flex flex-wrap gap-1.5">
                  {c.document_type && <Badge tone="navy">{DOCUMENT_TYPE_LABELS[c.document_type] ?? c.document_type}</Badge>}
                  {c.section && <Badge>{c.section}</Badge>}
                  {c.document_version && <Badge>Version {c.document_version}</Badge>}
                  {c.amendment_number && <Badge>Amendment {c.amendment_number}</Badge>}
                </div>
                <blockquote className="whitespace-pre-line border-l-2 border-navy-200 pl-3 text-[13px] leading-relaxed text-slate-600">
                  {c.excerpt}
                </blockquote>
                {c.source_url && (
                  <a
                    href={c.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-[13px] font-medium text-navy-700 hover:underline"
                  >
                    Official source <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
