import type { ApiSectorAllocation } from "../lib/api";

const percentFormatter = new Intl.NumberFormat("de-DE", { style: "percent", minimumFractionDigits: 0, maximumFractionDigits: 0 });

export function SectorAllocationBars({ items }: { items: ApiSectorAllocation[] }) {
  return (
    <div className="sector-list">
      {items.map((item) => (
        <article className="sector-row" key={item.sector}>
          <div className="sector-row-head"><strong>{item.sector}</strong><span>{percentFormatter.format(item.weight)}</span></div>
          <div className="sector-bar-track" aria-hidden="true"><div className="sector-bar-fill" style={{ width: `${Math.max(item.weight * 100, 6)}%` }} /></div>
          <small>{item.tickers.join(", ")}</small>
        </article>
      ))}
    </div>
  );
}
