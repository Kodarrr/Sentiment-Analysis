import useSWR from "swr";
import { apiFetch } from "@/lib/api";
import type { SentimentTrendPoint } from "@/lib/types";

interface UseSentimentTrendOptions {
  token: string | null;
  startDate?: string;
  endDate?: string;
}

interface UseSentimentTrendResult {
  data: SentimentTrendPoint[] | undefined;
  error: string | null;
  isLoading: boolean;
}

export function useSentimentTrend({
  token,
  startDate,
  endDate,
}: UseSentimentTrendOptions): UseSentimentTrendResult {
  const params = new URLSearchParams();
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  const query = params.toString();

  const key = token
    ? `/api/v1/feedback/stats/trend${query ? `?${query}` : ""}`
    : null;

  const { data, error, isLoading } = useSWR(key, (path: string) =>
    apiFetch<SentimentTrendPoint[]>(path, {}, token),
  );

  return {
    data,
    error: error instanceof Error ? error.message : error ? "Failed to load sentiment trend" : null,
    isLoading,
  };
}
