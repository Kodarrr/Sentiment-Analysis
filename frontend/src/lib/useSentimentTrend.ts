import useSWR from "swr";
import { apiFetch } from "@/lib/api";
import type { SentimentTrendPoint } from "@/lib/types";

interface UseSentimentTrendResult {
  data: SentimentTrendPoint[] | undefined;
  error: string | null;
  isLoading: boolean;
}

export function useSentimentTrend(token: string | null): UseSentimentTrendResult {
  const key = token ? "/api/v1/feedback/stats/trend" : null;

  const { data, error, isLoading } = useSWR(key, (path: string) =>
    apiFetch<SentimentTrendPoint[]>(path, {}, token),
  );

  return {
    data,
    error: error instanceof Error ? error.message : error ? "Failed to load sentiment trend" : null,
    isLoading,
  };
}
