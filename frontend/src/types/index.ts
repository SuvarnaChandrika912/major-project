export type Language = "en" | "hi" | "te" | "kn" | "ta";

export interface User {
  id: number;
  full_name: string;
  email: string;
  preferred_language: Language;
  organization: string | null;
  is_admin: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Citation {
  index: number;
  chunk_id: string;
  document_id: number | null;
  standard_number: string | null;
  standard_title: string | null;
  clause_number: string | null;
  section: string | null;
  page_number: number | null;
  document_version: string | null;
  amendment_number: string | null;
  document_status: string | null;
  document_type: string | null;
  source_url: string | null;
  excerpt: string;
  score: number | null;
}

export type EvidenceStatus = "SUFFICIENT" | "PARTIAL" | "INSUFFICIENT";

export interface Verification {
  evidence_status: EvidenceStatus;
  confidence: number;
  supported_claims: string[];
  unsupported_claims: string[];
  warnings: string[];
  outdated_documents: string[];
}

export interface AgentTrace {
  agent: string;
  status: "completed" | "failed" | "skipped" | "timeout";
  summary: string;
  duration_ms: number;
}

export interface ChatResponse {
  session_id: number;
  message_id: number;
  answer: string;
  intent: string;
  language: Language;
  agents_used: string[];
  citations: Citation[];
  verification: Verification;
  follow_up_questions: string[];
  clarification_questions: string[];
  agent_trace: AgentTrace[];
  structured: Record<string, unknown>;
}

export interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  message: string;
  agent_used: string | null;
  intent: string | null;
  extra: {
    citations?: Citation[];
    verification?: Verification;
    follow_up_questions?: string[];
    clarification_questions?: string[];
    agent_trace?: AgentTrace[];
    language?: Language;
  } | null;
  created_at: string;
}

export interface ChatSession {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ChatSessionDetail extends ChatSession {
  messages: ChatMessage[];
}

export interface Standard {
  id: number;
  standard_number: string;
  title: string;
  scope: string | null;
  publication_date: string | null;
  amendment_number: string | null;
  status: string;
  document_id: number | null;
}

export interface DocumentChunk {
  chunk_id: string;
  chunk_index: number;
  section: string | null;
  clause_number: string | null;
  page_number: number;
  text: string;
}

export interface BISDocument {
  id: number;
  document_title: string;
  document_type: string;
  standard_number: string | null;
  document_version: string | null;
  amendment_number: string | null;
  publication_date: string | null;
  source_url: string | null;
  status: string;
  ingestion_status: "pending" | "processing" | "indexed" | "failed";
  error_message: string | null;
  page_count: number;
  chunk_count: number;
  used_ocr: boolean;
  created_at: string;
}

export interface StandardDetail extends Standard {
  document: BISDocument | null;
  clauses: DocumentChunk[];
}

export interface StandardSearchHit {
  standard: Standard | null;
  document_id: number | null;
  standard_number: string | null;
  title: string | null;
  status: string | null;
  matched_clauses: Citation[];
  score: number | null;
}

export interface StandardSearchResponse {
  query: string;
  mode: string;
  results: StandardSearchHit[];
  message: string | null;
}

export interface ComparisonResult {
  standards: Standard[];
  answer: string;
  citations: Citation[];
  verification: Verification;
}

export interface CertificationScheme {
  id: number;
  scheme_name: string;
  description: string;
  requirements: string | null;
  official_source_url: string | null;
}

export interface OfficialLink {
  label: string;
  url: string;
}

export interface CertificationGuidance {
  answer: string;
  citations: Citation[];
  verification: Verification;
  follow_up_questions: string[];
  clarification_questions: string[];
  candidate_schemes: { name: string; reason: string; citation: string }[];
  documentation_checklist: string[];
  process_steps: string[];
  official_links: OfficialLink[];
  applicable_standards: string[];
  required_tests: { test: string; clause_number: string | null; citation: string }[];
  agents_used: string[];
  report_id: number | null;
}

export interface Laboratory {
  id: number;
  laboratory_name: string;
  address: string | null;
  city: string | null;
  state: string | null;
  contact_information: string | null;
  recognition_status: string | null;
  testing_capabilities: string | null;
  product_categories: string | null;
  official_source_url: string | null;
  last_verified_at: string | null;
}

export interface AssistantAnswer {
  answer: string;
  intent: string;
  citations: Citation[];
  verification: Verification;
  follow_up_questions: string[];
  official_resources: { name: string; url: string; purpose?: string }[];
  agents_used: string[];
}

export interface ChecklistItem {
  requirement: string;
  clause_number: string | null;
  citation: string;
  status: "meets" | "does_not_meet" | "missing_information";
  notes: string;
}

export interface ComplianceResult {
  answer: string;
  citations: Citation[];
  verification: Verification;
  checklist: ChecklistItem[];
  status_counts: Partial<Record<ChecklistItem["status"], number>>;
  missing_specifications: string[];
  required_documents: string[];
  agents_used: string[];
  report_id: number | null;
}

export type ReportType = "compliance" | "certification_roadmap" | "standard_comparison" | "laboratory_recommendation";

export interface ReportSummary {
  id: number;
  product_name: string;
  report_title: string;
  report_type: ReportType;
  created_at: string;
}

export interface Report extends ReportSummary {
  report_data: {
    answer?: string;
    content?: {
      executive_summary: string;
      sections?: { heading: string; content: string }[];
      recommendations?: string[];
      limitations?: string[];
    };
    citations?: Citation[];
    verification?: Verification;
    structured?: Record<string, unknown>;
    disclaimer?: string;
    agents_used?: string[];
  };
}

export interface AppNotification {
  id: number;
  title: string;
  description: string;
  notification_type: "info" | "success" | "warning" | "error" | "ingestion_success" | "ingestion_error";
  read_status: boolean;
  created_at: string;
}

export interface DashboardSummary {
  total_sessions: number;
  total_messages: number;
  total_reports: number;
  unread_notifications: number;
  indexed_documents: number;
  activity: { date: string; queries: number }[];
  intent_distribution: { intent: string; count: number }[];
}

export interface HealthStatus {
  status: string;
  database: string;
  pinecone: string;
  llm: string;
  embedding_model: string;
}
