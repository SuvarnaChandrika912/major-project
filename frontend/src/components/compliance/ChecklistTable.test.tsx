import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ChecklistTable } from "./ChecklistTable";

describe("ChecklistTable", () => {
  it("shows an empty message when there are no items", () => {
    render(<ChecklistTable items={[]} />);
    expect(screen.getByText(/No checklist items/)).toBeInTheDocument();
  });

  it("renders each requirement with its status label", () => {
    render(
      <ChecklistTable
        items={[
          { requirement: "Marking on the product", clause_number: "8.1", citation: "[1]", status: "meets", notes: "" },
          { requirement: "Rated voltage", clause_number: null, citation: "", status: "missing_information", notes: "Not provided" },
        ]}
      />,
    );
    expect(screen.getByText("Marking on the product")).toBeInTheDocument();
    expect(screen.getByText("8.1")).toBeInTheDocument();
    expect(screen.getByText("Meets")).toBeInTheDocument();
    expect(screen.getByText("Missing information")).toBeInTheDocument();
    expect(screen.getByText("Not provided")).toBeInTheDocument();
  });
});
