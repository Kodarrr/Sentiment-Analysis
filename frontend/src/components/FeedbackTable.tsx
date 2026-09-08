import type { Feedback } from "@/lib/types";

function SentimentBadge({ label }: { label: string | null }) {
  if (!label) {
    return <span className="text-xs text-black/40 dark:text-white/40">pending</span>;
  }

  const isPositive = label === "POSITIVE";
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
        isPositive
          ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
          : "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300"
      }`}
    >
      {label}
    </span>
  );
}

export function FeedbackTable({ items }: { items: Feedback[] }) {
  if (items.length === 0) {
    return <p className="p-6 text-sm text-black/60 dark:text-white/60">No feedback found.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-black/10 text-black/60 dark:border-white/10 dark:text-white/60">
          <tr>
            <th className="px-4 py-2 font-medium">User</th>
            <th className="px-4 py-2 font-medium">Text</th>
            <th className="px-4 py-2 font-medium">Sentiment</th>
            <th className="px-4 py-2 font-medium">Score</th>
            <th className="px-4 py-2 font-medium">Status</th>
            <th className="px-4 py-2 font-medium">Submitted</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id} className="border-b border-black/5 dark:border-white/5">
              <td className="px-4 py-2">{item.user_id}</td>
              <td className="max-w-md truncate px-4 py-2" title={item.text}>
                {item.text}
              </td>
              <td className="px-4 py-2">
                <SentimentBadge label={item.sentiment_label} />
              </td>
              <td className="px-4 py-2">
                {item.sentiment_score !== null ? item.sentiment_score.toFixed(2) : "-"}
              </td>
              <td className="px-4 py-2">{item.status}</td>
              <td className="px-4 py-2">{new Date(item.created_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
