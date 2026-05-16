import { http } from "./http";
import type { TicketCreateRequest, TicketItem } from "../types/ticket";

function normalizeList(data: any): TicketItem[] {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.items)) return data.items;
  if (Array.isArray(data?.data)) return data.data;
  if (Array.isArray(data?.results)) return data.results;
  return [];
}

export async function listTickets(): Promise<TicketItem[]> {
  const res = await http.get("/tickets");
  return normalizeList(res.data);
}

export async function createTicket(payload: TicketCreateRequest): Promise<any> {
  // 当前后端真实存在的是 /api/v1/tickets/ai-create
  // 不再尝试 POST /tickets，避免 405
  const res = await http.post("/tickets/ai-create", payload);
  return res.data;
}
