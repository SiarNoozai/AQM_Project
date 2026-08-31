import { describe, expect, it } from "vitest";
import { createAssetInput, syncAssetMetadata } from "./assets";

describe("asset metadata", () => {
  it("keeps a name selected from search", () => {
    const asset = createAssetInput({ ticker: "AAPL", name: "Apple Inc. (Suchergebnis)" });
    const synced = syncAssetMetadata(asset, 0, { preserveName: true });

    expect(synced.name).toBe("Apple Inc. (Suchergebnis)");
  });
});
