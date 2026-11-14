"use client";

import { ProtectedPage } from "@/components/layout/ProtectedPage";
import { useState } from "react";
import { BookOpen, GitCompare, Search, X } from "lucide-react";
import { AnswerView } from "@/components/chat/AnswerView";
import { citationTitle } from "@/components/chat/CitationList";
import { AgentProgress } from "@/components/chat/AgentActivity";
import { StandardDetailModal } from "@/components/standards/StandardDetailModal";
import { Alert, Badge, Button, Card, EmptyState, Input, Modal, PageHeader, Select, SkeletonList, statusTone } from "@/components/ui";
import { useHashId } from "@/hooks/useHashId";
import { useRecentStandards } from "@/hooks/useRecentStandards";
import { standardsService } from "@/services/bis";
import type { ComparisonResult, StandardSearchHit, StandardSearchResponse } from "@/types";
import { errorMessage } from "@/utils/format";

const MODES = [
  { value: "auto", label: "Auto detect" },
  { value: "number", label: "Standard number" },
  { value: "keyword", label: "Keyword / product" },
  { value: "semantic", label: "Natural language" },
];

export default function StandardsPage() {
  return (
    <ProtectedPage>
      <StandardsPageContent />
    </ProtectedPage>
  );
}

function StandardsPageContent() {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState("auto");
  const [status, setStatus] = useState("");
  const [result, setResult] = useState<StandardSearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const hashId = useHashId("standard");
  const [pickedId, setOpenId] = useState<number | null | undefined>(undefined);
  const openId = pickedId === undefined ? hashId : pickedId;
  const [selected, setSelected] = useState<StandardSearchHit[]>([]);
  const [compareOpen, setCompareOpen] = useState(false);
  const [focus, setFocus] = useState("");
  const [comparison, setComparison] = useState<ComparisonResult | null>(null);
  const [comparing, setComparing] = useState(false);
  const [compareError, setCompareError] = useState<string | null>(null);
  const recent = useRecentStandards();

  const search = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      setResult(await standardsService.search(query.trim(), mode, status || undefined));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const toggleSelect = (hit: StandardSearchHit) => {
    if (!hit.standard) return;
    setSelected((prev) =>
      prev.some((s) => s.standard?.id === hit.standard?.id)
        ? prev.filter((s) => s.standard?.id !== hit.standard?.id)
        : prev.length >= 4
          ? prev
          : [...prev, hit],
    );
  };

  const runCompare = async () => {
    setComparing(true);
    setCompareError(null);
    setComparison(null);
    try {
      setComparison(await standardsService.compare(selected.map((s) => s.standard!.id), focus));
    } catch (err) {
      setCompareError(errorMessage(err));
    } finally {
      setComparing(false);
    }
  };

  return (
    <div>
      <PageHeader
        title="Find Indian Standards"
        description="Search indexed Indian Standards by number, product, keyword or a natural-language description."
        icon={<Search className="h-5 w-5" />}
      />

      <Card className="p-4">
        <form onSubmit={search} className="flex flex-col gap-3 md:flex-row">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="e.g. IS 1293, pressure cooker, requirements for steel wires…" className="pl-9" aria-label="Search standards" />
          </div>
          <Select value={mode} onChange={(e) => setMode(e.target.value)} className="md:w-48" aria-label="Search mode">
            {MODES.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
          </Select>
          <Select value={status} onChange={(e) => setStatus(e.target.value)} className="md:w-40" aria-label="Status filter">
            <option value="">Any status</option>
            <option value="current">Current</option>
            <option value="superseded">Superseded</option>
            <option value="withdrawn">Withdrawn</option>
          </Select>
          <Button type="submit" loading={loading}>Search</Button>
        </form>
      </Card>

      {selected.length > 0 && (
        <div className="sticky top-16 z-10 mt-4 flex flex-wrap items-center gap-2 rounded-xl border border-navy-200 bg-navy-50 px-4 py-3">
          <span className="text-sm font-medium text-navy-900">Compare:</span>
          {selected.map((s) => (
            <Badge key={s.standard!.id} tone="navy" className="bg-white">
              {s.standard!.standard_number}
              <button onClick={() => toggleSelect(s)} aria-label={`Remove ${s.standard!.standard_number}`}>
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
          <Button size="sm" className="ml-auto" disabled={selected.length < 2} onClick={() => setCompareOpen(true)}>
            <GitCompare className="h-4 w-4" /> Compare {selected.length}
          </Button>
        </div>
      )}

      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_280px]">
        <div className="space-y-3">
          {error && <Alert tone="error">{error}</Alert>}
          {loading && <Card className="p-5"><SkeletonList rows={4} /></Card>}
          {!loading && result?.message && <Alert tone={result.results.length ? "info" : "warning"}>{result.message}</Alert>}
          {!loading && !result && !error && (
            <Card>
              <EmptyState icon={<BookOpen className="h-5 w-5" />} title="Search the indexed standards" description="Results include matching clauses with page references from authorised BIS documents." />
            </Card>
          )}
          {!loading &&
            result?.results.map((hit) => {
              const id = hit.standard?.id;
              const isSelected = selected.some((s) => s.standard?.id === id);
              return (
                <Card key={`${hit.document_id}-${hit.standard_number}`} className="p-4">
                  <div className="flex items-start gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-semibold text-navy-900">{hit.standard_number ?? "Unnumbered document"}</p>
                        {hit.status && <Badge tone={statusTone(hit.status)}>{hit.status}</Badge>}
                      </div>
                      <p className="mt-0.5 text-sm text-slate-700">{hit.title}</p>
                      {hit.standard?.scope && <p className="mt-2 line-clamp-2 text-sm text-slate-500">{hit.standard.scope}</p>}
                    </div>
                    <div className="flex shrink-0 flex-col gap-2 sm:flex-row">
                      {id && (
                        <>
                          <Button size="sm" variant="secondary" onClick={() => setOpenId(id)}>View clauses</Button>
                          <Button size="sm" variant={isSelected ? "primary" : "ghost"} onClick={() => toggleSelect(hit)}>
                            <GitCompare className="h-4 w-4" /> {isSelected ? "Selected" : "Compare"}
                          </Button>
                        </>
                      )}
                    </div>
                  </div>
                  {hit.matched_clauses.length > 0 && (
                    <div className="mt-3 space-y-2 border-t border-slate-100 pt-3">
                      {hit.matched_clauses.map((c) => (
                        <div key={c.chunk_id} className="text-sm">
                          <p className="text-xs font-medium text-slate-500">{citationTitle(c)}</p>
                          <p className="line-clamp-2 text-slate-600">{c.excerpt}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </Card>
              );
            })}
        </div>
        <aside>
          <Card>
            <div className="border-b border-slate-100 px-4 py-3 text-sm font-semibold text-slate-800">Recently viewed</div>
            <div className="p-2">
              {recent.items.length === 0 ? (
                <p className="px-2 py-3 text-sm text-slate-500">Standards you open will appear here.</p>
              ) : (
                recent.items.map((s) => (
                  <button key={s.id} onClick={() => setOpenId(s.id)} className="block w-full rounded-lg px-2 py-2 text-left hover:bg-slate-50">
                    <p className="text-sm font-medium text-navy-800">{s.standard_number}</p>
                    <p className="truncate text-xs text-slate-500">{s.title}</p>
                  </button>
                ))
              )}
            </div>
          </Card>
        </aside>
      </div>

      <StandardDetailModal
        key={openId ?? "closed"}
        standardId={openId}
        onClose={() => {
          setOpenId(null);
          if (window.location.hash) window.history.replaceState(null, "", "/standards");
        }}
        onLoaded={(s) => recent.add({ id: s.id, standard_number: s.standard_number, title: s.title })}
      />

      <Modal open={compareOpen} onClose={() => setCompareOpen(false)} title="Compare standards" wide>
        <div className="space-y-4">
          <p className="text-sm text-slate-600">Comparing {selected.map((s) => s.standard!.standard_number).join(", ")}.</p>
          <div className="flex gap-2">
            <Input value={focus} onChange={(e) => setFocus(e.target.value)} placeholder="Optional focus, e.g. test methods or marking requirements" />
            <Button onClick={runCompare} loading={comparing}>Compare</Button>
          </div>
          {compareError && <Alert tone="error">{compareError}</Alert>}
          {comparing && <AgentProgress />}
          {comparison && <AnswerView answer={comparison.answer} citations={comparison.citations} verification={comparison.verification} />}
        </div>
      </Modal>
    </div>
  );
}
