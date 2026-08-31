import type { ReactNode } from "react";

type MetricCardProps = {
  label: string;
  value: string;
  helper: string;
  icon: ReactNode;
  tone?: "positive" | "warning" | "neutral";
};

export function MetricCard({ label, value, helper, icon, tone = "neutral" }: MetricCardProps) {
  return (
    <article className={`metric-card ${tone}`}>
      <div className="metric-label-row">
        <span>{label}</span>
        <div className="metric-icon">{icon}</div>
      </div>
      <strong>{value}</strong>
      <p>{helper}</p>
    </article>
  );
}
