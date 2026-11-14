"use client";

import { useState } from "react";
import { Bot, HelpCircle, ThumbsDown, ThumbsUp } from "lucide-react";
import { chatService } from "@/services/chat";
import type { AgentTrace, Citation, Verification } from "@/types";
import { cn, INTENT_LABELS } from "@/utils/format";
import { AgentTraceView } from "./AgentActivity";
import { AnswerView } from "./AnswerView";

export interface UiMessage {
  key: string;
  id?: number;
  role: "user" | "assistant";
  content: string;
  intent?: string | null;
  citations?: Citation[];
  verification?: Verification;
  followUps?: string[];
  clarifications?: string[];
  trace?: AgentTrace[];
  error?: boolean;
}

function Feedback({ messageId }: { messageId: number }) {
  const [rating, setRating] = useState<-1 | 1 | null>(null);
  const [failed, setFailed] = useState(false);
  const send = async (value: -1 | 1) => {
    setRating(value);
    try {
      await chatService.feedback(messageId, value);
      setFailed(false);
    } catch {
      setFailed(true);
    }
  };
  return (
    <span className="inline-flex items-center gap-0.5">
      <button
        type="button"
        onClick={() => send(1)}
        aria-label="Helpful"
        className={cn("rounded-md p-1.5 hover:bg-slate-100", rating === 1 ? "text-emerald-600" : "text-slate-400")}
      >
        <ThumbsUp className="h-3.5 w-3.5" />
      </button>
      <button
        type="button"
        onClick={() => send(-1)}
        aria-label="Not helpful"
        className={cn("rounded-md p-1.5 hover:bg-slate-100", rating === -1 ? "text-red-600" : "text-slate-400")}
      >
        <ThumbsDown className="h-3.5 w-3.5" />
      </button>
      {failed && <span className="text-xs text-red-600">Feedback not saved</span>}
    </span>
  );
}

export function MessageBubble({ message, onFollowUp, isLast }: {
  message: UiMessage;
  onFollowUp: (q: string) => void;
  isLast: boolean;
}) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-navy-900 px-4 py-2.5 text-[15px] text-white">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-navy-50 text-navy-800">
        <Bot className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1 space-y-3">
        {message.intent && (
          <span className="text-xs font-medium text-slate-400">{INTENT_LABELS[message.intent] ?? message.intent}</span>
        )}
        <div className={cn("rounded-2xl rounded-tl-md border bg-white px-4 py-3", message.error ? "border-red-200" : "border-slate-200")}>
          {message.error ? (
            <p className="text-sm text-red-700">{message.content}</p>
          ) : (
            <AnswerView
              answer={message.content}
              citations={message.citations ?? []}
              verification={message.verification}
              actions={
                <>
                  {message.id ? <Feedback messageId={message.id} /> : null}
                  <AgentTraceView trace={message.trace} />
                </>
              }
            />
          )}
        </div>
        {isLast && !message.error && (message.followUps?.length || message.clarifications?.length) ? (
          <div className="flex flex-wrap gap-2">
            {[...(message.clarifications ?? []), ...(message.followUps ?? [])].map((q) => (
              <button
                key={q}
                type="button"
                onClick={() => onFollowUp(q)}
                className="inline-flex items-center gap-1.5 rounded-full border border-navy-100 bg-navy-50/60 px-3 py-1.5 text-left text-sm text-navy-800 hover:bg-navy-50"
              >
                <HelpCircle className="h-3.5 w-3.5 shrink-0" />
                {q}
              </button>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}
