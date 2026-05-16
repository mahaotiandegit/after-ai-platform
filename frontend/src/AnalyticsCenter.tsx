import { useEffect, useState } from "react";

type DistributionItem = {
  label: string;
  count: number;
};

type AnalyticsOverview = {
  orders_total: number;
  tickets_total: number;
  tickets_open: number;
  tickets_high_priority: number;
  refunds_pending: number;
  documents_indexed: number;
  avg_qa_latency_ms: number;
  ticket_status_distribution: DistributionItem[];
  ticket_category_distribution: DistributionItem[];
  refund_status_distribution: DistributionItem[];
};

type AnalyticsAskResponse = {
  question: string;
  intent: string;
  sql: string;
  columns: string[];
  rows: Record<string, string | number | boolean | null>[];
  summary: string;
};

const examples = [
  "最近 7 天工单按类型分布",
  "最近 7 天高优先级工单有多少",
  "最近 7 天工单按状态统计",
  "最近 7 天退款状态分布",
  "最近 30 天物流相关工单有多少",
];

function MiniBar({ item, max }: { item: DistributionItem; max: number }) {
  const width = max > 0 ? Math.max(8, Math.round((item.count / max) * 100)) : 0;

  return (
    <div className="mini-bar-row">
      <div className="mini-bar-label">{item.label}</div>
      <div className="mini-bar-track">
        <div className="mini-bar-fill" style={{ width: `${width}%` }} />
      </div>
      <div className="mini-bar-value">{item.count}</div>
    </div>
  );
}

function DistributionCard({ title, items }: { title: string; items: DistributionItem[] }) {
  const max = Math.max(0, ...items.map((item) => item.count));

  return (
    <div className="analytics-card">
      <div className="card-title">{title}</div>
      <div className="mini-bar-list">
        {items.length === 0 && <div className="empty">暂无数据</div>}
        {items.map((item) => (
          <MiniBar key={item.label} item={item} max={max} />
        ))}
      </div>
    </div>
  );
}

export default function AnalyticsCenter() {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [question, setQuestion] = useState("最近 7 天工单按类型分布");
  const [askResult, setAskResult] = useState<AnalyticsAskResponse | null>(null);
  const [loadingOverview, setLoadingOverview] = useState(false);
  const [loadingAsk, setLoadingAsk] = useState(false);
  const [error, setError] = useState("");

  async function loadOverview() {
    setLoadingOverview(true);
    setError("");

    try {
      const response = await fetch("/api/v1/analytics/overview");

      if (!response.ok) {
        const text = await response.text();
        throw new Error(`加载分析概览失败：HTTP ${response.status} ${text}`);
      }

      const data = (await response.json()) as AnalyticsOverview;
      setOverview(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "未知错误");
    } finally {
      setLoadingOverview(false);
    }
  }

  async function askAnalytics(nextQuestion?: string) {
    const finalQuestion = (nextQuestion ?? question).trim();
    if (!finalQuestion) return;

    setQuestion(finalQuestion);
    setLoadingAsk(true);
    setError("");

    try {
      const response = await fetch("/api/v1/analytics/ask", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: finalQuestion,
          limit: 20,
        }),
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(`问数失败：HTTP ${response.status} ${text}`);
      }

      const data = (await response.json()) as AnalyticsAskResponse;
      setAskResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "未知错误");
    } finally {
      setLoadingAsk(false);
    }
  }

  useEffect(() => {
    loadOverview();
  }, []);

  return (
    <>
      {error && <div className="error-box">{error}</div>}

      <section className="analytics-metrics">
        <div className="metric-card">
          <span>订单总数</span>
          <strong>{overview?.orders_total ?? "-"}</strong>
        </div>
        <div className="metric-card">
          <span>工单总数</span>
          <strong>{overview?.tickets_total ?? "-"}</strong>
        </div>
        <div className="metric-card">
          <span>未关闭工单</span>
          <strong>{overview?.tickets_open ?? "-"}</strong>
        </div>
        <div className="metric-card">
          <span>高优先级工单</span>
          <strong>{overview?.tickets_high_priority ?? "-"}</strong>
        </div>
        <div className="metric-card">
          <span>待处理退款</span>
          <strong>{overview?.refunds_pending ?? "-"}</strong>
        </div>
        <div className="metric-card">
          <span>平均 QA 延迟</span>
          <strong>{overview ? `${overview.avg_qa_latency_ms} ms` : "-"}</strong>
        </div>
      </section>

      <section className="analytics-grid">
        <DistributionCard
          title="工单状态分布"
          items={overview?.ticket_status_distribution ?? []}
        />
        <DistributionCard
          title="工单类型分布"
          items={overview?.ticket_category_distribution ?? []}
        />
        <DistributionCard
          title="退款状态分布"
          items={overview?.refund_status_distribution ?? []}
        />
      </section>

      <section className="panel analytics-ask-panel">
        <div className="panel-header">
          <div>
            <h2>自然语言问数</h2>
            <p>当前采用白名单 NL2SQL：识别问题意图后执行安全 SELECT 查询。</p>
          </div>
          <button className="secondary-button" onClick={loadOverview} disabled={loadingOverview}>
            {loadingOverview ? "刷新中..." : "刷新概览"}
          </button>
        </div>

        <div className="example-question-row">
          {examples.map((item) => (
            <button key={item} onClick={() => askAnalytics(item)} disabled={loadingAsk}>
              {item}
            </button>
          ))}
        </div>

        <div className="analytics-query-box">
          <input
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="例如：最近 7 天工单按类型分布"
          />
          <button onClick={() => askAnalytics()} disabled={loadingAsk || !question.trim()}>
            {loadingAsk ? "分析中..." : "开始分析"}
          </button>
        </div>
      </section>

      {askResult && (
        <section className="analytics-result-grid">
          <div className="answer-card">
            <div className="card-title">分析摘要</div>
            <h3>{askResult.question}</h3>
            <p className="answer-text">{askResult.summary}</p>

            <div className="summary-box">
              <div className="summary-title">识别意图</div>
              <p>{askResult.intent}</p>
            </div>

            <div className="summary-box">
              <div className="summary-title">执行 SQL</div>
              <pre className="sql-block">{askResult.sql}</pre>
            </div>
          </div>

          <div className="citation-card">
            <div className="card-title">查询结果</div>

            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    {askResult.columns.map((column) => (
                      <th key={column}>{column}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {askResult.rows.length === 0 && (
                    <tr>
                      <td colSpan={Math.max(1, askResult.columns.length)}>暂无数据</td>
                    </tr>
                  )}

                  {askResult.rows.map((row, index) => (
                    <tr key={index}>
                      {askResult.columns.map((column) => (
                        <td key={column}>{String(row[column] ?? "-")}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}
    </>
  );
}
