import { useState } from "react";
import "./App.css";
import TicketCenter from "./TicketCenter";
import AnalyticsCenter from "./AnalyticsCenter";
import { DocumentCenter, BadCaseCenter, MonitorCenter, AftersaleAgentCenter } from "./OpsPages";
type PageKey =
  | "knowledge"
  | "order"
  | "ticket"
  | "analytics"
  | "documents"
  | "agent"
  | "badcase"
  | "monitor";
type Citation = {
  chunk_id: string;
  document_id: string;
  document_title: string;
  file_name: string;
  file_type: string;
  content: string;
  page_no?: number;
  policy_code?: string;
  section?: string;
  score?: number;
};

type KnowledgeAskResponse = {
  question: string;
  query: string;
  answer: string;
  answer_summary?: string;
  citations: Citation[];
  hits?: Citation[];
  qa_log_id?: string;
};

type SystemHealthResponse = {
  status: string;
  services?: {
    database?: {
      status: string;
      detail: string;
    };
    redis?: {
      status: string;
      detail: string;
    };
  };
};

type OrderInfo = {
  id: string;
  order_no: string;
  customer_name: string;
  customer_phone: string;
  status: string;
  total_amount_cents: number;
  total_amount_yuan: number;
  created_at: string;
  updated_at: string;
};

type LogisticsInfo = {
  id: string;
  carrier: string;
  tracking_no: string;
  status: string;
  latest_event: string;
  shipped_at?: string | null;
  delivered_at?: string | null;
  created_at: string;
};

type RefundInfo = {
  id: string;
  refund_no: string;
  reason: string;
  amount_cents: number;
  amount_yuan: number;
  status: string;
  created_at: string;
  updated_at: string;
};

type TicketInfo = {
  id: string;
  ticket_no: string;
  customer_question: string;
  category: string;
  priority: string;
  title: string;
  summary: string;
  status: string;
  created_at: string;
  updated_at: string;
};

type OrderRecommendation = {
  issue_type: string;
  priority: string;
  suggested_action: string;
  risk_flags: string[];
  can_create_ticket: boolean;
  next_steps: string[];
};

type OrderWorkbenchResponse = {
  order_no: string;
  order: OrderInfo;
  logistics: LogisticsInfo[];
  refunds: RefundInfo[];
  tickets: TicketInfo[];
  recommendation: OrderRecommendation;
};

const defaultQuestion = "物流延迟应该怎么补偿？";
const defaultOrderNo = "ORDER-20260515-0001";

function formatDate(value?: string | null) {
  if (!value) return "-";
  return value.replace("T", " ").slice(0, 19);
}

function StatusPill({ value }: { value: string }) {
  return <span className={`status-pill status-${value}`}>{value}</span>;
}

