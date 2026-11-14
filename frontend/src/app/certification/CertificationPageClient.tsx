"use client";

import { useState } from "react";
import { ProtectedPage } from "@/components/layout/ProtectedPage";
import { ArrowLeft, ArrowRight, Check, ShieldCheck } from "lucide-react";
import { AgentProgress } from "@/components/chat/AgentActivity";
import { GuidanceResult } from "@/components/certification/GuidanceResult";
import { Alert, Button, Card, Field, Input, PageHeader, Select, Textarea } from "@/components/ui";
import { useAsync } from "@/hooks/useAsync";
import { certificationService, type GuidanceInput } from "@/services/bis";
import type { CertificationGuidance } from "@/types";
import { cn, errorMessage } from "@/utils/format";

const STEPS = ["Product", "Manufacturer", "Specifications", "Review"];
const ORG_TYPES = [
  { value: "msme", label: "MSME" },
  { value: "startup", label: "Startup" },
  { value: "large_manufacturer", label: "Large manufacturer" },
  { value: "importer", label: "Importer" },
  { value: "foreign_manufacturer", label: "Foreign manufacturer" },
  { value: "other", label: "Other" },
];

const INITIAL: GuidanceInput = {
  product_category: "",
  product_name: "",
  manufacturing_location: "india",
  manufacturing_country: "",
  product_specifications: "",
  existing_certification: "none",
  organization_type: "msme",
  save_report: true,
};

export default function CertificationPageClient() {
  return (
    <ProtectedPage>
      <CertificationPageContent />
    </ProtectedPage>
  );
}

