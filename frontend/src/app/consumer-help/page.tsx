"use client";

import { ProtectedPage } from "@/components/layout/ProtectedPage";
import { Users } from "lucide-react";
import { GuidedQA } from "@/components/chat/GuidedQA";
import { PageHeader } from "@/components/ui";

const FAQS = [
  {
    group: "ISI mark",
    questions: [
      "What does the ISI mark mean?",
      "How can I check whether an ISI mark is genuine?",
      "Which products must carry the ISI mark?",
    ],
  },
  {
    group: "Certification marks",
    questions: [
      "What other certification marks does BIS operate?",
      "How do I verify a BIS licence number printed on a product?",
    ],
  },
  {
    group: "Complaints",
    questions: [
      "How do I file a complaint about a substandard ISI-marked product?",
      "How can I report misuse of the ISI mark?",
    ],
  },
  {
    group: "Product quality",
    questions: [
      "What should I check before buying an electrical appliance?",
      "Where can I find the standard that applies to a product I bought?",
    ],
  },
];

export default function ConsumerHelpPage() {
  return (
    <ProtectedPage>
      <ConsumerHelpPageContent />
    </ProtectedPage>
  );
}

function ConsumerHelpPageContent() {
  return (
    <div>
      <PageHeader
        title="Consumer Help"
        description="ISI mark information, certification-mark verification and complaint procedures from official BIS consumer documents."
        icon={<Users className="h-5 w-5" />}
      />
      <GuidedQA topic="consumer" faqs={FAQS} placeholder="Ask about ISI marks, verification or complaints…" />
    </div>
  );
}