function App() {
  const [activePage, setActivePage] = useState<PageKey>("knowledge");

  const [question, setQuestion] = useState(defaultQuestion);
  const [knowledgeLoading, setKnowledgeLoading] = useState(false);
  const [knowledgeResult, setKnowledgeResult] = useState<KnowledgeAskResponse | null>(null);

  const [orderNo, setOrderNo] = useState(defaultOrderNo);
  const [orderLoading, setOrderLoading] = useState(false);
  const [orderResult, setOrderResult] = useState<OrderWorkbenchResponse | null>(null);

  const [healthLoading, setHealthLoading] = useState(false);
  const [health, setHealth] = useState<SystemHealthResponse | null>(null);
  const [error, setError] = useState("");

  async function askKnowledge() {
    setKnowledgeLoading(true);
    setError("");

    try {
      const response = await fetch("/api/v1/knowledge/ask", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question,
          top_k: 5,
        }),
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(`知识检索失败：HTTP ${response.status} ${text}`);
      }

      const data = (await response.json()) as KnowledgeAskResponse;
      setKnowledgeResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "未知错误");
    } finally {
      setKnowledgeLoading(false);
    }
  }

  async function queryOrderWorkbench() {
    setOrderLoading(true);
    setError("");

    try {
      const cleanOrderNo = orderNo.trim();
      const response = await fetch(`/api/v1/order-workbench/${encodeURIComponent(cleanOrderNo)}`);

      if (!response.ok) {
        const text = await response.text();
        throw new Error(`订单查询失败：HTTP ${response.status} ${text}`);
      }

      const data = (await response.json()) as OrderWorkbenchResponse;
      setOrderResult(data);
    } catch (err) {
      setOrderResult(null);
      setError(err instanceof Error ? err.message : "未知错误");
    } finally {
      setOrderLoading(false);
    }
  }

  async function checkHealth() {
    setHealthLoading(true);
    setError("");

    try {
      const response = await fetch("/api/v1/system/health");

      if (!response.ok) {
        const text = await response.text();
        throw new Error(`系统健康检查失败：HTTP ${response.status} ${text}`);
      }

      const data = (await response.json()) as SystemHealthResponse;
      setHealth(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "未知错误");
    } finally {
      setHealthLoading(false);
    }
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">AI</div>
          <div>
            <div className="brand-title">After-AI Platform</div>
            <div className="brand-subtitle">电商售后知识与工单自动化平台</div>
          </div>
        </div>

        <nav className="menu">
          <button
            className={`menu-item ${activePage === "knowledge" ? "active" : ""}`}
            onClick={() => setActivePage("knowledge")}
          >
            知识检索
          </button>
          <button
            className={`menu-item ${activePage === "order" ? "active" : ""}`}
            onClick={() => setActivePage("order")}
          >
            订单处理
          </button>
          <button
            className={`menu-item ${activePage === "ticket" ? "active" : ""}`}
            onClick={() => setActivePage("ticket")}
          >
            工单中心
          </button>
          <button
            className={`menu-item ${activePage === "analytics" ? "active" : ""}`}
            onClick={() => setActivePage("analytics")}
          >
            数据分析
          </button>
          <button
            className={`menu-item ${activePage === "documents" ? "active" : ""}`}
            onClick={() => setActivePage("documents")}
          >
            文档管理
          </button>
          <button
  className={`menu-item ${activePage === "agent" ? "active" : ""}`}
  onClick={() => setActivePage("agent")}
>
  售后 Agent
</button>
          <button
            className={`menu-item ${activePage === "badcase" ? "active" : ""}`}
            onClick={() => setActivePage("badcase")}
          >
            Bad Case
          </button>
          <button
            className={`menu-item ${activePage === "monitor" ? "active" : ""}`}
            onClick={() => setActivePage("monitor")}
          >
            系统监控
          </button>
        </nav>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
<h1>
  {activePage === "knowledge"
    ? "知识检索"
    : activePage === "order"
    ? "订单处理台"
    : activePage === "ticket"
    ? "工单中心"
    : activePage === "analytics"
    ? "数据分析"
    : activePage === "documents"
    ? "文档管理"
    : activePage === "agent"
    ? "售后 Agent"
    : activePage === "badcase"
    ? "Bad Case"
    : "系统监控"}
</h1>            <p>
              {activePage === "knowledge"
                ? "面向客服场景的售后规则、补偿标准、SOP 检索与引用返回。"
                : activePage === "order"
                ? "输入订单号，聚合订单、物流、退款、历史工单，并生成推荐处理方案。"
                : activePage === "ticket"
                ? "自动创建、分派、升级和流转售后工单。"
                : activePage === "analytics"
                ? "面向客服组长和运营的售后趋势分析与自然语言问数。"
                : activePage === "documents"
? "维护售后规则、SOP、活动政策等知识库文档。"
: activePage === "agent"
? "把知识检索、订单查询、工单创建和运营问数串成一个售后处理工作流。"
: activePage === "badcase"
? "复盘 AI 误判、低质量回答和人工反馈样本。"
: "查看系统健康、核心表数量和 AI 调用日志。"}
            </p>
          </div>
          <button className="secondary-button" onClick={checkHealth} disabled={healthLoading}>
            {healthLoading ? "检查中..." : "系统健康检查"}
          </button>
        </header>

        {health && (
          <section className="health-card">
            <div className="health-item">
              <span>系统状态</span>
              <strong>{health.status}</strong>
            </div>
            <div className="health-item">
              <span>PostgreSQL</span>
              <strong>{health.services?.database?.status ?? "-"}</strong>
              <small>{health.services?.database?.detail ?? ""}</small>
            </div>
            <div className="health-item">
              <span>Redis</span>
              <strong>{health.services?.redis?.status ?? "-"}</strong>
              <small>{health.services?.redis?.detail ?? ""}</small>
            </div>
          </section>
        )}

        {error && <div className="error-box">{error}</div>}

        {activePage === "knowledge" && (
          <>
            <section className="panel">
              <div className="panel-header">
                <div>
                  <h2>售后问题查询</h2>
                  <p>输入客服问题，系统返回处理建议和引用依据。</p>
                </div>
              </div>

              <div className="query-box">
                <textarea
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  placeholder="例如：物流延迟应该怎么补偿？"
                />
                <button onClick={askKnowledge} disabled={knowledgeLoading || !question.trim()}>
                  {knowledgeLoading ? "查询中..." : "开始查询"}
                </button>
              </div>
            </section>

            {knowledgeResult && (
              <section className="result-grid">
                <div className="answer-card">
                  <div className="card-title">AI 处理建议</div>
                  <h3>{knowledgeResult.question}</h3>
                  <p className="answer-text">{knowledgeResult.answer}</p>

                  {knowledgeResult.answer_summary && (
                    <div className="summary-box">
                      <div className="summary-title">摘要</div>
                      <p>{knowledgeResult.answer_summary}</p>
                    </div>
                  )}

                  <div className="meta-row">
                    <span>检索 query：{knowledgeResult.query}</span>
                    <span>QA Log：{knowledgeResult.qa_log_id ?? "-"}</span>
                  </div>
                </div>

                <div className="citation-card">
                  <div className="card-title">引用来源</div>

                  {knowledgeResult.citations.length === 0 && (
                    <div className="empty">暂无引用来源</div>
                  )}

                  {knowledgeResult.citations.map((item) => (
                    <article className="citation-item" key={item.chunk_id}>
                      <div className="citation-head">
                        <strong>{item.document_title}</strong>
                        <span>{item.file_type}</span>
                      </div>

                      <div className="citation-meta">
                        <span>文件：{item.file_name}</span>
                        <span>章节：{item.section ?? "-"}</span>
                        <span>页码：{item.page_no ?? "-"}</span>
                        <span>规则编号：{item.policy_code ?? "-"}</span>
                        <span>分数：{item.score ?? "-"}</span>
                      </div>

                      <p>{item.content}</p>
                    </article>
                  ))}
                </div>
              </section>
            )}
          </>
        )}

        {activePage === "order" && (
          <>
            <section className="panel">
              <div className="panel-header">
                <div>
                  <h2>订单售后处理台</h2>
                  <p>聚合订单上下文，减少客服在多个系统之间切换。</p>
                </div>
              </div>

              <div className="order-query-row">
                <input
                  value={orderNo}
                  onChange={(event) => setOrderNo(event.target.value)}
                  placeholder="例如：ORDER-20260515-0001"
                />
                <button onClick={queryOrderWorkbench} disabled={orderLoading || !orderNo.trim()}>
                  {orderLoading ? "查询中..." : "查询订单"}
                </button>
              </div>
            </section>

            {orderResult && (
              <>
                <section className="order-overview-grid">
                  <div className="metric-card">
                    <span>订单号</span>
                    <strong>{orderResult.order.order_no}</strong>
                  </div>
                  <div className="metric-card">
                    <span>客户</span>
                    <strong>{orderResult.order.customer_name}</strong>
                    <small>{orderResult.order.customer_phone}</small>
                  </div>
                  <div className="metric-card">
                    <span>订单状态</span>
                    <strong>{orderResult.order.status}</strong>
                  </div>
                  <div className="metric-card">
                    <span>订单金额</span>
                    <strong>¥{orderResult.order.total_amount_yuan}</strong>
                  </div>
                </section>

                <section className="result-grid order-grid">
                  <div className="answer-card">
                    <div className="card-title">推荐处理方案</div>

                    <div className="recommendation-head">
                      <div>
                        <span>问题类型</span>
                        <strong>{orderResult.recommendation.issue_type}</strong>
                      </div>
                      <div>
                        <span>优先级</span>
                        <strong>{orderResult.recommendation.priority}</strong>
                      </div>
                      <div>
                        <span>是否建议新建工单</span>
                        <strong>
                          {orderResult.recommendation.can_create_ticket ? "可以创建" : "不建议重复创建"}
                        </strong>
                      </div>
                    </div>

                    <p className="answer-text">{orderResult.recommendation.suggested_action}</p>

                    <div className="risk-tags">
                      {orderResult.recommendation.risk_flags.length === 0 && <span>暂无风险标签</span>}
                      {orderResult.recommendation.risk_flags.map((flag) => (
                        <span key={flag}>{flag}</span>
                      ))}
                    </div>

                    <div className="summary-box">
                      <div className="summary-title">下一步动作</div>
                      <ol className="step-list">
                        {orderResult.recommendation.next_steps.map((step) => (
                          <li key={step}>{step}</li>
                        ))}
                      </ol>
                    </div>
                  </div>

                  <div className="citation-card">
                    <div className="card-title">物流与退款</div>

                    <div className="section-title">物流信息</div>
                    {orderResult.logistics.length === 0 && <div className="empty">暂无物流记录</div>}
                    {orderResult.logistics.map((item) => (
                      <article className="record-item" key={item.id}>
                        <div className="record-head">
                          <strong>{item.carrier}</strong>
                          <StatusPill value={item.status} />
                        </div>
                        <div className="citation-meta">
                          <span>运单号：{item.tracking_no}</span>
                          <span>创建时间：{formatDate(item.created_at)}</span>
                        </div>
                        <p>{item.latest_event}</p>
                      </article>
                    ))}

                    <div className="section-title with-margin">退款记录</div>
                    {orderResult.refunds.length === 0 && <div className="empty">暂无退款记录</div>}
                    {orderResult.refunds.map((item) => (
                      <article className="record-item" key={item.id}>
                        <div className="record-head">
                          <strong>{item.refund_no}</strong>
                          <StatusPill value={item.status} />
                        </div>
                        <div className="citation-meta">
                          <span>金额：¥{item.amount_yuan}</span>
                          <span>更新时间：{formatDate(item.updated_at)}</span>
                        </div>
                        <p>{item.reason}</p>
                      </article>
                    ))}
                  </div>
                </section>

                <section className="panel table-panel">
                  <div className="panel-header">
                    <div>
                      <h2>历史工单</h2>
                      <p>用于判断是否重复建单、是否需要继续原工单处理。</p>
                    </div>
                  </div>

                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>工单号</th>
                          <th>标题</th>
                          <th>类型</th>
                          <th>优先级</th>
                          <th>状态</th>
                          <th>摘要</th>
                        </tr>
                      </thead>
                      <tbody>
                        {orderResult.tickets.length === 0 && (
                          <tr>
                            <td colSpan={6}>暂无历史工单</td>
                          </tr>
                        )}

                        {orderResult.tickets.map((ticket) => (
                          <tr key={ticket.id}>
                            <td>{ticket.ticket_no}</td>
                            <td>{ticket.title}</td>
                            <td>{ticket.category}</td>
                            <td><StatusPill value={ticket.priority} /></td>
                            <td><StatusPill value={ticket.status} /></td>
                            <td>{ticket.summary}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              </>
            )}
          </>
        )}
        {activePage === "ticket" && <TicketCenter />}
        {activePage === "analytics" && <AnalyticsCenter />}
        {activePage === "documents" && <DocumentCenter />}
        {activePage === "agent" && <AftersaleAgentCenter />}
        {activePage === "badcase" && <BadCaseCenter />}
        {activePage === "monitor" && <MonitorCenter />}
      </main>
    </div>
  );
}

export default App;
