import { describe, expect, it } from "vitest";
import { formatPercent } from "./portfolioMath";

describe("formatting", () => {
  it("formats percentages using German notation", () => {
    expect(formatPercent(0.123)).toBe("12,3 %");
  });

  it("keeps ISO dates parseable for the UI", () => {
    expect(new Intl.DateTimeFormat("de-DE").format(new Date("2024-01-15"))).toContain("2024");
  });
});
