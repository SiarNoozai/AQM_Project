import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "./App";

describe("Portfolio Builder", () => {
  it("does not render calculated demo KPIs before the first analysis", () => {
    render(<App />);

    expect(screen.getByText("Noch keine Auswertung vorhanden")).toBeInTheDocument();
    expect(screen.queryByText("Sharpe Ratio")).not.toBeInTheDocument();
  });

  it("disables analysis actions when the weight sum is invalid", () => {
    render(<App />);
    fireEvent.change(screen.getByLabelText("Gewichtung AAPL"), { target: { value: "20" } });

    expect(screen.getByText("85 %")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /auswerten|analyse starten/i }).every((button) => (button as HTMLButtonElement).disabled)).toBe(true);
  });
});
