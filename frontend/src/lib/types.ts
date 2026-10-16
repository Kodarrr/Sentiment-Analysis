export interface Feedback {
  id: string;
  user_id: string;
  text: string;
  status: string;
  sentiment_label: string | null;
  sentiment_score: number | null;
  sentiment_polarity?: string | null;
  confidence?: number | null;
  probabilities?: Record<string, number> | null;
  model_id?: string | null;
  model_revision?: string | null;
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

export interface SentimentTrendPoint {
  date: string;
  positive_count: number;
  negative_count: number;
  neutral_count?: number;
}

export interface SentimentDistribution {
  labels: Record<string, number>;
  polarities: Record<string, number>;
  total: number;
}

