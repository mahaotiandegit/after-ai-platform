import { http } from "./http";
import type { AiAuditLogItem } from "../types/aiAudit";

function normalizeList(data: any): AiAuditLogItem[] {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.items)) return data.items;
  if (Array.isArray(data?.data)) return data.data;
  if (Array.isArray(data?.results)) return data.results;
  return [];
}

export async function listAiAuditLogs(): Promise<AiAuditLogItem[]> {
  const res = await http.get("/ai-audit/logs");
  return normalizeList(res.data);
}
