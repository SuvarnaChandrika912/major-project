"use client";

import { useEffect, useState } from "react";
import { Database, FileUp, RefreshCw, ShieldCheck, Trash2 } from "lucide-react";
import { Alert, Badge, Button, Card, CardHeader, EmptyState, Field, Input, PageHeader, Select, SkeletonList, statusTone, Textarea } from "@/components/ui";
import { useAuth } from "@/context/AuthContext";
import { ProtectedPage } from "@/components/layout/ProtectedPage";
import { useAsync } from "@/hooks/useAsync";
import { certificationService, documentService } from "@/services/bis";
import { DOCUMENT_TYPE_LABELS, errorMessage, formatDate } from "@/utils/format";

const EMPTY_FORM = {
  document_title: "",
  document_type: "indian_standard",
  standard_number: "",
  document_version: "",
  amendment_number: "",
  publication_date: "",
  source_url: "",
  document_status: "current",
};

export default function AdminDocumentsPage() {
  return (
    <ProtectedPage>
      <AdminDocumentsPageContent />
    </ProtectedPage>
  );
}

function AdminDocumentsPageContent() {
  const { user } = useAuth();
  const docs = useAsync(() => documentService.list());
  const schemes = useAsync(() => certificationService.schemes());
  const [form, setForm] = useState(EMPTY_FORM);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<{ tone: "success" | "error"; text: string } | null>(null);
  const [scheme, setScheme] = useState({ scheme_name: "", description: "", requirements: "", official_source_url: "" });
  const [schemeMsg, setSchemeMsg] = useState<{ tone: "success" | "error"; text: string } | null>(null);

  const processing = (docs.data ?? []).some((d) => d.ingestion_status === "pending" || d.ingestion_status === "processing");
  const reloadDocs = docs.reload;
  useEffect(() => {
    if (!processing) return;
    const timer = window.setInterval(() => void reloadDocs(), 4000);
    return () => window.clearInterval(timer);
  }, [processing, reloadDocs]);

  if (!user?.is_admin) {
    return <Alert tone="error" title="Administrator access required">Only administrators can manage the knowledge base.</Alert>;
  }

  const upload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return setMessage({ tone: "error", text: "Choose a PDF file to upload." });
    const data = new FormData();
    data.append("file", file);
    Object.entries(form).forEach(([k, v]) => v && data.append(k, v));
    setUploading(true);
    setMessage(null);
    try {
      const doc = await documentService.upload(data);
      setMessage({ tone: "success", text: `"${doc.document_title}" uploaded. Indexing runs in the background.` });
      setForm(EMPTY_FORM);
      setFile(null);
      await docs.reload();
    } catch (err) {
      setMessage({ tone: "error", text: errorMessage(err) });
    } finally {
      setUploading(false);
    }
  };

  const act = async (fn: () => Promise<unknown>) => {
    try {
      await fn();
      await docs.reload();
    } catch (err) {
      setMessage({ tone: "error", text: errorMessage(err) });
    }
  };

  const addScheme = async (e: React.FormEvent) => {
    e.preventDefault();
    setSchemeMsg(null);
    try {
      await certificationService.createScheme({
        scheme_name: scheme.scheme_name.trim(),
        description: scheme.description.trim(),
        requirements: scheme.requirements.trim() || null,
        official_source_url: scheme.official_source_url.trim() || null,
      });
      setScheme({ scheme_name: "", description: "", requirements: "", official_source_url: "" });
      setSchemeMsg({ tone: "success", text: "Scheme record added." });
      await schemes.reload();
    } catch (err) {
      setSchemeMsg({ tone: "error", text: errorMessage(err) });
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Knowledge Base"
        description="Upload authorised BIS documents. Each file is validated, OCR-processed if scanned, split into clause-level chunks, embedded and indexed in Pinecone."
        icon={<Database className="h-5 w-5" />}
      />
      <Alert tone="warning">Only upload documents you are authorised to use. Respect BIS copyright and licensing terms. Content from uploaded PDFs is treated as untrusted data by the agents.</Alert>

      <Card>
        <CardHeader title="Upload document" icon={<FileUp className="h-4 w-4" />} />
        <form onSubmit={upload} className="space-y-4 p-5">
          {message && <Alert tone={message.tone} onClose={() => setMessage(null)}>{message.text}</Alert>}
          <div className="grid gap-4 md:grid-cols-3">
            <Field label="Document title" required htmlFor="dt">
              <Input id="dt" value={form.document_title} onChange={(e) => setForm({ ...form, document_title: e.target.value })} required minLength={3} />
            </Field>
            <Field label="Document type" htmlFor="dtype">
              <Select id="dtype" value={form.document_type} onChange={(e) => setForm({ ...form, document_type: e.target.value })}>
                {Object.entries(DOCUMENT_TYPE_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </Select>
            </Field>
            <Field label="Standard number" hint="Detected automatically if left blank" htmlFor="sn">
              <Input id="sn" value={form.standard_number} onChange={(e) => setForm({ ...form, standard_number: e.target.value })} placeholder="IS 1293:2019" />
            </Field>
            <Field label="Version" htmlFor="ver">
              <Input id="ver" value={form.document_version} onChange={(e) => setForm({ ...form, document_version: e.target.value })} placeholder="e.g. 2019 or Fourth Revision" />
            </Field>
            <Field label="Amendment number" htmlFor="amd">
              <Input id="amd" value={form.amendment_number} onChange={(e) => setForm({ ...form, amendment_number: e.target.value })} />
            </Field>
            <Field label="Publication date" htmlFor="pd">
              <Input id="pd" type="date" value={form.publication_date} onChange={(e) => setForm({ ...form, publication_date: e.target.value })} />
            </Field>
            <Field label="Official source URL" htmlFor="url">
              <Input id="url" type="url" value={form.source_url} onChange={(e) => setForm({ ...form, source_url: e.target.value })} placeholder="https://" />
            </Field>
            <Field label="Document status" htmlFor="ds">
              <Select id="ds" value={form.document_status} onChange={(e) => setForm({ ...form, document_status: e.target.value })}>
                <option value="current">Current</option>
                <option value="superseded">Superseded</option>
                <option value="withdrawn">Withdrawn</option>
                <option value="draft">Draft</option>
              </Select>
            </Field>
            <Field label="PDF file" required>
              <label className="flex h-10 cursor-pointer items-center gap-2 rounded-lg border border-dashed border-slate-300 px-3 text-sm text-slate-600 hover:bg-slate-50">
                <FileUp className="h-4 w-4 text-slate-400" />
                <span className="truncate">{file ? file.name : "Choose PDF"}</span>
                <input type="file" accept="application/pdf" className="hidden" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
              </label>
            </Field>
          </div>
          <div className="flex justify-end"><Button type="submit" loading={uploading}>Upload and index</Button></div>
        </form>
      </Card>

      <Card>
        <CardHeader title="Indexed documents" action={<Button size="sm" variant="secondary" onClick={docs.reload}><RefreshCw className="h-4 w-4" /> Refresh</Button>} />
        {docs.loading && !docs.data ? (
          <div className="p-5"><SkeletonList rows={4} /></div>
        ) : !docs.data?.length ? (
          <EmptyState icon={<Database className="h-5 w-5" />} title="No documents yet" description="Upload authorised BIS documents to build the knowledge base." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-5 py-2 font-medium">Document</th>
                  <th className="px-3 py-2 font-medium">Type</th>
                  <th className="px-3 py-2 font-medium">Indexing</th>
                  <th className="px-3 py-2 font-medium">Status</th>
                  <th className="px-3 py-2 font-medium">Chunks</th>
                  <th className="px-5 py-2 text-right font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {docs.data.map((d) => (
                  <tr key={d.id} className="align-top">
                    <td className="px-5 py-3">
                      <p className="font-medium text-slate-800">{d.document_title}</p>
                      <p className="text-xs text-slate-500">
                        {[d.standard_number, d.document_version && `v${d.document_version}`, formatDate(d.created_at)].filter(Boolean).join(" · ")}
                        {d.used_ocr && " · OCR"}
                      </p>
                      {d.error_message && <p className={`mt-1 text-xs ${d.ingestion_status === "failed" ? "text-red-600" : "text-amber-700"}`}>{d.error_message}</p>}
                    </td>
                    <td className="px-3 py-3 text-slate-600">{DOCUMENT_TYPE_LABELS[d.document_type] ?? d.document_type}</td>
                    <td className="px-3 py-3"><Badge tone={statusTone(d.ingestion_status)}>{d.ingestion_status}</Badge></td>
                    <td className="px-3 py-3">
                      <select
                        value={d.status}
                        onChange={(e) => act(() => documentService.setStatus(d.id, e.target.value))}
                        className="rounded-md border border-slate-200 px-2 py-1 text-xs"
                        aria-label={`Status of ${d.document_title}`}
                      >
                        {["current", "superseded", "withdrawn", "draft"].map((s) => <option key={s} value={s}>{s}</option>)}
                      </select>
                    </td>
                    <td className="px-3 py-3 text-slate-600">{d.chunk_count} / {d.page_count}p</td>
                    <td className="px-5 py-3">
                      <div className="flex justify-end gap-1">
                        <Button size="sm" variant="ghost" onClick={() => act(() => documentService.reindex(d.id))} aria-label="Re-index"><RefreshCw className="h-4 w-4" /></Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => window.confirm(`Delete "${d.document_title}" and its vectors?`) && act(() => documentService.remove(d.id))}
                          aria-label="Delete"
                        >
                          <Trash2 className="h-4 w-4 text-red-600" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card>
        <CardHeader title="Certification scheme records" description="Structured scheme information from official BIS sources, used by the certification agent." icon={<ShieldCheck className="h-4 w-4" />} />
        <div className="grid gap-6 p-5 lg:grid-cols-2">
          <form onSubmit={addScheme} className="space-y-3">
            {schemeMsg && <Alert tone={schemeMsg.tone}>{schemeMsg.text}</Alert>}
            <Field label="Scheme name" required htmlFor="sname"><Input id="sname" value={scheme.scheme_name} onChange={(e) => setScheme({ ...scheme, scheme_name: e.target.value })} required minLength={2} /></Field>
            <Field label="Description" required htmlFor="sdesc"><Textarea id="sdesc" rows={3} value={scheme.description} onChange={(e) => setScheme({ ...scheme, description: e.target.value })} required /></Field>
            <Field label="Requirements" htmlFor="sreq"><Textarea id="sreq" rows={3} value={scheme.requirements} onChange={(e) => setScheme({ ...scheme, requirements: e.target.value })} /></Field>
            <Field label="Official source URL" htmlFor="surl"><Input id="surl" type="url" value={scheme.official_source_url} onChange={(e) => setScheme({ ...scheme, official_source_url: e.target.value })} /></Field>
            <Button type="submit">Add scheme</Button>
          </form>
          <div className="space-y-2">
            {schemes.data?.length === 0 && <p className="text-sm text-slate-500">No scheme records yet.</p>}
            {schemes.data?.map((s) => (
              <div key={s.id} className="flex items-start gap-2 rounded-lg border border-slate-200 p-3">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-slate-800">{s.scheme_name}</p>
                  <p className="line-clamp-2 text-xs text-slate-500">{s.description}</p>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={async () => {
                    if (!window.confirm(`Delete scheme "${s.scheme_name}"?`)) return;
                    await certificationService.deleteScheme(s.id);
                    await schemes.reload();
                  }}
                  aria-label={`Delete ${s.scheme_name}`}
                >
                  <Trash2 className="h-4 w-4 text-red-600" />
                </Button>
              </div>
            ))}
          </div>
        </div>
      </Card>
    </div>
  );
}
