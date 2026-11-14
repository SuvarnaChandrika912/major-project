"use client";

import { ProtectedPage } from "@/components/layout/ProtectedPage";
import { Gem } from "lucide-react";
import { GuidedQA } from "@/components/chat/GuidedQA";
import { PageHeader } from "@/components/ui";

const FAQS = [
  {
    group: "Understanding hallmarking",
    questions: [
      "What is hallmarking of gold and silver jewellery?",
      "What marks appear on hallmarked gold jewellery?",
      "Is hallmarking mandatory for gold jewellery?",
    ],
  },
  {
    group: "HUID and verification",
    questions: [
      "What is HUID and how is it assigned?",
      "How do I verify the HUID of my jewellery?",
      "What should I do if the HUID does not match?",
    ],
  },
  {
    group: "Jewellers",
    questions: [
      "How does a jeweller obtain BIS registration for hallmarking?",
      "What are an Assaying and Hallmarking Centre's responsibilities?",
    ],
  },
  {
    group: "Complaints",
    questions: [
      "How can I complain about incorrectly hallmarked jewellery?",
      "What information do I need to raise a hallmarking complaint?",
    ],
  },
];

export default function HallmarkingPage() {
  return (
    <ProtectedPage>
      <HallmarkingPageContent />
    </ProtectedPage>
  );
}

function HallmarkingPageContent() {
  return (
    <div>
      <PageHeader
        title="Hallmarking"
        description="Hallmarking, HUID and jeweller guidance answered from indexed BIS hallmarking documents."
        icon={<Gem className="h-5 w-5" />}
      />
      <GuidedQA topic="hallmarking" faqs={FAQS} placeholder="Ask about hallmarking, HUID or purity marks…" />
    </div>
  );
}
