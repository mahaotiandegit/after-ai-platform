import { http } from "./http";
import type { BadCaseItem } from "../types/badCase";

function normalizeList(data: any): BadCaseItem[] {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.items)) return data.items;
  if (Array.isArray(data?.data)) return data.data;
  if (Array.isArray(data?.results)) return data.results;
  return [];
}

export async function listBadCases(): Promise<BadCaseItem[]> {
  const res = await http.get("/bad-cases");
  return normalizeList(res.data);
}
