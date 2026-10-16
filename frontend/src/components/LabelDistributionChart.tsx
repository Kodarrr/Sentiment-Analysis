"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { SentimentDistribution } from "@/lib/types";

const LABEL_COLORS: Record<string, string> = {
  SN: "#ef4444", // Red - Strongly Negative
  WN: "#f59e0b", // Amber - Weakly Negative
  NU: "#71717a", // Zinc - Neutral
  WP: "#34d399", // Mint Green - Weakly Positive
  SP: "#059669", // Deep Emerald - Strongly Positive
  NEGATIVE: "#dc2626",
  POSITIVE: "#16a34a",
};

const LABEL_NAMES: Record<string, string> = {
  SN: "Strongly Negative (SN)",
  WN: "Weakly Negative (WN)",
  NU: "Neutral (NU)",
  WP: "Weakly Positive (WP)",
  SP: "Strongly Positive (SP)",
  NEGATIVE: "Negative (EN)",
  POSITIVE: "Positive (EN)",
};

export function LabelDistributionChart({
  distribution,
}: {
  distribution: SentimentDistribution | undefined;
}) {
  if (!distribution || distribution.total === 0) {
    return (
      <p className="p-6 text-sm text-black/60 dark:text-white/60">
        No sentiment distribution data yet.
      </p>
    );
  }

  // Desired ordering: SN -> WN -> NU -> WP -> SP -> NEGATIVE -> POSITIVE
  const order = ["SN", "WN", "NU", "WP", "SP", "NEGATIVE", "POSITIVE"];
  const chartData = order
    .filter((key) => key in distribution.labels)
    .map((key) => ({
      key,
      name: LABEL_NAMES[key] ?? key,
      count: distribution.labels[key] || 0,
      fill: LABEL_COLORS[key] ?? "#8884d8",
    }));

  // Include any extra labels not in order list
  for (const [k, count] of Object.entries(distribution.labels)) {
    if (!order.includes(k)) {
      chartData.push({
        key: k,
        name: k,
        count,
        fill: LABEL_COLORS[k] ?? "#8884d8",
      });
    }
  }

  return (
    <div className="h-72 w-full p-4">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
          <CartesianGrid stroke="#8a8a86" strokeOpacity={0.2} vertical={false} />
          <XAxis dataKey="key" stroke="#71717a" fontSize={12} tickLine={false} />
          <YAxis allowDecimals={false} stroke="#71717a" fontSize={12} tickLine={false} />
          <Tooltip
            formatter={(value, _name, props) => [
              `${value} feedback (${(((Number(value) || 0) / distribution.total) * 100).toFixed(1)}%)`,
              props.payload.name,
            ]}
            contentStyle={{ fontSize: 12 }}
          />
          <Bar dataKey="count" radius={[4, 4, 0, 0]}>
            {chartData.map((entry) => (
              <Cell key={`cell-${entry.key}`} fill={entry.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
