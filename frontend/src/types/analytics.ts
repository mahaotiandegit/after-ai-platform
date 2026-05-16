export interface AnalyticsAskRequest {
  question: string;
  limit?: number;
}

export interface AnalyticsAskResponse {
  question?: string;
  intent?: string;
  sql?: string;
  columns?: string[];
  rows?: Record<string, any>[];
  summary?: string;
}