function CertificationPageContent() {
  const [step, setStep] = useState(0);
  const [form, setForm] = useState<GuidanceInput>(INITIAL);
  const [result, setResult] = useState<CertificationGuidance | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const schemes = useAsync(() => certificationService.schemes());

  const set = <K extends keyof GuidanceInput>(key: K, value: GuidanceInput[K]) => setForm((f) => ({ ...f, [key]: value }));
  const canContinue =
    step === 0 ? form.product_name.trim().length >= 2 && form.product_category.trim().length >= 2 : step === 1 ? form.manufacturing_location === "india" || !!form.manufacturing_country?.trim() : true;

  const generate = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(await certificationService.guidance(form));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <PageHeader
        title="Certification Guide"
        description="Answer a few questions to get candidate certification schemes, applicable standards, documents and a step-by-step roadmap."
        icon={<ShieldCheck className="h-5 w-5" />}
      />
      <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
        <div className="space-y-6">
          <Card className="p-5">
            <ol className="mb-6 flex items-center gap-2">
              {STEPS.map((label, i) => (
                <li key={label} className="flex flex-1 items-center gap-2">
                  <span className={cn("flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold", i < step ? "bg-emerald-500 text-white" : i === step ? "bg-navy-900 text-white" : "bg-slate-100 text-slate-500")}>
                    {i < step ? <Check className="h-4 w-4" /> : i + 1}
                  </span>
                  <span className={cn("hidden text-sm sm:inline", i === step ? "font-medium text-slate-900" : "text-slate-500")}>{label}</span>
                  {i < STEPS.length - 1 && <span className="h-px flex-1 bg-slate-200" />}
                </li>
              ))}
            </ol>

            {step === 0 && (
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Product category" required htmlFor="cat">
                  <Input id="cat" value={form.product_category} onChange={(e) => set("product_category", e.target.value)} placeholder="e.g. Electrical appliances" />
                </Field>
                <Field label="Product name" required htmlFor="name">
                  <Input id="name" value={form.product_name} onChange={(e) => set("product_name", e.target.value)} placeholder="e.g. Electric room heater" />
                </Field>
              </div>
            )}
            {step === 1 && (
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Manufacturing location" htmlFor="loc">
                  <Select id="loc" value={form.manufacturing_location} onChange={(e) => set("manufacturing_location", e.target.value as GuidanceInput["manufacturing_location"])}>
                    <option value="india">In India</option>
                    <option value="outside_india">Outside India</option>
                  </Select>
                </Field>
                {form.manufacturing_location === "outside_india" && (
                  <Field label="Country of manufacture" required htmlFor="country">
                    <Input id="country" value={form.manufacturing_country} onChange={(e) => set("manufacturing_country", e.target.value)} />
                  </Field>
                )}
                <Field label="Organization type" htmlFor="org">
                  <Select id="org" value={form.organization_type} onChange={(e) => set("organization_type", e.target.value)}>
                    {ORG_TYPES.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </Select>
                </Field>
                <Field label="Existing certification status" htmlFor="existing">
                  <Input id="existing" value={form.existing_certification} onChange={(e) => set("existing_certification", e.target.value)} placeholder="e.g. none, BIS licence expired, ISO 9001" />
                </Field>
              </div>
            )}
            {step === 2 && (
              <Field label="Product specifications" hint="Ratings, materials, capacity, dimensions — anything that determines the applicable standard." htmlFor="specs">
                <Textarea id="specs" rows={6} value={form.product_specifications} onChange={(e) => set("product_specifications", e.target.value)} placeholder="e.g. 2000 W, 230 V AC, oil-filled, 11 fins, metal body" />
              </Field>
            )}
            {step === 3 && (
              <div className="space-y-3 text-sm">
                <dl className="grid gap-x-6 gap-y-2 sm:grid-cols-2">
                  {[
                    ["Product", `${form.product_name} (${form.product_category})`],
                    ["Manufactured", form.manufacturing_location === "india" ? "In India" : `Outside India — ${form.manufacturing_country}`],
                    ["Organization", ORG_TYPES.find((o) => o.value === form.organization_type)?.label],
                    ["Existing certification", form.existing_certification || "none"],
                  ].map(([k, v]) => (
                    <div key={k}>
                      <dt className="text-xs text-slate-500">{k}</dt>
                      <dd className="font-medium text-slate-800">{v}</dd>
                    </div>
                  ))}
                </dl>
                <div>
                  <p className="text-xs text-slate-500">Specifications</p>
                  <p className="whitespace-pre-line font-medium text-slate-800">{form.product_specifications || "Not provided"}</p>
                </div>
                <label className="flex items-center gap-2 pt-2">
                  <input type="checkbox" checked={form.save_report} onChange={(e) => set("save_report", e.target.checked)} className="h-4 w-4 rounded border-slate-300 text-navy-900" />
                  Save the roadmap to My Reports
                </label>
              </div>
            )}

            <div className="mt-6 flex justify-between">
              <Button variant="secondary" onClick={() => setStep((s) => s - 1)} disabled={step === 0 || loading}>
                <ArrowLeft className="h-4 w-4" /> Back
              </Button>
              {step < STEPS.length - 1 ? (
                <Button onClick={() => setStep((s) => s + 1)} disabled={!canContinue}>
                  Continue <ArrowRight className="h-4 w-4" />
                </Button>
              ) : (
                <Button onClick={generate} loading={loading}>Generate roadmap</Button>
              )}
            </div>
          </Card>

          {error && <Alert tone="error">{error}</Alert>}
          {loading && <Card className="p-5"><AgentProgress /></Card>}
          {result && <GuidanceResult result={result} />}
        </div>

        <aside>
          <Card>
            <div className="border-b border-slate-100 px-4 py-3">
              <p className="text-sm font-semibold text-slate-800">Scheme records</p>
              <p className="text-xs text-slate-500">Maintained by administrators from official sources</p>
            </div>
            <div className="divide-y divide-slate-100">
              {schemes.loading && <p className="p-4 text-sm text-slate-500">Loading…</p>}
              {schemes.error && <p className="p-4 text-sm text-red-600">{schemes.error}</p>}
              {schemes.data?.length === 0 && <p className="p-4 text-sm text-slate-500">No scheme records have been added yet.</p>}
              {schemes.data?.map((s) => (
                <div key={s.id} className="p-4">
                  <p className="text-sm font-medium text-slate-800">{s.scheme_name}</p>
                  <p className="mt-0.5 line-clamp-3 text-xs text-slate-500">{s.description}</p>
                  {s.official_source_url && (
                    <a href={s.official_source_url} target="_blank" rel="noopener noreferrer" className="mt-1 inline-block text-xs font-medium text-navy-700 hover:underline">
                      Official source
                    </a>
                  )}
                </div>
              ))}
            </div>
          </Card>
        </aside>
      </div>
    </div>
  );
}
