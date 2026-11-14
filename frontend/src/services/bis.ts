import type {
  AppNotification,
  BISDocument,
  CertificationGuidance,
  CertificationScheme,
  ComparisonResult,
  HealthStatus,
  Laboratory,
  Language,
  StandardDetail,
  StandardSearchResponse,
} from "@/types";
import { api } from "./api";

export const standardsService = {
  search: (q: string, mode = "auto", status?: string) =>
    api.get<StandardSearchResponse>("/api/standards/search", { q, mode, status }),
  get: (id: number) => api.get<StandardDetail>(`/api/standards/${id}`),
  compare: (standard_ids: number[], focus?: string, language?: Language | null) =>
    api.post<ComparisonResult>("/api/standards/compare", { standard_ids, focus: focus || null, language: language ?? null }),
};

export interface GuidanceInput {
  product_category: string;
  product_name: string;
  manufacturing_location: "india" | "outside_india";
  manufacturing_country?: string;
  product_specifications: string;
  existing_certification: string;
  organization_type: string;
  language?: Language | null;
  save_report: boolean;
}

export const certificationService = {
  guidance: (input: GuidanceInput) => api.post<CertificationGuidance>("/api/certification/guidance", input),
  schemes: () => api.get<CertificationScheme[]>("/api/certification/schemes"),
  createScheme: (input: Omit<CertificationScheme, "id">) => api.post<CertificationScheme>("/api/certification/schemes", input),
  deleteScheme: (id: number) => api.delete(`/api/certification/schemes/${id}`),
};

export interface LabQuery {
  q?: string;
  state?: string;
  city?: string;
  capability?: string;
  product_category?: string;
  limit?: number;
  offset?: number;
}

export const laboratoryService = {
  list: (query: LabQuery) => api.get<{ total: number; items: Laboratory[] }>("/api/laboratories", { ...query }),
  get: (id: number) => api.get<Laboratory>(`/api/laboratories/${id}`),
  filters: () => api.get<{ states: string[]; cities: string[] }>("/api/laboratories/filters"),
  importCsv: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.upload<{ imported: number }>("/api/laboratories/import", form);
  },
};

export const documentService = {
  list: () => api.get<BISDocument[]>("/api/documents"),
  upload: (form: FormData) => api.upload<BISDocument>("/api/documents/upload", form),
  setStatus: (id: number, status: string) => api.patch<BISDocument>(`/api/documents/${id}/status`, { status }),
  reindex: (id: number) => api.post<BISDocument>(`/api/documents/${id}/reindex`),
  remove: (id: number) => api.delete(`/api/documents/${id}`),
};

export const notificationService = {
  list: (unreadOnly = false) => api.get<AppNotification[]>("/api/notifications", { unread_only: unreadOnly }),
  markRead: (id: number) => api.patch<AppNotification>(`/api/notifications/${id}/read`),
  markAllRead: () => api.post<void>("/api/notifications/read-all"),
  remove: (id: number) => api.delete(`/api/notifications/${id}`),
};

export const systemService = {
  health: () => api.get<HealthStatus>("/api/health"),
};
