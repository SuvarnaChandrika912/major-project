import type { Language } from "@/types";

export function cn(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}

export function formatDate(value: string | null | undefined, withTime = false): string {
  if (!value) return "—";
  const date = new Date(value.endsWith("Z") || value.includes("+") ? value : `${value}Z`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    ...(withTime ? { hour: "2-digit", minute: "2-digit" } : {}),
  });
}

export function timeAgo(value: string): string {
  const date = new Date(value.endsWith("Z") ? value : `${value}Z`);
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return days < 7 ? `${days}d ago` : formatDate(value);
}

export const LANGUAGES: { value: Language; label: string; native: string }[] = [
  { value: "en", label: "English", native: "English" },
  { value: "hi", label: "Hindi", native: "हिन्दी" },
  { value: "te", label: "Telugu", native: "తెలుగు" },
  { value: "kn", label: "Kannada", native: "ಕನ್ನಡ" },
  { value: "ta", label: "Tamil", native: "தமிழ்" },
];

export const AGENT_LABELS: Record<string, string> = {
  supervisor_agent: "Supervisor",
  product_agent: "Product Classification",
  standards_agent: "Standards Research",
  certification_agent: "Certification",
  testing_agent: "Testing & Laboratory",
  consumer_agent: "Consumer & Hallmarking",
  compliance_agent: "Compliance Assessment",
  verification_agent: "Verification",
  translation_agent: "Translation",
  report_agent: "Report Generation",
};

export const INTENT_LABELS: Record<string, string> = {
  GENERAL_BIS_QUERY: "General BIS",
  PRODUCT_STANDARD_SEARCH: "Product standards",
  CERTIFICATION_QUERY: "Certification",
  LABORATORY_SEARCH: "Laboratories",
  HALLMARKING_QUERY: "Hallmarking",
  CONSUMER_QUERY: "Consumer help",
  COMPLIANCE_ASSESSMENT: "Compliance",
  STANDARD_COMPARISON: "Comparison",
  DOCUMENT_ANALYSIS: "Document analysis",
};

export const REPORT_TYPE_LABELS: Record<string, string> = {
  compliance: "Compliance gap report",
  certification_roadmap: "Certification roadmap",
  standard_comparison: "Standard comparison",
  laboratory_recommendation: "Laboratory recommendation",
};

export const DOCUMENT_TYPE_LABELS: Record<string, string> = {
  indian_standard: "Indian Standard",
  certification_guideline: "Certification guideline",
  hallmarking: "Hallmarking",
  faq: "Official FAQ",
  laboratory_information: "Laboratory information",
  other: "Other",
};

export function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : "Something went wrong. Please try again.";
}
