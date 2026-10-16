"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { SentimentTrendPoint } from "@/lib/types";

// Fixed status colors (not categorical): POSITIVE maps to "good", NEGATIVE to
// "critical" - these are mode-invariant by design, so no separate dark values.
const COLORS = {
  positive: "#10b981",
  neutral: "#71717a",
  negative: "#ef4444",
  grid: "#8a8a86",
  text: "#71717a",
};

function formatDate(value: string) {
  return new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function SentimentTrendChart({ data }: { data: SentimentTrendPoint[] }) {
  if (data.length === 0) {
    return (
      <p className="p-6 text-sm text-black/60 dark:text-white/60">
        Not enough data yet to show a trend.
      </p>
    );
  }

  return (
    <div className="h-72 w-full p-4">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={COLORS.grid} strokeOpacity={0.2} vertical={false} />
          <XAxis
            dataKey="date"
            tickFormatter={formatDate}
            stroke={COLORS.text}
            fontSize={12}
            tickLine={false}
          />
          <YAxis allowDecimals={false} stroke={COLORS.text} fontSize={12} tickLine={false} />
          <Tooltip
            labelFormatter={(value) => formatDate(String(value))}
            contentStyle={{ fontSize: 12 }}
          />
          <Legend verticalAlign="top" height={32} />
          <Line
            type="monotone"
            dataKey="positive_count"
            name="Positive"
            stroke={COLORS.positive}
            strokeWidth={2}
            dot={{ r: 3 }}
          />
          <Line
            type="monotone"
            dataKey="neutral_count"
            name="Neutral"
            stroke={COLORS.neutral}
            strokeWidth={2}
            strokeDasharray="3 3"
            dot={{ r: 3 }}
          />
          <Line
            type="monotone"
            dataKey="negative_count"
            name="Negative"
            stroke={COLORS.negative}
            strokeWidth={2}
            dot={{ r: 3 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
