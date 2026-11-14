"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Bot, MessageSquarePlus, PanelLeft, Trash2 } from "lucide-react";
import { AgentProgress } from "@/components/chat/AgentActivity";
import { ChatInput } from "@/components/chat/ChatInput";
import { MessageBubble, type UiMessage } from "@/components/chat/MessageBubble";
import { Alert, SkeletonList } from "@/components/ui";
import { useAuth } from "@/context/AuthContext";
import { ProtectedPage } from "@/components/layout/ProtectedPage";
import { PENDING_QUERY_KEY, POPULAR_QUERIES } from "@/lib/navigation";
import { chatService } from "@/services/chat";
import type { ChatMessage, ChatSession, Language } from "@/types";
import { cn, errorMessage, timeAgo } from "@/utils/format";

function fromStored(m: ChatMessage): UiMessage {
  return {
    key: `m${m.id}`,
    id: m.id,
    role: m.role,
    content: m.message,
    intent: m.intent,
    citations: m.extra?.citations,
    verification: m.extra?.verification,
    followUps: m.extra?.follow_up_questions,
    clarifications: m.extra?.clarification_questions,
    trace: m.extra?.agent_trace,
  };
}

export default function AssistantPage() {
  return (
    <ProtectedPage>
      <AssistantPageContent />
    </ProtectedPage>
  );
}

