"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const CITATION_RE = /\[(\d{1,3})\](?!\()/g;

/** Renders an AI answer; numeric citation markers like [2] become clickable chips. */
export function Markdown({ content, onCitationClick }: { content: string; onCitationClick?: (index: number) => void }) {
  const withLinks = content.replace(CITATION_RE, (_m, n) => `[\\[${n}\\]](#cite-${n})`);
  return (
    <div className="prose-answer">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }) => {
            if (href?.startsWith("#cite-")) {
              const index = Number(href.slice(6));
              return (
                <button
                  type="button"
                  className="citation-marker"
                  onClick={() => onCitationClick?.(index)}
                  aria-label={`Show source ${index}`}
                >
                  {index}
                </button>
              );
            }
            return (
              <a href={href} target="_blank" rel="noopener noreferrer">
                {children}
              </a>
            );
          },
        }}
      >
        {withLinks}
      </ReactMarkdown>
    </div>
  );
}
