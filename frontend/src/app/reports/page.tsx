"use client";

import { ProtectedPage } from "@/components/layout/ProtectedPage";
import { useState } from "react";
import { Download, FileBarChart, Plus, Search, Trash2 } from "lucide-react";
import { AgentProgress } from "@/components/chat/AgentActivity";
import { ReportViewer } from "@/components/dashboard/ReportViewer";
import { Alert, Badge, Button, Card, EmptyState, Field, Input, Modal, PageHeader, Select, SkeletonList, Textarea } from "@/components/ui";
import { useAsync } from "@/hooks/useAsync";
import { useHashId } from "@/hooks/useHashId";
import { standardsService } from "@/services/bis";
import { reportService } from "@/services/reports";
import type { ReportType, StandardSearchHit } from "@/types";
import { errorMessage, formatDate, REPORT_TYPE_LABELS } from "@/utils/format";

const TYPES = Object.entries(REPORT_TYPE_LABELS) as [ReportType, string][];

export default function ReportsPage() {
  return (
    <ProtectedPage>
      <ReportsPageContent />
    </ProtectedPage>
  );
}

function ReportsPageContent() {
  const [filter, setFilter] = useState<ReportType | "">("");
  const reports = useAsync(() => reportService.list(filter || undefined), [filter]);
  const hashId = useHashId("report");
  const [pickedId, setOpenId] = useState<number | null | undefined>(undefined);
  const openId = pickedId === undefined ? hashId : pickedId;
  const [error, setError] = useState<string | null>(null);
  const [genOpen, setGenOpen] = useState(false);
  const [form, setForm] = useState({ report_type: "compliance" as ReportType, product_name: "", product_category: "", specifications: "" });
  const [stdQuery, setStdQuery] = useState("");
  const [stdHits, setStdHits] = useState<StandardSearchHit[]>([]);
  const [selectedStds, setSelectedStds] = useState<{ id: number; number: string }[]>([]);
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);

  const searchStandards = async () => {
    if (!stdQuery.trim()) return;
    try {
      const res = await standardsService.search(stdQuery.trim());
      setStdHits(res.results.filter((h) => h.standard));
    } catch (err) {
      setGenError(errorMessage(err));
    }
  };

  const generate = async (e: React.FormEvent) => {
    e.preventDefault();
    setGenerating(true);
    setGenError(null);
    try {
      const report = await reportService.generate({ ...form, standard_ids: selectedStds.map((s) => s.id) });
      setGenOpen(false);
      setForm({ report_type: "compliance", product_name: "", product_category: "", specifications: "" });
      setSelectedStds([]);
      await reports.reload();
      setOpenId(report.id);
      window.dispatchEvent(new Event("notifications:changed"));
    } catch (err) {
      setGenError(errorMessage(err));
    } finally {
      setGenerating(false);
    }
  };

  const download = async (id: number, title: string) => {
    try {
      await reportService.download(id, title);
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const remove = async (id: number) => {
    if (!window.confirm("Delete this report permanently?")) return;
    try {
      await reportService.remove(id);
      reports.setData((reports.data ?? []).filter((r) => r.id !== id));
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <div>
      <PageHeader
        title="My Reports"
        description="Compliance reports, certification roadmaps, comparisons and laboratory recommendations you have generated."
        icon={<FileBarChart className="h-5 w-5" />}
        action={<Button onClick={() => setGenOpen(true)}><Plus className="h-4 w-4" /> Generate report</Button>}
      />
      <div className="mb-4 flex flex-wrap gap-2">
        <Button size="sm" variant={filter === "" ? "primary" : "secondary"} onClick={() => setFilter("")}>All</Button>
        {TYPES.map(([value, label]) => (
          <Button key={value} size="sm" variant={filter === value ? "primary" : "secondary"} onClick={() => setFilter(value)}>{label}</Button>
        ))}
      </div>
      {(error || reports.error) && <Alert tone="error" className="mb-4">{error || reports.error}</Alert>}
      <Card>
        {reports.loading ? (
          <div className="p-5"><SkeletonList rows={5} /></div>
        ) : !reports.data?.length ? (
          <EmptyState icon={<FileBarChart className="h-5 w-5" />} title="No reports yet" description="Generate a report here or save one from the Certification Guide or Compliance Workspace." />
        ) : (
          <ul className="divide-y divide-slate-100">
            {reports.data.map((r) => (
              <li key={r.id} className="flex flex-col gap-2 px-5 py-4 sm:flex-row sm:items-center">
                <button onClick={() => setOpenId(r.id)} className="min-w-0 flex-1 text-left">
                  <p className="truncate font-medium text-slate-800 hover:text-navy-700">{r.report_title}</p>
                  <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                    <Badge tone="navy">{REPORT_TYPE_LABELS[r.report_type]}</Badge>
                    {formatDate(r.created_at, true)}
                  </div>
                </button>
                <div className="flex gap-2">
                  <Button size="sm" variant="secondary" onClick={() => download(r.id, r.report_title)}><Download className="h-4 w-4" /> PDF</Button>
                  <Button size="sm" variant="ghost" onClick={() => remove(r.id)} aria-label={`Delete ${r.report_title}`}><Trash2 className="h-4 w-4 text-red-600" /></Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <ReportViewer
        key={openId ?? "closed"}
        reportId={openId}
        onClose={() => {
          setOpenId(null);
          if (window.location.hash) window.history.replaceState(null, "", "/reports");
        }}
        onDeleted={(id) => {
          setOpenId(null);
          reports.setData((reports.data ?? []).filter((r) => r.id !== id));
        }}
      />

      <Modal open={genOpen} onClose={() => !generating && setGenOpen(false)} title="Generate report">
        <form onSubmit={generate} className="space-y-4">
          {genError && <Alert tone="error">{genError}</Alert>}
          <Field label="Report type" htmlFor="rtype">
            <Select id="rtype" value={form.report_type} onChange={(e) => setForm({ ...form, report_type: e.target.value as ReportType })}>
              {TYPES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </Select>
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Product name" required htmlFor="rprod">
              <Input id="rprod" value={form.product_name} onChange={(e) => setForm({ ...form, product_name: e.target.value })} required minLength={2} />
            </Field>
            <Field label="Product category" htmlFor="rcat">
              <Input id="rcat" value={form.product_category} onChange={(e) => setForm({ ...form, product_category: e.target.value })} />
            </Field>
          </div>
          {form.report_type === "standard_comparison" ? (
            <Field label="Standards to compare" hint="Select 2 to 4 indexed standards.">
              <div className="flex gap-2">
                <Input value={stdQuery} onChange={(e) => setStdQuery(e.target.value)} placeholder="Search standards" />
                <Button type="button" variant="secondary" onClick={searchStandards}><Search className="h-4 w-4" /></Button>
              </div>
              <div className="mt-2 max-h-40 space-y-1 overflow-y-auto">
                {stdHits.map((h) => {
                  const checked = selectedStds.some((s) => s.id === h.standard!.id);
                  return (
                    <label key={h.standard!.id} className="flex items-center gap-2 rounded px-2 py-1 text-sm hover:bg-slate-50">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() =>
                          setSelectedStds(checked ? selectedStds.filter((s) => s.id !== h.standard!.id) : [...selectedStds, { id: h.standard!.id, number: h.standard!.standard_number }].slice(0, 4))
                        }
                      />
                      <span className="font-medium">{h.standard!.standard_number}</span>
                      <span className="truncate text-slate-500">{h.standard!.title}</span>
                    </label>
                  );
                })}
              </div>
              {selectedStds.length > 0 && <p className="text-xs text-slate-500">Selected: {selectedStds.map((s) => s.number).join(", ")}</p>}
            </Field>
          ) : (
            <Field label="Specifications" htmlFor="rspecs">
              <Textarea id="rspecs" rows={4} value={form.specifications} onChange={(e) => setForm({ ...form, specifications: e.target.value })} />
            </Field>
          )}
          {generating && <AgentProgress />}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setGenOpen(false)} disabled={generating}>Cancel</Button>
            <Button type="submit" loading={generating} disabled={form.product_name.trim().length < 2 || (form.report_type === "standard_comparison" && selectedStds.length < 2)}>
              Generate
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
