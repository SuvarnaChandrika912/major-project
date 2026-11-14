import type { ComplianceResult, DashboardSummary, Language, Report, ReportSummary, ReportType } from "@/types";
import { api } from "./api";

export interface ComplianceInput {
  product_name: string;
  product_category: string;
  specifications: string;
  available_documents: string[];
  target_standard?: string | null;
  language?: Language | null;
  save_report: boolean;
}

export interface ReportInput {
  report_type: ReportType;
  product_name: string;
  product_category?: string;
  specifications?: string;
  standard_ids?: number[];
  state?: string | null;
  city?: string | null;
  language?: Language | null;
}

export const reportService = {
  list: (reportType?: ReportType) => api.get<ReportSummary[]>("/api/reports", { report_type: reportType }),
  get: (id: number) => api.get<Report>(`/api/reports/${id}`),
  generate: (input: ReportInput) => api.post<Report>("/api/reports/generate", input),
  download: (id: number, title: string) => api.download(`/api/reports/${id}/download`, `${title}.pdf`),
  remove: (id: number) => api.delete(`/api/reports/${id}`),
  analyzeCompliance: (input: ComplianceInput, file?: File | null) => {
    const form = new FormData();
    form.append("payload", JSON.stringify(input));
    if (file) form.append("file", file);
    return api.upload<ComplianceResult>("/api/compliance/analyze", form);
  },
  dashboard: () => api.get<DashboardSummary>("/api/dashboard/summary"),
};
