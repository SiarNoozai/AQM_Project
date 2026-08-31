import { describe, expect, it, vi } from "vitest";
import { exportPortfolioReport } from "./exportClient";

describe("exportClient", () => {
  it("rejects an error response before any download can be started", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Export fehlgeschlagen" }), { status: 500 })));

    await expect(exportPortfolioReport("pdf", {} as never)).rejects.toThrow("Export fehlgeschlagen");
    expect(fetch).toHaveBeenCalledOnce();
  });
});
