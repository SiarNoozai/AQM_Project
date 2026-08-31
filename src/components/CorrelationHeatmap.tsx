type HeatmapAsset = { id: string; ticker: string };

export function CorrelationHeatmap({ assets, values }: { assets: HeatmapAsset[]; values: number[][] }) {
  return (
    <div className="heatmap" role="table" aria-label="Korrelationsmatrix">
      <div className="heatmap-row header-row" role="row" style={{ gridTemplateColumns: `60px repeat(${assets.length}, minmax(52px, 1fr))` }}>
        <span aria-hidden="true" />
        {assets.map((asset, index) => <strong role="columnheader" key={asset.id}>{asset.ticker || `P${index + 1}`}</strong>)}
      </div>
      {assets.map((asset, rowIndex) => (
        <div className="heatmap-row" role="row" key={asset.id} style={{ gridTemplateColumns: `60px repeat(${assets.length}, minmax(52px, 1fr))` }}>
          <strong role="rowheader">{asset.ticker || `P${rowIndex + 1}`}</strong>
          {assets.map((columnAsset, columnIndex) => {
            const value = values[rowIndex]?.[columnIndex] ?? 0;
            const rowLabel = asset.ticker || `P${rowIndex + 1}`;
            const columnLabel = columnAsset.ticker || `P${columnIndex + 1}`;
            return <span className="heatmap-cell" role="cell" key={`${asset.id}-${columnAsset.id}`} style={{ backgroundColor: getCorrelationColor(value) }} aria-label={`${rowLabel} zu ${columnLabel}: ${value.toFixed(2)}`}>{value.toFixed(2)}</span>;
          })}
        </div>
      ))}
    </div>
  );
}

function getCorrelationColor(value: number) {
  const clamped = Math.max(-1, Math.min(1, value));
  if (clamped < 0) {
    const intensity = Math.round(225 + clamped * 55);
    return `rgb(${intensity}, ${intensity + 15}, 246)`;
  }
  const intensity = Math.round(244 - clamped * 82);
  return `rgb(${intensity - 8}, ${intensity + 8}, ${intensity - 30})`;
}
