import useSWR from "swr";
import { apiFetch } from "@/lib/api";
import type { SentimentDistribution } from "@/lib/types";

interface UseSentimentDistributionOptions {
  token: string | null;
  startDate?: string;
  endDate?: string;
}

interface UseSentimentDistributionResult {
  data: SentimentDistribution | undefined;
  error: string | null;
  isLoading: boolean;
}

export function useSentimentDistribution({
  token,
  startDate,
  endDate,
}: UseSentimentDistributionOptions): UseSentimentDistributionResult {
  const params = new URLSearchParams();
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  const query = params.toString();

  const key = token
    ? `/api/v1/feedback/stats/distribution${query ? `?${query}` : ""}`
    : null;

  const { data, error, isLoading } = useSWR(key, (path: string) =>
    apiFetch<SentimentDistribution>(path, {}, token),
  );

  return {
    data,
    error: error instanceof Error ? error.message : error ? "Failed to load distribution" : null,
    isLoading,
  };
}