function AssistantPageContent() {
  const { user } = useAuth();
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [loadingSession, setLoadingSession] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [language, setLanguage] = useState<Language>(user?.preferred_language ?? "en");
  const [historyOpen, setHistoryOpen] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const sessionRef = useRef<number | null>(null);
  sessionRef.current = sessionId;

  const loadSessions = useCallback(async () => {
    try {
      setSessions(await chatService.sessions());
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSessionsLoading(false);
    }
  }, []);

  const openSession = useCallback(async (id: number) => {
    setHistoryOpen(false);
    setLoadingSession(true);
    setError(null);
    try {
      const detail = await chatService.session(id);
      setSessionId(id);
      setMessages(detail.messages.map(fromStored));
      window.history.replaceState(null, "", `/assistant#session-${id}`);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoadingSession(false);
    }
  }, []);

  const send = useCallback(
    async (text: string) => {
      setError(null);
      setSending(true);
      const tempKey = `u${Date.now()}`;
      setMessages((prev) => [...prev, { key: tempKey, role: "user", content: text }]);
      try {
        const res = await chatService.send(text, sessionRef.current, language);
        if (!sessionRef.current) {
          setSessionId(res.session_id);
          window.history.replaceState(null, "", `/assistant#session-${res.session_id}`);
        }
        setMessages((prev) => [
          ...prev,
          {
            key: `a${res.message_id || Date.now()}`,
            id: res.message_id || undefined,
            role: "assistant",
            content: res.answer,
            intent: res.intent,
            citations: res.citations,
            verification: res.verification,
            followUps: res.follow_up_questions,
            clarifications: res.clarification_questions,
            trace: res.agent_trace,
          },
        ]);
        void loadSessions();
      } catch (err) {
        setMessages((prev) => [...prev, { key: `e${Date.now()}`, role: "assistant", content: errorMessage(err), error: true }]);
      } finally {
        setSending(false);
      }
    },
    [language, loadSessions],
  );

  useEffect(() => {
    void loadSessions();
    const match = /^#session-(\d+)$/.exec(window.location.hash);
    if (match) void openSession(Number(match[1]));

    const consumePending = () => {
      const pending = window.sessionStorage.getItem(PENDING_QUERY_KEY);
      if (pending) {
        window.sessionStorage.removeItem(PENDING_QUERY_KEY);
        setSessionId(null);
        setMessages([]);
        sessionRef.current = null;
        void send(pending);
      }
    };
    if (!match) consumePending();
    window.addEventListener("assistant:pending-query", consumePending);
    return () => window.removeEventListener("assistant:pending-query", consumePending);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  const newConversation = () => {
    setSessionId(null);
    setMessages([]);
    setError(null);
    setHistoryOpen(false);
    window.history.replaceState(null, "", "/assistant");
  };

  const removeSession = async (id: number) => {
    if (!window.confirm("Delete this conversation?")) return;
    try {
      await chatService.remove(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (id === sessionId) newConversation();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <div className="-mx-4 -my-6 flex h-[calc(100vh-4rem)] sm:-mx-6 lg:-mx-8">
      <aside
        className={cn(
          "absolute inset-y-16 left-0 z-10 w-72 shrink-0 flex-col border-r border-slate-200 bg-white md:static md:flex",
          historyOpen ? "flex" : "hidden",
        )}
      >
        <div className="p-3">
          <button
            onClick={newConversation}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-navy-900 px-3 py-2.5 text-sm font-medium text-white hover:bg-navy-800"
          >
            <MessageSquarePlus className="h-4 w-4" /> New conversation
          </button>
        </div>
        <p className="px-4 pb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">History</p>
        <div className="flex-1 space-y-0.5 overflow-y-auto px-2 pb-3">
          {sessionsLoading ? (
            <div className="p-2">
              <SkeletonList rows={4} />
            </div>
          ) : sessions.length === 0 ? (
            <p className="px-2 text-sm text-slate-500">No conversations yet.</p>
          ) : (
            sessions.map((s) => (
              <div
                key={s.id}
                className={cn(
                  "group flex items-center gap-1 rounded-lg px-2 py-2 text-sm",
                  s.id === sessionId ? "bg-navy-50 text-navy-900" : "text-slate-600 hover:bg-slate-50",
                )}
              >
                <button onClick={() => openSession(s.id)} className="min-w-0 flex-1 text-left">
                  <span className="block truncate font-medium">{s.title}</span>
                  <span className="text-xs text-slate-400">{timeAgo(s.updated_at)}</span>
                </button>
                <button
                  onClick={() => removeSession(s.id)}
                  className="rounded p-1 text-slate-400 opacity-0 hover:bg-white hover:text-red-600 group-hover:opacity-100 focus:opacity-100"
                  aria-label={`Delete ${s.title}`}
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))
          )}
        </div>
      </aside>

      <section className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-center gap-2 border-b border-slate-200 bg-white px-4 py-2 md:hidden">
          <button onClick={() => setHistoryOpen((v) => !v)} className="rounded-md p-1.5 text-slate-600 hover:bg-slate-100" aria-label="Toggle history">
            <PanelLeft className="h-5 w-5" />
          </button>
          <span className="text-sm font-medium text-slate-700">AI Assistant</span>
        </div>
        <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-8">
          <div className="mx-auto max-w-3xl space-y-6">
            {error && <Alert tone="error" onClose={() => setError(null)}>{error}</Alert>}
            {loadingSession ? (
              <SkeletonList rows={5} />
            ) : messages.length === 0 && !sending ? (
              <div className="py-10 text-center">
                <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-navy-900 text-white">
                  <Bot className="h-7 w-7" />
                </div>
                <h1 className="text-xl font-semibold text-slate-900">How can I help with Indian Standards today?</h1>
                <p className="mx-auto mt-2 max-w-lg text-sm text-slate-500">
                  Answers are generated from indexed BIS documents by specialised agents and checked by a verification agent before you see them.
                </p>
                <div className="mx-auto mt-8 grid max-w-2xl gap-2 sm:grid-cols-2">
                  {POPULAR_QUERIES.map((q) => (
                    <button
                      key={q}
                      onClick={() => send(q)}
                      className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-left text-sm text-slate-700 hover:border-navy-200 hover:bg-navy-50/40"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((m, i) => (
                <MessageBubble key={m.key} message={m} onFollowUp={send} isLast={i === messages.length - 1 && !sending} />
              ))
            )}
            {sending && (
              <div className="flex gap-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-navy-50 text-navy-800">
                  <Bot className="h-4 w-4" />
                </div>
                <div className="rounded-2xl rounded-tl-md border border-slate-200 bg-white px-4 py-3">
                  <AgentProgress />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        </div>
        <div className="border-t border-slate-200 bg-slate-50 px-4 py-3 sm:px-8">
          <div className="mx-auto max-w-3xl">
            <ChatInput onSend={send} disabled={sending} language={language} onLanguageChange={setLanguage} />
            <p className="mt-1.5 text-center text-[11px] text-slate-400">
              Preliminary AI guidance based on indexed documents. Verify with official BIS sources before acting.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
