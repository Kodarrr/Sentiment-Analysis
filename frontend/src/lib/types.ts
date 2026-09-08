export interface Feedback {
  id: string;
  user_id: string;
  text: string;
  status: string;
  sentiment_label: string | null;
  sentiment_score: number | null;
  retry_count: number;
  created_at: string;
  processed_at: string | null;
}

export interface PaginatedFeedback {
  items: Feedback[];
  total: number;
  page: number;
  page_size: number;
}
