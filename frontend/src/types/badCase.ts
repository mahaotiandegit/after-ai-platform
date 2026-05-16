export interface BadCaseItem {
  id?: string;
  source_type?: string;
  source_id?: string;
  scene?: string;
  question?: string;
  ai_output?: any;
  correction?: string;
  root_cause?: string;
  priority?: string;
  risk_level?: string;
  status?: string;
  tags?: string[];
  review_result?: string;
  created_at?: string;
  updated_at?: string;
}
