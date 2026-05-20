import { useEffect, useState } from "react";

type Ticket = {
  id: string;
  ticket_no: string;
  order_id?: string | null;
  customer_question: string;
  category: string;
  priority: string;
  title: string;
  summary: string;
  status: string;
  assignee_id?: string | null;
  created_by_id?: string | null;
  created_at: string;
  updated_at: string;
};

type TicketListResponse = {
  total: number;
  items: Ticket[];
};

type TicketAutoCreateResponse = {
  llm_provider?: string | null;
  llm_model?: string | null;
  used_llm?: boolean;
  classification_source?: string | null;
  recommended_action?: string | null;
  ticket: Ticket;
  classification_reason: string;
  next_action: string;
};

type TicketActionResponse = {
  ticket: Ticket;
  action: string;
  message: string;
};

function StatusPill({ value }: { value: string }) {
  return <span className={`status-pill status-${value}`}>{value}</span>;
}

function formatDate(value?: string | null) {
  if (!value) return "-";
  return value.replace("T", " ").slice(0, 19);
}

const ticketStatusSteps = [
  { key: "open", label: "待处理" },
  { key: "processing", label: "处理中" },
  { key: "resolved", label: "已解决" },
  { key: "closed", label: "已关闭" },
];



export default function TicketCenter() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [total, setTotal] = useState(0);
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null);

  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");

  const [createOrderNo, setCreateOrderNo] = useState("ORDER-20260515-0002");
  const [createQuestion, setCreateQuestion] = useState("物流一直在运输中，我想修改收货地址，能不能帮我处理？");
  const [createResult, setCreateResult] = useState<TicketAutoCreateResponse | null>(null);

  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function loadTickets() {
    setLoading(true);
    setError("");

    try {
      const params = new URLSearchParams();
      params.set("limit", "50");
      if (statusFilter) params.set("status", statusFilter);
      if (priorityFilter) params.set("priority", priorityFilter);
      if (categoryFilter) params.set("category", categoryFilter);

      const response = await fetch(`/api/v1/tickets?${params.toString()}`);

      if (!response.ok) {
        const text = await response.text();
        throw new Error(`加载工单失败：HTTP ${response.status} ${text}`);
      }

      const data = (await response.json()) as TicketListResponse;
      setTickets(data.items);
      setTotal(data.total);

      if (data.items.length > 0 && !selectedTicket) {
        setSelectedTicket(data.items[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "未知错误");
    } finally {
      setLoading(false);
    }
  }

  async function createTicket() {
    setActionLoading(true);
    setError("");
    setMessage("");
    setCreateResult(null);

    try {
      const response = await fetch("/api/v1/tickets/auto-create", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          order_no: createOrderNo.trim() || null,
          customer_question: createQuestion.trim(),
        }),
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(`创建工单失败：HTTP ${response.status} ${text}`);
      }

      const data = (await response.json()) as TicketAutoCreateResponse;
      setCreateResult(data);
      setSelectedTicket(data.ticket);
      setMessage(`工单创建成功：${data.ticket.ticket_no}`);
      await loadTickets();
    } catch (err) {
      setError(err instanceof Error ? err.message : "未知错误");
    } finally {
      setActionLoading(false);
    }
  }

  async function changeStatus(ticketNo: string, status: string) {
    setActionLoading(true);
    setError("");

    try {
      const response = await fetch(`/api/v1/tickets/${encodeURIComponent(ticketNo)}/status`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          status,
          note: `前端工单中心更新状态为 ${status}`,
        }),
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(`更新状态失败：HTTP ${response.status} ${text}`);
      }

      const data = (await response.json()) as TicketActionResponse;
      setSelectedTicket(data.ticket);
      setMessage(data.message);
      await loadTickets();
    } catch (err) {
      setError(err instanceof Error ? err.message : "未知错误");
    } finally {
      setActionLoading(false);
    }
  }

  async function escalateTicket(ticketNo: string) {
    setActionLoading(true);
    setError("");
    setMessage("");

    try {
      const response = await fetch(`/api/v1/tickets/${encodeURIComponent(ticketNo)}/escalate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          reason: "用户问题风险较高或处理复杂，前端工单中心触发升级。",
        }),
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(`升级工单失败：HTTP ${response.status} ${text}`);
      }

      const data = (await response.json()) as TicketActionResponse;
      setSelectedTicket(data.ticket);
      setMessage(data.message);
      await loadTickets();
    } catch (err) {
      setError(err instanceof Error ? err.message : "未知错误");
    } finally {
      setActionLoading(false);
    }
  }

  useEffect(() => {
    loadTickets();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <>
      {error && <div className="error-box">{error}</div>}
      {message && <div className="success-box">{message}</div>}
      <section className="analytics-metrics">
        <div className="metric-card">
          <span>工单总数</span>
          <strong>{total}</strong>
        </div>
        <div className="metric-card">
          <span>待处理</span>
          <strong>{tickets.filter((item) => item.status === "open").length}</strong>
        </div>
        <div className="metric-card">
          <span>处理中</span>
          <strong>{tickets.filter((item) => item.status === "processing").length}</strong>
        </div>
        <div className="metric-card">
          <span>高优先级</span>
          <strong>{tickets.filter((item) => item.priority === "high").length}</strong>
        </div>
        <div className="metric-card">
          <span>已解决</span>
          <strong>{tickets.filter((item) => item.status === "resolved").length}</strong>
        </div>
        <div className="metric-card">
          <span>已关闭</span>
          <strong>{tickets.filter((item) => item.status === "closed").length}</strong>
        </div>
      </section>

      <section className="ticket-layout">
        <div className="panel">
          <div className="panel-header">
            <div>
              <h2>工单列表</h2>
              <p>共 {total} 条，支持按状态和优先级筛选。</p>
            </div>
          </div>

          <div className="filter-row">
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
              <option value="">全部状态</option>
              <option value="open">open</option>
              <option value="processing">processing</option>
              <option value="resolved">resolved</option>
              <option value="closed">closed</option>
            </select>

            <select value={priorityFilter} onChange={(event) => setPriorityFilter(event.target.value)}>
              <option value="">全部优先级</option>
              <option value="high">high</option>
              <option value="medium">medium</option>
              <option value="low">low</option>
              <option value="normal">normal</option>
            </select>
            <select value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}>
              <option value="">全部类型</option>
              <option value="logistics_delay_refund">logistics_delay_refund</option>
              <option value="logistics_delay">logistics_delay</option>
              <option value="logistics_exception">logistics_exception</option>
              <option value="refund_progress">refund_progress</option>
              <option value="product_quality">product_quality</option>
              <option value="product_damage">product_damage</option>
              <option value="campaign_compensation">campaign_compensation</option>
              <option value="invoice">invoice</option>
              <option value="service_complaint">service_complaint</option>
              <option value="general_aftersale">general_aftersale</option>
            </select>

            <button onClick={loadTickets} disabled={loading}>
              {loading ? "加载中..." : "刷新列表"}
            </button>
          </div>

          <div className="ticket-list">
            {tickets.map((ticket) => (
              <button
                key={ticket.id}
                className={`ticket-list-item ${selectedTicket?.ticket_no === ticket.ticket_no ? "active" : ""}`}
                onClick={() => {
                  setError("");
                  setSelectedTicket(ticket);
                }}
              >
                <div className="ticket-list-head">
                  <strong>{ticket.ticket_no}</strong>
                  <StatusPill value={ticket.status} />
                </div>
                <div className="ticket-title">{ticket.title}</div>
                <div className="ticket-meta-line">
                  <span>{ticket.category}</span>
                  <StatusPill value={ticket.priority} />
                  <span>{formatDate(ticket.created_at)}</span>
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <div>
              <h2>AI 自动创建工单</h2>
              <p>输入订单号和用户问题，系统自动分类、定优先级、生成标题摘要。</p>
            </div>
          </div>

          <div className="create-ticket-form">
            <input
              value={createOrderNo}
              onChange={(event) => setCreateOrderNo(event.target.value)}
              placeholder="订单号，可为空，例如 ORDER-20260515-0002"
            />
            <textarea
              value={createQuestion}
              onChange={(event) => setCreateQuestion(event.target.value)}
              placeholder="用户原始问题"
            />
            <button onClick={createTicket} disabled={actionLoading || createQuestion.trim().length < 2}>
              {actionLoading ? "处理中..." : "AI 创建工单"}
            </button>
          </div>

          {createResult && (
            <div className="create-result">
              <div className="card-title">创建结果</div>
              <div className="ticket-list-head">
                <strong>{createResult.ticket.ticket_no}</strong>
                <StatusPill value={createResult.ticket.priority} />
              </div>
              <p>{createResult.classification_reason}</p>
              <p>{createResult.next_action}</p>
              <div className="meta-row">
                <span>LLM：{createResult.llm_provider ?? "-"} / {createResult.llm_model ?? "-"}</span>
                <span>used_llm：{String(createResult.used_llm)}</span>
                <span>{createResult.classification_source ?? "-"}</span>
              </div>
            </div>
          )}
        </div>
      </section>

      {selectedTicket && (
        <section className="panel ticket-detail-panel">
          <div className="panel-header">
            <div>
              <h2>工单详情</h2>
              <p>{selectedTicket.ticket_no}</p>
            </div>

            <div className="ticket-actions">
              <button
                disabled={actionLoading || selectedTicket.status === "processing" || selectedTicket.status === "closed"}
                onClick={() => changeStatus(selectedTicket.ticket_no, "processing")}
                title={selectedTicket.status === "closed" ? "已关闭工单不能重新转处理中" : ""}
              >
                转处理中
              </button>
              <button
                disabled={actionLoading || selectedTicket.status !== "processing"}
                onClick={() => changeStatus(selectedTicket.ticket_no, "open")}
                title={selectedTicket.status !== "processing" ? "只有 processing 状态可以退回 open" : ""}
              >
                退回待处理
              </button>
              <button
                disabled={actionLoading || selectedTicket.status === "resolved" || selectedTicket.status === "closed"}
                onClick={() => changeStatus(selectedTicket.ticket_no, "resolved")}
                title={selectedTicket.status === "closed" ? "已关闭工单不能标记解决" : ""}
              >
                标记已解决
              </button>
              <button
                disabled={actionLoading || selectedTicket.status === "closed"}
                onClick={() => changeStatus(selectedTicket.ticket_no, "closed")}
                title={selectedTicket.status === "closed" ? "工单已经关闭" : ""}
              >
                关闭
              </button>
              <button
                disabled={actionLoading || selectedTicket.status === "closed"}
                onClick={() => escalateTicket(selectedTicket.ticket_no)}
                title={selectedTicket.status === "closed" ? "已关闭工单不能升级" : ""}
              >
                升级
              </button>
            </div>
          </div>
          <div className="ticket-flow">
            {ticketStatusSteps.map((step, index) => (
              <div
                key={step.key}
                className={`ticket-flow-step ${
                  selectedTicket.status === step.key ? "active" : ""
                } ${
                  ticketStatusSteps.findIndex((item) => item.key === selectedTicket.status) > index
                    ? "done"
                    : ""
                }`}
              >
                <span>{index + 1}</span>
                <strong>{step.label}</strong>
                <small>{step.key}</small>
              </div>
            ))}
          </div>

          <div className="ticket-detail-grid">
            <div>
              <span>标题</span>
              <strong>{selectedTicket.title}</strong>
            </div>
            <div>
              <span>类型</span>
              <strong>{selectedTicket.category}</strong>
            </div>
            <div>
              <span>优先级</span>
              <StatusPill value={selectedTicket.priority} />
            </div>
            <div>
              <span>状态</span>
              <StatusPill value={selectedTicket.status} />
            </div>
            <div>
              <span>订单ID</span>
              <strong>{selectedTicket.order_id ?? "-"}</strong>
            </div>
            <div>
              <span>处理人</span>
              <strong>{selectedTicket.assignee_id ?? "-"}</strong>
            </div>
            <div>
              <span>创建时间</span>
              <strong>{formatDate(selectedTicket.created_at)}</strong>
            </div>
            <div>
              <span>更新时间</span>
              <strong>{formatDate(selectedTicket.updated_at)}</strong>
            </div>
          </div>

          <div className="summary-box">
            <div className="summary-title">用户问题</div>
            <p>{selectedTicket.customer_question}</p>
          </div>

          <div className="summary-box">
            <div className="summary-title">工单摘要</div>
            <p>{selectedTicket.summary}</p>
          </div>
        </section>
      )}
    </>
  );
}
