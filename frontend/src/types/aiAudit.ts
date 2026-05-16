export interface AiAuditLogItem {
  id?: string;
  trace_id?: string | null;
  scene?: string;
  provider?: string;
  model?: string;
  input_summary?: string;
  input_payload?: any;
  output_payload?: any;
  success?: boolean;
  error_message?: string | null;
  latency_ms?: number;
  status?: string;
  created_at?: string;
}
