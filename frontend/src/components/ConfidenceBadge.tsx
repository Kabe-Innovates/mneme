import { clsx } from "clsx";

interface Props {
  confidence: number;
}

export function ConfidenceBadge({ confidence }: Props) {
  const pct = Math.round(confidence * 100);
  const level = pct >= 80 ? "high" : pct >= 50 ? "medium" : "low";

  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
        level === "high" && "bg-green-100 text-green-700",
        level === "medium" && "bg-yellow-100 text-yellow-700",
        level === "low" && "bg-orange-100 text-orange-700"
      )}
      title="Confidence score"
    >
      <span
        className={clsx(
          "h-1.5 w-1.5 rounded-full",
          level === "high" && "bg-green-500",
          level === "medium" && "bg-yellow-500",
          level === "low" && "bg-orange-500"
        )}
      />
      {pct}% confidence
    </span>
  );
}
