import { http } from "./http";
import type { KnowledgeAskRequest, KnowledgeAskResponse } from "../types/knowledge";

export async function askKnowledge(payload: KnowledgeAskRequest): Promise<KnowledgeAskResponse> {
  const res = await http.post("/knowledge/ask", payload);
  return res.data;
}
