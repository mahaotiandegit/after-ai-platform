export interface KnowledgeAskRequest {
  question: string;
  top_k?: number;
}

export interface KnowledgeCitation {
  document_id?: string;
  document_title?: string;
  source?: string;
  page?: number;
  content?: string;
}

export interface KnowledgeChunk {
  id?: string;
  content?: string;
  score?: number;
  document_title?: string;
  source?: string;
}

export interface KnowledgeAskResponse {
  question?: string;
  answer?: string;
  answer_summary?: string;
  citations?: KnowledgeCitation[];
  chunks?: KnowledgeChunk[];
  hits?: KnowledgeChunk[];
}
