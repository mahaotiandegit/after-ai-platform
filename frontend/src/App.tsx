import { useState } from "react";
import "./App.css";

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

const defaultQuestion = "物流延迟应该怎么补偿？";

function App() {
  const [question, setQuestion] = useState(defaultQuestion);
  const [loading, setLoading] = useState(false);
  const [healthLoading, setHealthLoading] = useState(false);
  const [result, setResult] = useState<KnowledgeAskResponse | null>(null);
  const [health, setHealth] = useState<SystemHealthResponse | null>(null);
  const [error, setError] = useState("");

  async function askKnowledge() {
    setLoading(true);
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
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "未知错误");
    } finally {
      setLoading(false);
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
          <div className="menu-item active">知识检索</div>
          <div className="menu-item">订单处理</div>
          <div className="menu-item">工单中心</div>
          <div className="menu-item">数据分析</div>
          <div className="menu-item">文档管理</div>
          <div className="menu-item">Bad Case</div>
          <div className="menu-item">系统监控</div>
        </nav>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <h1>知识检索</h1>
            <p>面向客服场景的售后规则、补偿标准、SOP 检索与引用返回。</p>
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
            <button onClick={askKnowledge} disabled={loading || !question.trim()}>
              {loading ? "查询中..." : "开始查询"}
            </button>
          </div>

          {error && <div className="error-box">{error}</div>}
        </section>

        {result && (
          <section className="result-grid">
            <div className="answer-card">
              <div className="card-title">AI 处理建议</div>
              <h3>{result.question}</h3>
              <p className="answer-text">{result.answer}</p>

              {result.answer_summary && (
                <div className="summary-box">
                  <div className="summary-title">摘要</div>
                  <p>{result.answer_summary}</p>
                </div>
              )}

              <div className="meta-row">
                <span>检索 query：{result.query}</span>
                <span>QA Log：{result.qa_log_id ?? "-"}</span>
              </div>
            </div>

            <div className="citation-card">
              <div className="card-title">引用来源</div>

              {result.citations.length === 0 && (
                <div className="empty">暂无引用来源</div>
              )}

              {result.citations.map((item) => (
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
      </main>
    </div>
  );
}

export default App;
