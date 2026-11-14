"use client";

import Link from "next/link";
import { CheckSquare, ExternalLink, FileText, FlaskConical, ListOrdered, ShieldCheck } from "lucide-react";
import { AnswerView } from "@/components/chat/AnswerView";
import { Alert, Badge, Card, CardHeader } from "@/components/ui";
import type { CertificationGuidance } from "@/types";

function Section({ title, icon, children, empty }: { title: string; icon: React.ReactNode; children: React.ReactNode; empty: boolean }) {
  return (
    <Card>
      <CardHeader title={title} icon={icon} />
      <div className="p-4 text-sm text-slate-700">
        {empty ? <p className="text-slate-500">Not found in the indexed documents.</p> : children}
      </div>
    </Card>
  );
}

export function GuidanceResult({ result }: { result: CertificationGuidance }) {
  return (
    <div className="space-y-4">
      {result.report_id && (
        <Alert tone="success">
          Roadmap saved. <Link href={`/reports#report-${result.report_id}`} className="font-medium underline">Open in My Reports</Link>
        </Alert>
      )}
      <Card className="p-5">
        <AnswerView answer={result.answer} citations={result.citations} verification={result.verification} />
      </Card>
      <div className="grid gap-4 md:grid-cols-2">
        <Section title="Candidate certification schemes" icon={<ShieldCheck className="h-4 w-4" />} empty={!result.candidate_schemes.length}>
          <ul className="space-y-2">
            {result.candidate_schemes.map((s) => (
              <li key={s.name}>
                <p className="font-medium text-slate-800">{s.name}</p>
                <p className="text-slate-500">{s.reason}</p>
              </li>
            ))}
          </ul>
        </Section>
        <Section title="Applicable standard references" icon={<FileText className="h-4 w-4" />} empty={!result.applicable_standards.length}>
          <div className="flex flex-wrap gap-1.5">
            {result.applicable_standards.map((s) => <Badge key={s} tone="navy">{s}</Badge>)}
          </div>
        </Section>
        <Section title="Documentation checklist" icon={<CheckSquare className="h-4 w-4" />} empty={!result.documentation_checklist.length}>
          <ul className="list-disc space-y-1 pl-5">
            {result.documentation_checklist.map((d) => <li key={d}>{d}</li>)}
          </ul>
        </Section>
        <Section title="Testing guidance" icon={<FlaskConical className="h-4 w-4" />} empty={!result.required_tests.length}>
          <ul className="space-y-1">
            {result.required_tests.map((t) => (
              <li key={t.test}>
                {t.test}
                {t.clause_number && <span className="ml-1 text-slate-500">(Clause {t.clause_number})</span>}
              </li>
            ))}
          </ul>
        </Section>
      </div>
      <Section title="Certification process roadmap" icon={<ListOrdered className="h-4 w-4" />} empty={!result.process_steps.length}>
        <ol className="space-y-3">
          {result.process_steps.map((step, i) => (
            <li key={step} className="flex gap-3">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-navy-900 text-xs font-semibold text-white">{i + 1}</span>
              <span className="pt-0.5">{step}</span>
            </li>
          ))}
        </ol>
      </Section>
      {result.official_links.length > 0 && (
        <Card className="p-4">
          <p className="mb-2 text-sm font-semibold text-slate-800">Official links</p>
          <div className="flex flex-wrap gap-3">
            {result.official_links.map((l) => (
              <a key={l.url} href={l.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-sm font-medium text-navy-700 hover:underline">
                {l.label} <ExternalLink className="h-3.5 w-3.5" />
              </a>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
