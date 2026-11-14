"use client";

import { ProtectedPage } from "@/components/layout/ProtectedPage";
import Link from "next/link";
import { useState } from "react";
import { ClipboardCheck, FileUp, Plus, X } from "lucide-react";
import { AgentProgress } from "@/components/chat/AgentActivity";
import { AnswerView } from "@/components/chat/AnswerView";
import { ChecklistTable } from "@/components/compliance/ChecklistTable";
import { Alert, Badge, Button, Card, CardHeader, Field, Input, PageHeader, Textarea } from "@/components/ui";
import { useAsync } from "@/hooks/useAsync";
import { reportService } from "@/services/reports";
import type { ComplianceResult } from "@/types";
import { errorMessage, timeAgo } from "@/utils/format";

export default function CompliancePage() {
  return (
    <ProtectedPage>
      <CompliancePageContent />
    </ProtectedPage>
  );
}

function CompliancePageContent() {
  const [productName, setProductName] = useState("");
  const [category, setCategory] = useState("");
  const [targetStandard, setTargetStandard] = useState("");
  const [specs, setSpecs] = useState("");
  const [docInput, setDocInput] = useState("");
  const [documents, setDocuments] = useState<string[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [saveReport, setSaveReport] = useState(true);
  const [result, setResult] = useState<ComplianceResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const previous = useAsync(() => reportService.list("compliance"));

  const addDocument = () => {
    const d = docInput.trim();
    if (d && !documents.includes(d)) setDocuments([...documents, d]);
    setDocInput("");
  };

  const analyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (file && file.size > 20 * 1024 * 1024) return setError("Technical documents must be smaller than 20 MB.");
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await reportService.analyzeCompliance(
        {
          product_name: productName.trim(),
          product_category: category.trim(),
          specifications: specs.trim(),
          available_documents: documents,
          target_standard: targetStandard.trim() || null,
          save_report: saveReport,
        },
        file,
      );
      setResult(res);
      if (res.report_id) {
        void previous.reload();
        window.dispatchEvent(new Event("notifications:changed"));
      }
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const counts = result?.status_counts ?? {};

  return (
    <div>
      <PageHeader
        title="Compliance Workspace"
        description="Create a product profile and get a preliminary checklist mapped to clauses of the applicable Indian Standards."
        icon={<ClipboardCheck className="h-5 w-5" />}
      />
      <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
        <div className="space-y-6">
          <Card>
            <CardHeader title="Product profile" description="Only information you provide is assessed. Nothing here is an official BIS approval." />
            <form onSubmit={analyze} className="space-y-4 p-5">
              <div className="grid gap-4 sm:grid-cols-3">
                <Field label="Product name" required htmlFor="pname">
                  <Input id="pname" value={productName} onChange={(e) => setProductName(e.target.value)} required minLength={2} />
                </Field>
                <Field label="Product category" htmlFor="pcat">
                  <Input id="pcat" value={category} onChange={(e) => setCategory(e.target.value)} />
                </Field>
                <Field label="Target standard" hint="Optional, e.g. IS 1293" htmlFor="pstd">
                  <Input id="pstd" value={targetStandard} onChange={(e) => setTargetStandard(e.target.value)} />
                </Field>
              </div>
              <Field label="Specifications" hint="One per line: materials, ratings, dimensions, markings, test results…" htmlFor="pspecs">
                <Textarea id="pspecs" rows={6} value={specs} onChange={(e) => setSpecs(e.target.value)} />
              </Field>
              <Field label="Documents you already have" htmlFor="pdocs">
                <div className="flex gap-2">
                  <Input
                    id="pdocs"
                    value={docInput}
                    onChange={(e) => setDocInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        addDocument();
                      }
                    }}
                    placeholder="e.g. Test report, factory layout, QC plan"
                  />
                  <Button type="button" variant="secondary" onClick={addDocument}><Plus className="h-4 w-4" /> Add</Button>
                </div>
                {documents.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {documents.map((d) => (
                      <Badge key={d} tone="navy">
                        {d}
                        <button type="button" onClick={() => setDocuments(documents.filter((x) => x !== d))} aria-label={`Remove ${d}`}>
                          <X className="h-3 w-3" />
                        </button>
                      </Badge>
                    ))}
                  </div>
                )}
              </Field>
              <Field label="Technical document (PDF)" hint="Optional. Used only for this analysis and never added to the knowledge base.">
                <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-dashed border-slate-300 px-4 py-3 text-sm text-slate-600 hover:bg-slate-50">
                  <FileUp className="h-5 w-5 text-slate-400" />
                  <span className="truncate">{file ? file.name : "Choose a PDF file"}</span>
                  {file && (
                    <button type="button" className="ml-auto text-slate-400 hover:text-red-600" onClick={(e) => { e.preventDefault(); setFile(null); }} aria-label="Remove file">
                      <X className="h-4 w-4" />
                    </button>
                  )}
                  <input type="file" accept="application/pdf" className="hidden" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
                </label>
              </Field>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <label className="flex items-center gap-2 text-sm text-slate-700">
                  <input type="checkbox" checked={saveReport} onChange={(e) => setSaveReport(e.target.checked)} className="h-4 w-4 rounded border-slate-300" />
                  Save as a compliance report
                </label>
                <Button type="submit" loading={loading} disabled={productName.trim().length < 2}>Generate checklist</Button>
              </div>
            </form>
          </Card>

          {error && <Alert tone="error">{error}</Alert>}
          {loading && <Card className="p-5"><AgentProgress /></Card>}
          {result && (
            <div className="space-y-4">
              {result.report_id && (
                <Alert tone="success">
                  Report saved. <Link href={`/reports#report-${result.report_id}`} className="font-medium underline">Open in My Reports</Link>
                </Alert>
              )}
              <div className="grid grid-cols-3 gap-3">
                {[
                  { label: "Meets", value: counts.meets ?? 0, cls: "text-emerald-700" },
                  { label: "Does not meet", value: counts.does_not_meet ?? 0, cls: "text-red-700" },
                  { label: "Missing information", value: counts.missing_information ?? 0, cls: "text-amber-700" },
                ].map((s) => (
                  <Card key={s.label} className="p-4 text-center">
                    <p className={`text-2xl font-semibold ${s.cls}`}>{s.value}</p>
                    <p className="text-xs text-slate-500">{s.label}</p>
                  </Card>
                ))}
              </div>
              <Card>
                <CardHeader title="Preliminary compliance checklist" />
                <div className="p-5"><ChecklistTable items={result.checklist} /></div>
              </Card>
              <div className="grid gap-4 md:grid-cols-2">
                <Card>
                  <CardHeader title="Missing specifications" />
                  <ul className="list-disc space-y-1 p-5 pl-9 text-sm text-slate-700">
                    {result.missing_specifications.length ? result.missing_specifications.map((m) => <li key={m}>{m}</li>) : <li className="list-none text-slate-500">None identified.</li>}
                  </ul>
                </Card>
                <Card>
                  <CardHeader title="Documents typically required" />
                  <ul className="list-disc space-y-1 p-5 pl-9 text-sm text-slate-700">
                    {result.required_documents.length ? result.required_documents.map((m) => <li key={m}>{m}</li>) : <li className="list-none text-slate-500">Not stated in the indexed documents.</li>}
                  </ul>
                </Card>
              </div>
              <Card className="p-5">
                <AnswerView answer={result.answer} citations={result.citations} verification={result.verification} />
              </Card>
            </div>
          )}
        </div>
        <aside>
          <Card>
            <div className="border-b border-slate-100 px-4 py-3 text-sm font-semibold text-slate-800">Previous assessments</div>
            <div className="p-2">
              {previous.data?.length ? (
                previous.data.map((r) => (
                  <Link key={r.id} href={`/reports#report-${r.id}`} className="block rounded-lg px-2 py-2 hover:bg-slate-50">
                    <p className="truncate text-sm font-medium text-slate-700">{r.product_name}</p>
                    <p className="text-xs text-slate-400">{timeAgo(r.created_at)}</p>
                  </Link>
                ))
              ) : (
                <p className="px-2 py-3 text-sm text-slate-500">{previous.loading ? "Loading…" : "No saved assessments yet."}</p>
              )}
            </div>
          </Card>
        </aside>
      </div>
    </div>
  );
}
