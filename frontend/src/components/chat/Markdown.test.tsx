import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Markdown } from "./Markdown";

describe("Markdown", () => {
  it("turns numeric citation markers into clickable buttons", () => {
    const onClick = vi.fn();
    render(<Markdown content="Requirement applies [1] and also [2]." onCitationClick={onClick} />);
    const second = screen.getByRole("button", { name: "Show source 2" });
    expect(screen.getByRole("button", { name: "Show source 1" })).toBeInTheDocument();
    fireEvent.click(second);
    expect(onClick).toHaveBeenCalledWith(2);
  });

  it("keeps ordinary links as external links", () => {
    render(<Markdown content="Visit [BIS](https://www.bis.gov.in)." />);
    const link = screen.getByRole("link", { name: "BIS" });
    expect(link).toHaveAttribute("href", "https://www.bis.gov.in");
    expect(link).toHaveAttribute("target", "_blank");
  });
});
