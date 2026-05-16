import { http } from "./http";
import type { AnalyticsAskRequest, AnalyticsAskResponse } from "../types/analytics";

export async function askAnalytics(payload: AnalyticsAskRequest): Promise<AnalyticsAskResponse> {
  const res = await http.post("/analytics/ask", payload);
  return res.data;
}
