"use client";

import { useEffect, useMemo, useState } from "react";
import { ExternalLink, Search } from "lucide-react";
import { Alert, Badge, Input, Modal, SkeletonList, statusTone } from "@/components/ui";
import { standardsService } from "@/services/bis";
import type { StandardDetail } from "@/types";
import { errorMessage, formatDate } from "@/utils/format";

export function StandardDetailModal({ standardId, onClose, onLoaded }: {
  standardId: number | null;
  onClose: () => void;
  onLoaded?: (s: StandardDetail) => void;
}) {
  const [detail, setDetail] = useState<StandardDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    if (standardId === null) return;
    standardsService
      .get(standardId)
      .then((d) => {
        setDetail(d);
        onLoaded?.(d);
      })
      .catch((err) => setError(errorMessage(err)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [standardId]);

  const clauses = useMemo(() => {
    if (!detail) return [];
    const f = filter.trim().toLowerCase();
    return f
      ? detail.clauses.filter((c) => c.text.toLowerCase().includes(f) || (c.clause_number ?? "").startsWith(f) || (c.section ?? "").toLowerCase().includes(f))
      : detail.clauses;
  }, [detail, filter]);

  return (
    <Modal open={standardId !== null} onClose={onClose} title={detail ? detail.standard_number : "Standard"} wide>
      {error && <Alert tone="error">{error}</Alert>}
      {!detail && !error && <SkeletonList rows={6} />}
      {detail && (
        <div className="space-y-5">
          <div>
            <h3 className="text-lg font-semibold text-slate-900">{detail.title}</h3>
            <div className="mt-2 flex flex-wrap gap-1.5">
              <Badge tone={statusTone(detail.status)}>{detail.status}</Badge>
              {detail.document?.document_version && <Badge>Version {detail.document.document_version}</Badge>}
              {detail.amendment_number && <Badge>Amendment {detail.amendment_number}</Badge>}
              {detail.publication_date && <Badge>Published {formatDate(detail.publication_date)}</Badge>}
              {detail.document && <Badge>{detail.document.page_count} pages</Badge>}
            </div>
            {detail.status !== "current" && (
              <Alert tone="warning" className="mt-3">
                This document is marked as <strong>{detail.status}</strong>. Check for a newer version before relying on it.
              </Alert>
            )}
            {detail.scope && (
              <div className="mt-4 rounded-lg bg-slate-50 p-3 text-sm text-slate-700">
                <p className="mb-1 text-xs font-semibold uppercase text-slate-500">Scope</p>
                <p className="whitespace-pre-line">{detail.scope}</p>
              </div>
            )}
            {detail.document?.source_url && (
              <a href={detail.document.source_url} target="_blank" rel="noopener noreferrer" className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-navy-700 hover:underline">
                Official source <ExternalLink className="h-4 w-4" />
              </a>
            )}
          </div>
          <div>
            <div className="mb-3 flex items-center justify-between gap-3">
              <p className="text-sm font-semibold text-slate-800">Clauses ({detail.clauses.length})</p>
              <div className="relative w-56">
                <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <Input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Filter clauses" className="h-9 pl-8" />
              </div>
            </div>
            <div className="space-y-2">
              {clauses.map((c) => (
                <div key={c.chunk_id} className="rounded-lg border border-slate-200 p-3">
                  <div className="mb-1.5 flex flex-wrap items-center gap-1.5 text-xs">
                    {c.clause_number && <Badge tone="navy">Clause {c.clause_number}</Badge>}
                    {c.section && <span className="font-medium text-slate-600">{c.section}</span>}
                    <span className="ml-auto text-slate-400">Page {c.page_number}</span>
                  </div>
                  <p className="whitespace-pre-line text-[13px] leading-relaxed text-slate-700">{c.text}</p>
                </div>
              ))}
              {clauses.length === 0 && <p className="py-6 text-center text-sm text-slate-500">No clauses match this filter.</p>}
            </div>
          </div>
        </div>
      )}
    </Modal>
  );
}
