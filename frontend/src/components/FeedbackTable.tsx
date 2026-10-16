import type { Feedback } from "@/lib/types";

const LABEL_METADATA: Record<string, { desc: string; style: string }> = {
  SP: {
    desc: "Strongly Positive (গাঢ় ইতিবাচক)",
    style: "bg-emerald-100 text-emerald-800 border-emerald-300 dark:bg-emerald-950 dark:text-emerald-300 dark:border-emerald-800",
  },
  WP: {
    desc: "Weakly Positive (হালকা ইতিবাচক)",
    style: "bg-teal-100 text-teal-800 border-teal-300 dark:bg-teal-950 dark:text-teal-300 dark:border-teal-800",
  },
  NU: {
    desc: "Neutral (নিরপেক্ষ)",
    style: "bg-slate-100 text-slate-700 border-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700",
  },
  WN: {
    desc: "Weakly Negative (হালকা নেতিবাচক)",
    style: "bg-amber-100 text-amber-800 border-amber-300 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-800",
  },
  SN: {
    desc: "Strongly Negative (গাঢ় নেতিবাচক)",
    style: "bg-rose-100 text-rose-800 border-rose-300 dark:bg-rose-950 dark:text-rose-300 dark:border-rose-800 font-bold",
  },
  POSITIVE: {
    desc: "Positive (English DistilBERT)",
    style: "bg-emerald-100 text-emerald-800 border-emerald-300 dark:bg-emerald-950 dark:text-emerald-300 dark:border-emerald-800",
  },
  NEGATIVE: {
    desc: "Negative (English DistilBERT)",
    style: "bg-rose-100 text-rose-800 border-rose-300 dark:bg-rose-950 dark:text-rose-300 dark:border-rose-800 font-bold",
  },
};

function SentimentBadge({ label, polarity }: { label: string | null; polarity?: string | null }) {
  if (!label) {
    return <span className="text-xs text-slate-400 italic">pending</span>;
  }

  const meta = LABEL_METADATA[label.toUpperCase()] ?? {
    desc: polarity ? `Polarity: ${polarity}` : label,
    style: "bg-slate-100 text-slate-700 border-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700",
  };

  return (
    <span
      title={`${label}: ${meta.desc}`}
      className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-semibold shadow-xs ${meta.style}`}
    >
      <span>{label}</span>
      {polarity && (
        <span className="text-[10px] opacity-75 font-normal">({polarity.slice(0, 3)})</span>
      )}
    </span>
  );
}

export function FeedbackTable({ items }: { items: Feedback[] }) {
  if (items.length === 0) {
    return (
      <div className="p-8 text-center text-sm text-slate-500">
        No customer feedback found matching the selected filters.
      </div>
    );
  }

  return (
    <div className="w-full">
      {/* Legend Tooltip Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 bg-slate-50/50 px-4 py-2.5 text-xs text-slate-500 dark:border-slate-800/80 dark:bg-slate-900/50">
        <span className="font-semibold text-slate-700 dark:text-slate-300">Feedback Stream</span>
        <div className="flex flex-wrap items-center gap-2 text-[11px]">
          <span className="font-medium text-slate-400">Bangla 5-Classes:</span>
          <span title="Strongly Negative (গাঢ় নেতিবাচক)" className="cursor-help rounded-md border border-rose-200 bg-rose-50 px-1.5 py-0.5 font-bold text-rose-700 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-300">SN</span>
          <span title="Weakly Negative (হালকা নেতিবাচক)" className="cursor-help rounded-md border border-amber-200 bg-amber-50 px-1.5 py-0.5 font-semibold text-amber-700 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-300">WN</span>
          <span title="Neutral (নিরপেক্ষ)" className="cursor-help rounded-md border border-slate-200 bg-slate-100 px-1.5 py-0.5 font-medium text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">NU</span>
          <span title="Weakly Positive (হালকা ইতিবাচক)" className="cursor-help rounded-md border border-teal-200 bg-teal-50 px-1.5 py-0.5 font-semibold text-teal-700 dark:border-teal-900 dark:bg-teal-950 dark:text-teal-300">WP</span>
          <span title="Strongly Positive (গাঢ় ইতিবাচক)" className="cursor-help rounded-md border border-emerald-200 bg-emerald-50 px-1.5 py-0.5 font-bold text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-300">SP</span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-100 bg-slate-50/30 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:border-slate-800 dark:bg-slate-900/30 dark:text-slate-400">
            <tr>
              <th className="px-4 py-3">User</th>
              <th className="px-4 py-3">Feedback Text</th>
              <th className="px-4 py-3">Sentiment</th>
              <th className="px-4 py-3">Confidence</th>
              <th className="px-4 py-3">Model</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Submitted</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
            {items.map((item) => {
              const conf = item.confidence ?? item.sentiment_score;
              const isBangla = item.model_id?.includes("bangla") || false;

              return (
                <tr
                  key={item.id}
                  className="transition hover:bg-slate-50/80 dark:hover:bg-slate-800/40"
                >
                  <td className="px-4 py-3 font-mono text-xs text-slate-700 dark:text-slate-300">
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2 py-0.5 dark:bg-slate-800">
                      <span className="h-1.5 w-1.5 rounded-full bg-slate-400"></span>
                      {item.user_id}
                    </span>
                  </td>
                  <td className="max-w-md px-4 py-3 text-slate-900 dark:text-slate-100 font-normal">
                    <p className="line-clamp-2" title={item.text}>
                      {item.text}
                    </p>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <SentimentBadge label={item.sentiment_label} polarity={item.sentiment_polarity} />
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {conf !== null && conf !== undefined ? (
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono text-xs font-semibold text-slate-800 dark:text-slate-200">
                          {(conf * 100).toFixed(1)}%
                        </span>
                      </div>
                    ) : (
                      <span className="text-slate-400">-</span>
                    )}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {item.model_id ? (
                      <span
                        title={item.model_id}
                        className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-semibold ${
                          isBangla
                            ? "bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800"
                            : "bg-indigo-50 text-indigo-700 border border-indigo-200 dark:bg-indigo-950/60 dark:text-indigo-300 dark:border-indigo-800"
                        }`}
                      >
                        {isBangla ? "🇧🇩 BanglaBERT" : "🇬🇧 DistilBERT"}
                      </span>
                    ) : (
                      <span className="text-slate-400 text-xs">-</span>
                    )}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span
                      className={`inline-flex items-center gap-1 text-xs font-semibold ${
                        item.status === "processed"
                          ? "text-emerald-600 dark:text-emerald-400"
                          : item.status === "failed"
                            ? "text-rose-600 dark:text-rose-400"
                            : "text-amber-500"
                      }`}
                    >
                      <span className={`h-1.5 w-1.5 rounded-full ${
                        item.status === "processed"
                          ? "bg-emerald-500"
                          : item.status === "failed"
                            ? "bg-rose-500"
                            : "bg-amber-400 animate-pulse"
                      }`} />
                      {item.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-xs text-slate-500 dark:text-slate-400">
                    {new Date(item.created_at).toLocaleString([], {
                      month: "short",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
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
