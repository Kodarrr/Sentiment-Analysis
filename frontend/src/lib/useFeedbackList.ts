import useSWR from "swr";
import { apiFetch } from "@/lib/api";
import type { PaginatedFeedback } from "@/lib/types";

interface UseFeedbackListOptions {
  token: string | null;
  page: number;
  pageSize?: number;
  sentiment?: string;
  startDate?: string;
  endDate?: string;
}

interface UseFeedbackListResult {
  data: PaginatedFeedback | undefined;
  error: string | null;
  isLoading: boolean;
  refetch: () => void;
}

export function useFeedbackList({
  token,
  page,
  pageSize = 20,
  sentiment,
  startDate,
  endDate,
}: UseFeedbackListOptions): UseFeedbackListResult {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (sentiment) params.set("sentiment", sentiment);
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);

  const key = token ? `/api/v1/feedback?${params.toString()}` : null;

  const { data, error, isLoading, mutate } = useSWR(key, (path: string) =>
    apiFetch<PaginatedFeedback>(path, {}, token),
  );

  return {
    data,
    error: error instanceof Error ? error.message : error ? "Failed to load feedback" : null,
    isLoading,
    refetch: () => void mutate(),
  };
}
