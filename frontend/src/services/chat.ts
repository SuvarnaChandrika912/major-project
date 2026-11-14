import type { AssistantAnswer, ChatResponse, ChatSession, ChatSessionDetail, Language } from "@/types";
import { api } from "./api";

export const chatService = {
  send: (message: string, sessionId?: number | null, language?: Language | null) =>
    api.post<ChatResponse>("/api/chat/message", { message, session_id: sessionId ?? null, language: language ?? null }),
  sessions: () => api.get<ChatSession[]>("/api/chat/sessions"),
  session: (id: number) => api.get<ChatSessionDetail>(`/api/chat/sessions/${id}`),
  rename: (id: number, title: string) => api.patch<ChatSession>(`/api/chat/sessions/${id}`, { title }),
  remove: (id: number) => api.delete(`/api/chat/sessions/${id}`),
  feedback: (messageId: number, rating: -1 | 1, comments?: string) =>
    api.post("/api/chat/feedback", { message_id: messageId, rating, comments }),
  hallmarking: (query: string, language?: Language | null) =>
    api.post<AssistantAnswer>("/api/hallmarking/query", { query, language: language ?? null }),
  consumer: (query: string, language?: Language | null) =>
    api.post<AssistantAnswer>("/api/consumer/query", { query, language: language ?? null }),
  resources: () => api.get<{ name: string; url: string; purpose: string }[]>("/api/consumer/resources"),
};
