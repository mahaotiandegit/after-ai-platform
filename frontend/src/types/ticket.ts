export interface TicketItem {
  id?: string;
  ticket_no?: string;
  title?: string;
  summary?: string;
  customer_question?: string;
  category?: string;
  priority?: string;
  status?: string;
  assignee_id?: string;
  created_at?: string;
  createdAt?: string;
}

export interface TicketCreateRequest {
  order_id?: string;
  customer_question: string;
  title?: string;
  summary?: string;
  category?: string;
  priority?: string;
}
