import { clsx } from "clsx";

interface Props {
  confidence: number;
  band?: string;
}

export function ConfidenceBadge({ confidence, band }: Props) {
  const pct = Math.round(confidence * 100);
  const level = band?.toLowerCase() || (pct >= 85 ? "high" : pct >= 50 ? "medium" : "low");

  return (
    <span
      className={clsx(
        "font-mono inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-medium tracking-tight",
        level === "high" && "bg-green-500/15 text-green-400",
        level === "medium" && "bg-yellow-500/15 text-yellow-400",
        level === "low" && "bg-orange-500/15 text-orange-400"
      )}
      title={`Confidence: ${pct}% (${level})`}
    >
      <span
        className={clsx(
          "h-1.5 w-1.5 rounded-full",
          level === "high" && "bg-green-500",
          level === "medium" && "bg-yellow-500",
          level === "low" && "bg-orange-500"
        )}
      />
      {pct}% · {level.toUpperCase()}
    </span>
  );
}
