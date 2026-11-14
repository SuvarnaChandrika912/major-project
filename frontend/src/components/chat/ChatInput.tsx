"use client";

import { useEffect, useRef, useState } from "react";
import { Languages, SendHorizonal } from "lucide-react";
import type { Language } from "@/types";
import { LANGUAGES } from "@/utils/format";

export function ChatInput({ onSend, disabled, language, onLanguageChange }: {
  onSend: (text: string) => void;
  disabled: boolean;
  language: Language;
  onLanguageChange: (lang: Language) => void;
}) {
  const [text, setText] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  }, [text]);

  const submit = () => {
    const value = text.trim();
    if (!value || disabled) return;
    onSend(value);
    setText("");
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-2 shadow-sm focus-within:border-navy-300 focus-within:ring-2 focus-within:ring-navy-100">
      <textarea
        ref={ref}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
        }}
        rows={1}
        maxLength={4000}
        placeholder="Ask about a product standard, certification, testing, hallmarking…"
        className="block max-h-44 w-full resize-none bg-transparent px-2 py-1.5 text-[15px] text-slate-800 placeholder:text-slate-400 focus:outline-none"
        aria-label="Message"
      />
      <div className="mt-1 flex items-center justify-between gap-2 px-1">
        <label className="inline-flex items-center gap-1.5 text-xs text-slate-500">
          <Languages className="h-4 w-4" />
          <span className="sr-only">Answer language</span>
          <select
            value={language}
            onChange={(e) => onLanguageChange(e.target.value as Language)}
            className="rounded-md border-0 bg-transparent py-1 text-xs font-medium text-slate-600 focus:outline-none focus:ring-1 focus:ring-navy-200"
          >
            {LANGUAGES.map((l) => (
              <option key={l.value} value={l.value}>
                {l.native}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={submit}
          disabled={disabled || !text.trim()}
          className="flex h-9 w-9 items-center justify-center rounded-xl bg-navy-900 text-white transition-colors hover:bg-navy-800 disabled:bg-slate-200 disabled:text-slate-400"
          aria-label="Send message"
        >
          <SendHorizonal className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
