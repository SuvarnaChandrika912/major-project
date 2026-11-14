"use client";

import Link from "next/link";
import { useState } from "react";
import { FlaskConical, Search, Sparkles, Upload } from "lucide-react";
import { LabCard } from "@/components/laboratories/LabCard";
import { Alert, Button, Card, EmptyState, Field, Input, PageHeader, Select, Skeleton } from "@/components/ui";
import { useAuth } from "@/context/AuthContext";
import { ProtectedPage } from "@/components/layout/ProtectedPage";
import { useAsync } from "@/hooks/useAsync";
import { laboratoryService, type LabQuery } from "@/services/bis";
import { reportService } from "@/services/reports";
import type { Laboratory } from "@/types";
import { errorMessage } from "@/utils/format";

const PAGE_SIZE = 12;

export default function LaboratoriesPage() {
  return (
    <ProtectedPage>
      <LaboratoriesPageContent />
    </ProtectedPage>
  );
}

function LaboratoriesPageContent() {
  const { user } = useAuth();
  const filters = useAsync(() => laboratoryService.filters());
  const [query, setQuery] = useState<LabQuery>({});
  const [draft, setDraft] = useState<LabQuery>({});
  const [page, setPage] = useState(0);
  const [aiProduct, setAiProduct] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const [aiMessage, setAiMessage] = useState<{ tone: "success" | "error"; text: string; reportId?: number } | null>(null);
  const [importMsg, setImportMsg] = useState<string | null>(null);

  const labs = useAsync(() => laboratoryService.list({ ...query, limit: PAGE_SIZE, offset: page * PAGE_SIZE }), [query, page]);
  const items: Laboratory[] = labs.data?.items ?? [];
  const total = labs.data?.total ?? 0;
  const loading = labs.loading;
  const error = labs.error;

  const apply = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(0);
    setQuery({ ...draft });
  };

  const recommend = async () => {
    if (aiProduct.trim().length < 2) return;
    setAiLoading(true);
    setAiMessage(null);
    try {
      const report = await reportService.generate({
        report_type: "laboratory_recommendation",
        product_name: aiProduct.trim(),
        state: draft.state || null,
        city: draft.city || null,
      });
      setAiMessage({ tone: "success", text: "Laboratory recommendation report generated.", reportId: report.id });
    } catch (err) {
      setAiMessage({ tone: "error", text: errorMessage(err) });
    } finally {
      setAiLoading(false);
    }
  };

  const importCsv = async (file: File) => {
    setImportMsg(null);
    try {
      const res = await laboratoryService.importCsv(file);
      setImportMsg(`Imported ${res.imported} laboratory record(s).`);
      void filters.reload();
      void labs.reload();
    } catch (err) {
      setImportMsg(errorMessage(err));
    }
  };

  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div>
      <PageHeader
        title="Laboratory Finder"
        description="Find testing laboratories by capability, product category and location. Only verified records added by administrators are shown."
        icon={<FlaskConical className="h-5 w-5" />}
        action={
          user?.is_admin ? (
            <label className="inline-flex h-10 cursor-pointer items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 hover:bg-slate-50">
              <Upload className="h-4 w-4" /> Import CSV
              <input type="file" accept=".csv" className="hidden" onChange={(e) => e.target.files?.[0] && importCsv(e.target.files[0])} />
            </label>
          ) : undefined
        }
      />
      {importMsg && <Alert tone="info" className="mb-4" onClose={() => setImportMsg(null)}>{importMsg}</Alert>}

      <Card className="mb-4 p-4">
        <form onSubmit={apply} className="grid gap-3 md:grid-cols-6">
          <div className="relative md:col-span-2">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <Input className="pl-9" placeholder="Laboratory name or keyword" value={draft.q ?? ""} onChange={(e) => setDraft({ ...draft, q: e.target.value })} aria-label="Search laboratories" />
          </div>
          <Input placeholder="Testing capability" value={draft.capability ?? ""} onChange={(e) => setDraft({ ...draft, capability: e.target.value })} aria-label="Testing capability" />
          <Input placeholder="Product category" value={draft.product_category ?? ""} onChange={(e) => setDraft({ ...draft, product_category: e.target.value })} aria-label="Product category" />
          <Select value={draft.state ?? ""} onChange={(e) => setDraft({ ...draft, state: e.target.value })} aria-label="State">
            <option value="">All states</option>
            {filters.data?.states.map((s) => <option key={s} value={s}>{s}</option>)}
          </Select>
          <div className="flex gap-2">
            <Select value={draft.city ?? ""} onChange={(e) => setDraft({ ...draft, city: e.target.value })} aria-label="City">
              <option value="">All cities</option>
              {filters.data?.cities.map((c) => <option key={c} value={c}>{c}</option>)}
            </Select>
            <Button type="submit">Filter</Button>
          </div>
        </form>
      </Card>

      <Card className="mb-6 p-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-end">
          <Field label="AI laboratory recommendation" hint="The testing agent matches test requirements from indexed standards with laboratory records.">
            <Input value={aiProduct} onChange={(e) => setAiProduct(e.target.value)} placeholder="Product, e.g. packaged drinking water" className="md:w-96" />
          </Field>
          <Button onClick={recommend} loading={aiLoading} disabled={aiProduct.trim().length < 2}>
            <Sparkles className="h-4 w-4" /> Recommend laboratories
          </Button>
        </div>
        {aiMessage && (
          <Alert tone={aiMessage.tone} className="mt-3">
            {aiMessage.text}{" "}
            {aiMessage.reportId && <Link href={`/reports#report-${aiMessage.reportId}`} className="font-medium underline">View report</Link>}
          </Alert>
        )}
      </Card>

      {error && <Alert tone="error" className="mb-4">{error}</Alert>}
      {loading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-40 rounded-xl" />)}
        </div>
      ) : items.length === 0 ? (
        <Card>
          <EmptyState
            icon={<FlaskConical className="h-5 w-5" />}
            title="No laboratories found"
            description={total === 0 && !Object.values(query).some(Boolean) ? "No laboratory records have been added yet. Administrators can import verified records from official sources." : "Try different filters."}
          />
        </Card>
      ) : (
        <>
          <p className="mb-3 text-sm text-slate-500">{total} laboratories</p>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {items.map((lab) => <LabCard key={lab.id} lab={lab} />)}
          </div>
          {pages > 1 && (
            <div className="mt-6 flex items-center justify-center gap-2">
              <Button variant="secondary" size="sm" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>Previous</Button>
              <span className="text-sm text-slate-500">Page {page + 1} of {pages}</span>
              <Button variant="secondary" size="sm" disabled={page + 1 >= pages} onClick={() => setPage((p) => p + 1)}>Next</Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
