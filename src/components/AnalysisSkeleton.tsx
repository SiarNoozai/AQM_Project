import { RefreshCw } from "lucide-react";

export function AnalysisSkeleton() {
  return (
    <section className="analysis-skeleton" aria-live="polite" aria-label="Analyse wird geladen">
      <div className="skeleton-intro">
        <RefreshCw className="spinning" size={17} />
        <div>
          <strong>Historische Daten werden ausgewertet</strong>
          <span>Kurse, Kennzahlen und die Vergleichsgewichtung werden vorbereitet.</span>
        </div>
      </div>
      <div className="skeleton-kpis" aria-hidden="true">
        {Array.from({ length: 4 }, (_, index) => (
          <div className="skeleton-block metric-skeleton" key={index}><span /><strong /><small /></div>
        ))}
      </div>
      <div className="skeleton-block chart-skeleton" aria-hidden="true">
        <span className="skeleton-chart-title" />
        <div className="skeleton-chart-lines" />
      </div>
      <div className="skeleton-detail-row" aria-hidden="true">
        <div className="skeleton-block detail-skeleton" />
        <div className="skeleton-block detail-skeleton" />
      </div>
    </section>
  );
}
