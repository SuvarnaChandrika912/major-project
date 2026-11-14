import Image from "next/image";
import { BookOpenCheck, FlaskConical, Gem, ShieldCheck } from "lucide-react";

const HIGHLIGHTS = [
  { icon: BookOpenCheck, text: "Source-grounded answers with standard and clause references" },
  { icon: ShieldCheck, text: "Certification roadmaps and preliminary compliance checks" },
  { icon: FlaskConical, text: "Testing requirements and laboratory records" },
  { icon: Gem, text: "Hallmarking, HUID and ISI mark guidance for consumers" },
];

export function AuthLayout({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="hidden flex-col justify-between bg-navy-900 p-12 text-white lg:flex">
        <div className="flex items-center gap-3">
          <Image src="/logo.svg" alt="" width={40} height={40} className="rounded-lg ring-1 ring-white/20" />
          <span className="text-lg font-bold tracking-wide">BIS SAATHI</span>
        </div>
        <div>
          <h2 className="max-w-md text-3xl font-semibold leading-tight">
            Your AI companion for Indian Standards and BIS certification.
          </h2>
          <ul className="mt-8 space-y-4">
            {HIGHLIGHTS.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-start gap-3 text-navy-100">
                <Icon className="mt-0.5 h-5 w-5 shrink-0 text-white" />
                {text}
              </li>
            ))}
          </ul>
        </div>
        <p className="text-xs text-navy-200">
          BIS SAATHI provides preliminary guidance. Official decisions rest with the Bureau of Indian Standards.
        </p>
      </div>
      <div className="flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-md">
          <div className="mb-8 flex items-center gap-2.5 lg:hidden">
            <Image src="/logo.svg" alt="" width={36} height={36} />
            <span className="text-lg font-bold text-navy-900">BIS SAATHI</span>
          </div>
          <h1 className="text-2xl font-semibold text-slate-900">{title}</h1>
          <p className="mt-1.5 text-sm text-slate-500">{subtitle}</p>
          <div className="mt-8">{children}</div>
        </div>
      </div>
    </div>
  );
}
