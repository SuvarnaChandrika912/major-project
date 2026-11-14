"use client";

import { useEffect, useState } from "react";
import { Download, Trash2 } from "lucide-react";
import { CitationList } from "@/components/chat/CitationList";
import { Markdown } from "@/components/chat/Markdown";
import { VerificationBadge } from "@/components/chat/VerificationBadge";
import { ChecklistTable } from "@/components/compliance/ChecklistTable";
import { Alert, Badge, Button, Modal, SkeletonList } from "@/components/ui";
import { reportService } from "@/services/reports";
import type { ChecklistItem, Report } from "@/types";
import { errorMessage, formatDate, REPORT_TYPE_LABELS } from "@/utils/format";

export function ReportViewer({ reportId, onClose, onDeleted }: { reportId: number | null; onClose: () => void; onDeleted: (id: number) => void }) {
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [active, setActive] = useState<number | null>(null);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    if (reportId === null) return;
    reportService.get(reportId).then(setReport).catch((err) => setError(errorMessage(err)));
  }, [reportId]);

  const download = async () => {
    if (!report) return;
    setDownloading(true);
    try {
      await reportService.download(report.id, report.report_title);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setDownloading(false);
    }
  };

  const remove = async () => {
    if (!report || !window.confirm("Delete this report permanently?")) return;
    try {
      await reportService.remove(report.id);
      onDeleted(report.id);
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const data = report?.report_data;
  const content = data?.content;
  const structured = (data?.structured ?? {}) as Record<string, { checklist?: ChecklistItem[]; recommended_laboratories?: { name: string; city: string; state: string; reason: string; recognition_status: string }[] }>;
  const checklist = structured.compliance_agent?.checklist ?? [];
  const labs = structured.testing_agent?.recommended_laboratories ?? [];

  return (
    <Modal open={reportId !== null} onClose={onClose} title={report?.report_title ?? "Report"} wide>
      {error && <Alert tone="error" className="mb-4">{error}</Alert>}
      {!report && !error && <SkeletonList rows={6} />}
      {report && (
        <div className="space-y-5">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="navy">{REPORT_TYPE_LABELS[report.report_type]}</Badge>
            <Badge>{report.product_name}</Badge>
            <span className="text-xs text-slate-500">{formatDate(report.created_at, true)}</span>
            <div className="ml-auto flex gap-2">
              <Button size="sm" onClick={download} loading={downloading}><Download className="h-4 w-4" /> PDF</Button>
              <Button size="sm" variant="secondary" onClick={remove}><Trash2 className="h-4 w-4 text-red-600" /> Delete</Button>
            </div>
          </div>
          <Alert tone="warning">{data?.disclaimer ?? "Preliminary AI-generated report. Not an official BIS certification or approval."}</Alert>
          <VerificationBadge verification={data?.verification} />
          <section>
            <h3 className="mb-1 text-sm font-semibold text-navy-900">Executive summary</h3>
            <Markdown content={content?.executive_summary ?? data?.answer ?? ""} onCitationClick={setActive} />
          </section>
          {content?.sections?.map((s) => (
            <section key={s.heading}>
              <h3 className="mb-1 text-sm font-semibold text-navy-900">{s.heading}</h3>
              <Markdown content={s.content} onCitationClick={setActive} />
            </section>
          ))}
          {checklist.length > 0 && (
            <section>
              <h3 className="mb-2 text-sm font-semibold text-navy-900">Compliance checklist</h3>
              <ChecklistTable items={checklist} />
            </section>
          )}
          {labs.length > 0 && (
            <section>
              <h3 className="mb-2 text-sm font-semibold text-navy-900">Recommended laboratories</h3>
              <ul className="space-y-2 text-sm">
                {labs.map((l) => (
                  <li key={l.name} className="rounded-lg border border-slate-200 p-3">
                    <p className="font-medium text-slate-800">{l.name} <span className="font-normal text-slate-500">({l.city}, {l.state})</span></p>
                    <p className="text-xs text-slate-500">Recognition: {l.recognition_status}</p>
                    <p className="mt-1 text-slate-600">{l.reason}</p>
                  </li>
                ))}
              </ul>
            </section>
          )}
          {[["Recommendations", content?.recommendations], ["Limitations", content?.limitations]].map(([title, list]) =>
            Array.isArray(list) && list.length ? (
              <section key={title as string}>
                <h3 className="mb-1 text-sm font-semibold text-navy-900">{title as string}</h3>
                <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
                  {(list as string[]).map((x) => <li key={x}>{x}</li>)}
                </ul>
              </section>
            ) : null,
          )}
          <CitationList citations={data?.citations ?? []} active={active} onToggle={setActive} />
        </div>
      )}
    </Modal>
  );
}
