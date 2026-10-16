import type { Feedback } from "@/lib/types";

const LABEL_METADATA: Record<string, { desc: string; style: string }> = {
  SN: {
    desc: "Strongly Negative",
    style: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300 font-semibold",
  },
  WN: {
    desc: "Weakly Negative",
    style: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  },
  NU: {
    desc: "Neutral",
    style: "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300",
  },
  WP: {
    desc: "Weakly Positive",
    style: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300",
  },
  SP: {
    desc: "Strongly Positive",
    style: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 font-semibold",
  },
  NEGATIVE: {
    desc: "Negative (English DistilBERT)",
    style: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
  },
  POSITIVE: {
    desc: "Positive (English DistilBERT)",
    style: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
  },
};

function SentimentBadge({ label, polarity }: { label: string | null; polarity?: string | null }) {
  if (!label) {
    return <span className="text-xs text-black/40 dark:text-white/40">pending</span>;
  }

  const meta = LABEL_METADATA[label.toUpperCase()] ?? {
    desc: polarity ? `Polarity: ${polarity}` : label,
    style: "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300",
  };

  return (
    <span
      title={`${label}: ${meta.desc}`}
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs ${meta.style}`}
    >
      <span>{label}</span>
      {polarity && (
        <span className="text-[10px] opacity-70">({polarity.slice(0, 3)})</span>
      )}
    </span>
  );
}

export function FeedbackTable({ items }: { items: Feedback[] }) {
  if (items.length === 0) {
    return <p className="p-6 text-sm text-black/60 dark:text-white/60">No feedback found.</p>;
  }

  return (
    <div className="space-y-2">
      {/* Legend Tooltip Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-black/5 px-4 py-2 text-xs text-black/60 dark:border-white/5 dark:text-white/60">
        <span className="font-medium">Feedback Stream</span>
        <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
          <span className="font-medium text-black/70 dark:text-white/70">Bangla 5-Classes:</span>
          <span title="Strongly Negative" className="cursor-help rounded bg-red-100 px-1 py-0.5 font-medium text-red-800 dark:bg-red-950 dark:text-red-300">SN</span>
          <span title="Weakly Negative" className="cursor-help rounded bg-amber-100 px-1 py-0.5 font-medium text-amber-800 dark:bg-amber-950 dark:text-amber-300">WN</span>
          <span title="Neutral" className="cursor-help rounded bg-zinc-100 px-1 py-0.5 font-medium text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">NU</span>
          <span title="Weakly Positive" className="cursor-help rounded bg-emerald-50 px-1 py-0.5 font-medium text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300">WP</span>
          <span title="Strongly Positive" className="cursor-help rounded bg-emerald-100 px-1 py-0.5 font-medium text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">SP</span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-black/10 text-black/60 dark:border-white/10 dark:text-white/60">
            <tr>
              <th className="px-4 py-2 font-medium">User</th>
              <th className="px-4 py-2 font-medium">Text</th>
              <th className="px-4 py-2 font-medium">Label</th>
              <th className="px-4 py-2 font-medium">Confidence</th>
              <th className="px-4 py-2 font-medium">Model</th>
              <th className="px-4 py-2 font-medium">Status</th>
              <th className="px-4 py-2 font-medium">Submitted</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const conf = item.confidence ?? item.sentiment_score;
              const modelShortName = item.model_id
                ? item.model_id.includes("banglabert")
                  ? "BanglaBERT"
                  : "DistilBERT"
                : "-";

              return (
                <tr key={item.id} className="border-b border-black/5 dark:border-white/5">
                  <td className="px-4 py-2 font-mono text-xs">{item.user_id}</td>
                  <td className="max-w-md truncate px-4 py-2" title={item.text}>
                    {item.text}
                  </td>
                  <td className="px-4 py-2">
                    <SentimentBadge label={item.sentiment_label} polarity={item.sentiment_polarity} />
                  </td>
                  <td className="px-4 py-2">
                    {conf !== null && conf !== undefined ? (
                      <span className="font-mono text-xs">
                        {(conf * 100).toFixed(1)}%
                      </span>
                    ) : (
                      "-"
                    )}
                  </td>
                  <td className="px-4 py-2">
                    <span
                      title={item.model_id ?? "Unknown"}
                      className="rounded bg-black/5 px-1.5 py-0.5 text-xs text-black/70 dark:bg-white/10 dark:text-white/70"
                    >
                      {modelShortName}
                    </span>
                  </td>
                  <td className="px-4 py-2">{item.status}</td>
                  <td className="px-4 py-2 text-xs text-black/60 dark:text-white/60">
                    {new Date(item.created_at).toLocaleString()}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
