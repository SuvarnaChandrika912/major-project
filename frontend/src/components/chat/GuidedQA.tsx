"use client";

import { useState } from "react";
import { ExternalLink, HelpCircle, Send } from "lucide-react";
import { AgentProgress } from "@/components/chat/AgentActivity";
import { AnswerView } from "@/components/chat/AnswerView";
import { Alert, Button, Card, CardHeader, Input, Select } from "@/components/ui";
import { useAuth } from "@/context/AuthContext";
import { useAsync } from "@/hooks/useAsync";
import { chatService } from "@/services/chat";
import type { AssistantAnswer, Language } from "@/types";
import { errorMessage, LANGUAGES } from "@/utils/format";

/** Topic-specific Q&A: FAQ prompts are answered live by the consumer agent from indexed documents. */
export function GuidedQA({ topic, faqs, placeholder }: {
  topic: "hallmarking" | "consumer";
  faqs: { group: string; questions: string[] }[];
  placeholder: string;
}) {
  const { user } = useAuth();
  const [query, setQuery] = useState("");
  const [language, setLanguage] = useState<Language>(user?.preferred_language ?? "en");
  const [asked, setAsked] = useState<string | null>(null);
  const [answer, setAnswer] = useState<AssistantAnswer | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const resources = useAsync(() => chatService.resources());

  const ask = async (q: string) => {
    if (q.trim().length < 2) return;
    setAsked(q);
    setLoading(true);
    setError(null);
    setAnswer(null);
    try {
      const fn = topic === "hallmarking" ? chatService.hallmarking : chatService.consumer;
      setAnswer(await fn(q.trim(), language));
      setQuery("");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
      <div className="space-y-4">
        <Card className="p-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void ask(query);
            }}
            className="flex flex-col gap-2 sm:flex-row"
          >
            <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={placeholder} aria-label="Your question" />
            <Select value={language} onChange={(e) => setLanguage(e.target.value as Language)} className="sm:w-36" aria-label="Answer language">
              {LANGUAGES.map((l) => <option key={l.value} value={l.value}>{l.native}</option>)}
            </Select>
            <Button type="submit" loading={loading} disabled={query.trim().length < 2}>
              <Send className="h-4 w-4" /> Ask
            </Button>
          </form>
        </Card>

        {error && <Alert tone="error">{error}</Alert>}
        {(loading || answer) && (
          <Card className="p-5">
            {asked && <p className="mb-3 text-sm font-medium text-slate-500">{asked}</p>}
            {loading ? (
              <AgentProgress />
            ) : (
              answer && (
                <>
                  <AnswerView answer={answer.answer} citations={answer.citations} verification={answer.verification} />
                  {answer.follow_up_questions.length > 0 && (
                    <div className="mt-4 flex flex-wrap gap-2">
                      {answer.follow_up_questions.map((q) => (
                        <button key={q} onClick={() => ask(q)} className="rounded-full border border-navy-100 bg-navy-50/60 px-3 py-1.5 text-sm text-navy-800 hover:bg-navy-50">
                          {q}
                        </button>
                      ))}
                    </div>
                  )}
                </>
              )
            )}
          </Card>
        )}

        <div className="grid gap-4 md:grid-cols-2">
          {faqs.map((group) => (
            <Card key={group.group}>
              <CardHeader title={group.group} icon={<HelpCircle className="h-4 w-4" />} />
              <ul className="divide-y divide-slate-100">
                {group.questions.map((q) => (
                  <li key={q}>
                    <button onClick={() => ask(q)} disabled={loading} className="w-full px-5 py-3 text-left text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50">
                      {q}
                    </button>
                  </li>
                ))}
              </ul>
            </Card>
          ))}
        </div>
      </div>

      <aside className="space-y-4">
        <Card>
          <CardHeader title="Official BIS resources" description="Verify marks and lodge complaints only through official channels." />
          <div className="divide-y divide-slate-100">
            {(resources.data ?? []).map((r) => (
              <a key={r.name} href={r.url} target="_blank" rel="noopener noreferrer" className="block px-5 py-3 hover:bg-slate-50">
                <p className="flex items-center gap-1 text-sm font-medium text-navy-800">
                  {r.name} <ExternalLink className="h-3.5 w-3.5" />
                </p>
                <p className="mt-0.5 text-xs text-slate-500">{r.purpose}</p>
              </a>
            ))}
            {resources.error && <p className="px-5 py-3 text-sm text-red-600">{resources.error}</p>}
          </div>
        </Card>
        <Alert tone="info">
          BIS SAATHI never confirms that a specific product or jeweller is certified. Always verify licence numbers and HUIDs through official BIS services.
        </Alert>
      </aside>
    </div>
  );
}
