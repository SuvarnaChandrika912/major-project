import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Verification } from "@/types";
import { VerificationBadge } from "./VerificationBadge";

const base: Verification = {
  evidence_status: "PARTIAL",
  confidence: 0.62,
  supported_claims: [],
  unsupported_claims: ["claim"],
  warnings: ["Evidence includes a superseded document."],
  outdated_documents: [],
};

describe("VerificationBadge", () => {
  it("renders nothing without verification data", () => {
    const { container } = render(<VerificationBadge />);
    expect(container).toBeEmptyDOMElement();
  });

  it("shows status, confidence and expandable notes", () => {
    render(<VerificationBadge verification={base} />);
    const button = screen.getByRole("button");
    expect(button).toHaveTextContent("Partially supported · 62% confidence");
    expect(button).toHaveTextContent("(2 notes)");
    fireEvent.click(button);
    expect(screen.getByText("Evidence includes a superseded document.")).toBeInTheDocument();
    expect(screen.getByText(/1 unsupported statement/)).toBeInTheDocument();
  });
});
