import { useEffect, useRef, useState } from "react";

type GenericRow = Record<string, string | number | boolean | null | object>;

type ListResponse = {
  total: number;
  items: GenericRow[];
};

type MonitorResponse = {
  status: string;
  table_counts: GenericRow[];
  recent_qa_logs: GenericRow[];
  recent_ai_invocations: GenericRow[];
};

function valueText(value: unknown) {
  if (value === null || value === undefined) return "-";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function GenericTable({ rows, maxColumns = 8 }: { rows: GenericRow[]; maxColumns?: number }) {
  const columns = rows.length > 0 ? Object.keys(rows[0]).slice(0, maxColumns) : [];

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr>
              <td colSpan={Math.max(1, columns.length)}>暂无数据</td>
            </tr>
          )}

          {rows.map((row, index) => (
            <tr key={index}>
              {columns.map((column) => (
                <td key={column}>{valueText(row[column])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function DocumentCenter() {
  const [data, setData] = useState<ListResponse | null>(null);
  const [chunkData, setChunkData] = useState<ListResponse | null>(null);
  const [selectedDocument, setSelectedDocument] = useState<GenericRow | null>(null);
  const [error, setError] = useState("");
  const [uploadMessage, setUploadMessage] = useState("");
  const [uploading, setUploading] = useState(false);
  const [loadingChunks, setLoadingChunks] = useState(false);
  const [uploadTitle, setUploadTitle] = useState("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  async function loadData() {
    setError("");

    try {
      const response = await fetch("/api/v1/ops/documents?limit=50");
      if (!response.ok) {
        const text = await response.text();
        throw new Error(`加载文档失败：HTTP ${response.status} ${text}`);
      }
      setData((await response.json()) as ListResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "未知错误");
    }
  }

  async function loadChunks(document: GenericRow) {
    const documentId = String(document.id ?? "");

    if (!documentId) {
      setError("文档 ID 为空，无法查看切块。");
      return;
    }

    setError("");
    setLoadingChunks(true);
    setSelectedDocument(document);

    try {
      const response = await fetch(`/api/v1/ops/documents/${documentId}/chunks`);
      if (!response.ok) {
        const text = await response.text();
        throw new Error(`加载切块失败：HTTP ${response.status} ${text}`);
      }

      setChunkData((await response.json()) as ListResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "未知错误");
    } finally {
      setLoadingChunks(false);
    }
  }

  async function uploadDocument() {
    setError("");
    setUploadMessage("");

    if (!uploadFile) {
      setError("请先选择要上传的文档。");
      return;
    }

    const formData = new FormData();
    formData.append("file", uploadFile);

    if (uploadTitle.trim()) {
      formData.append("title", uploadTitle.trim());
    }

    setUploading(true);

    try {
      const response = await fetch("/api/v1/documents/upload", {
        method: "POST",
        body: formData,
      });

      const responseText = await response.text();
      let result: any = null;

      try {
        result = responseText ? JSON.parse(responseText) : null;
      } catch {
        result = responseText;
      }

      if (!response.ok) {
        const detail =
          typeof result === "object" && result !== null && "detail" in result
            ? String(result.detail)
            : String(responseText || "未知错误");

        throw new Error(`上传失败：HTTP ${response.status} ${detail}`);
      }

      setUploadMessage(
        `上传成功：${result?.title ?? uploadFile.name}，已生成 ${result?.chunk_count ?? "-"} 个切块。`
      );

      setUploadTitle("");
      setUploadFile(null);
      setChunkData(null);
      setSelectedDocument(null);

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }

      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "未知错误");
    } finally {
      setUploading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  const documents = data?.items ?? [];
  const chunks = chunkData?.items ?? [];

  return (
    <>
      {error && <div className="error-box">{error}</div>}
      {uploadMessage && <div className="success-box">{uploadMessage}</div>}

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>文档上传</h2>
            <p>上传售后规则、SOP、活动政策等知识库文档。当前支持 txt / md / csv / json / log / pdf / docx / xlsx。</p>
          </div>
        </div>

        <div className="query-box">
          <input
            value={uploadTitle}
            onChange={(event) => setUploadTitle(event.target.value)}
            placeholder="文档标题，可不填；不填时默认使用文件名"
          />

          <input
            ref={fileInputRef}
            type="file"
            accept=".txt,.md,.markdown,.csv,.json,.log,.pdf,.docx,.xlsx"
            onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)}
          />

          <button onClick={uploadDocument} disabled={uploading || !uploadFile}>
            {uploading ? "上传解析中..." : "上传并解析"}
          </button>
        </div>

        <p className="hint-text">
          上传成功后，系统会写入 documents 表，自动解析文本，切块写入 document_chunks 表，并进入知识检索。
        </p>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>文档管理</h2>
            <p>展示已入库文档、文件类型、索引状态和切块数量，可查看解析后的切块内容。</p>
          </div>
          <button className="secondary-button" onClick={loadData}>刷新</button>
        </div>

        <section className="analytics-metrics doc-metrics">
          <div className="metric-card">
            <span>文档总数</span>
            <strong>{data?.total ?? "-"}</strong>
          </div>
          <div className="metric-card">
            <span>已索引文档</span>
            <strong>{documents.filter((item) => item.status === "indexed").length}</strong>
          </div>
          <div className="metric-card">
            <span>总切块数</span>
            <strong>{documents.reduce((sum, item) => sum + Number(item.chunk_count ?? 0), 0)}</strong>
          </div>
        </section>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>title</th>
                <th>file_name</th>
                <th>file_type</th>
                <th>status</th>
                <th>chunk_count</th>
                <th>created_at</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {documents.length === 0 && (
                <tr>
                  <td colSpan={7}>暂无数据</td>
                </tr>
              )}

              {documents.map((item) => (
                <tr key={String(item.id)}>
                  <td>{valueText(item.title)}</td>
                  <td>{valueText(item.file_name)}</td>
                  <td>{valueText(item.file_type)}</td>
                  <td>{valueText(item.status)}</td>
                  <td>{valueText(item.chunk_count)}</td>
                  <td>{valueText(item.created_at)}</td>
                  <td>
                    <button className="secondary-button" onClick={() => loadChunks(item)}>
                      查看切块
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>切块预览</h2>
            <p>
              {selectedDocument
                ? `当前文档：${valueText(selectedDocument.title)}，共 ${chunkData?.total ?? "-"} 个切块。`
                : "选择一篇文档后，可以查看系统解析入库的 document_chunks 内容。"}
            </p>
          </div>
        </div>

        {loadingChunks && <p className="hint-text">正在加载切块...</p>}

        {!loadingChunks && chunks.length === 0 && (
          <div className="empty-box">暂无切块内容，请先点击上方文档的“查看切块”。</div>
        )}

        {!loadingChunks && chunks.map((chunk) => (
          <article className="chunk-card" key={String(chunk.id)}>
            <div className="chunk-meta">
              <span>chunk_index: {valueText(chunk.chunk_index)}</span>
              <span>policy_code: {valueText(chunk.policy_code)}</span>
              <span>section: {valueText(chunk.section)}</span>
              <span>parser: {valueText(chunk.parser)}</span>
              <span>token_count: {valueText(chunk.token_count)}</span>
            </div>
            <pre className="chunk-content">{valueText(chunk.content)}</pre>
          </article>
        ))}
      </section>
    </>
  );
}

type AgentToolCall = {
  tool_name: string;
  purpose: string;
  success: boolean;
  latency_ms: number;
  data?: unknown;
  error?: string | null;
};

type AftersaleAgentResponse = {
  question: string;
  order_no?: string | null;
  route_intents: string[];
  final_answer: string;
  action_plan: string[];
  risk_flags: string[];
  tool_calls: AgentToolCall[];
  created_ticket_no?: string | null;
  used_llm: boolean;
  provider: string;
  model: string;
};

export function AftersaleAgentCenter() {
  const [question, setQuestion] = useState("用户说包裹三天没更新，想要补偿，客服应该怎么处理？");
  const [orderNo, setOrderNo] = useState("ORDER-20260515-0001");
  const [autoCreateTicket, setAutoCreateTicket] = useState(false);
  const [includeAnalytics, setIncludeAnalytics] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AftersaleAgentResponse | null>(null);
  const [error, setError] = useState("");

  async function runAgent() {
    setError("");
    setLoading(true);

    try {
      const response = await fetch("/api/v1/agent/aftersale", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question,
          order_no: orderNo.trim() || null,
          top_k: 5,
          auto_create_ticket: autoCreateTicket,
          include_analytics: includeAnalytics,
        }),
      });

      const responseText = await response.text();
      const data = responseText ? JSON.parse(responseText) : null;

      if (!response.ok) {
        throw new Error(`售后 Agent 调用失败：HTTP ${response.status} ${responseText}`);
      }

      setResult(data as AftersaleAgentResponse);
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "未知错误");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      {error && <div className="error-box">{error}</div>}

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>售后 Agent</h2>
            <p>将知识库 RAG、订单上下文、工单创建和运营问数串成一个售后处理工作流。</p>
          </div>
        </div>

        <div className="query-box">
          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="例如：用户说包裹三天没更新，想要补偿，客服应该怎么处理？"
          />

          <input
            value={orderNo}
            onChange={(event) => setOrderNo(event.target.value)}
            placeholder="订单号，例如：ORDER-20260515-0001，可为空"
          />

          <label className="check-row">
            <input
              type="checkbox"
              checked={autoCreateTicket}
              onChange={(event) => setAutoCreateTicket(event.target.checked)}
            />
            <span>自动创建工单</span>
          </label>

          <label className="check-row">
            <input
              type="checkbox"
              checked={includeAnalytics}
              onChange={(event) => setIncludeAnalytics(event.target.checked)}
            />
            <span>同时调用运营问数</span>
          </label>

          <button onClick={runAgent} disabled={loading || !question.trim()}>
            {loading ? "Agent 执行中..." : "运行售后 Agent"}
          </button>
        </div>
      </section>

      {result && (
        <>
          <section className="result-grid">
            <div className="answer-card">
              <div className="card-title">Agent 最终建议</div>

              <div className="meta-row">
                <span>Provider：{result.provider}</span>
                <span>Model：{result.model}</span>
                <span>Used LLM：{String(result.used_llm)}</span>
                <span>工单：{result.created_ticket_no ?? "-"}</span>
              </div>

              <p className="answer-text">{result.final_answer}</p>
            </div>

            <div className="citation-card">
              <div className="card-title">路由意图</div>
              <div className="tag-row">
                {result.route_intents.map((item) => (
                  <span className="tag" key={item}>{item}</span>
                ))}
              </div>

              <div className="card-title margin-top">风险提示</div>
              {result.risk_flags.length === 0 && <div className="empty">暂无风险提示</div>}
              {result.risk_flags.map((item) => (
                <div className="warning-box" key={item}>{item}</div>
              ))}
            </div>
          </section>

          <section className="panel">
            <div className="panel-header">
              <div>
                <h2>下一步动作</h2>
                <p>客服可以按下面动作执行，并根据风险提示决定是否升级组长。</p>
              </div>
            </div>

            {result.action_plan.length === 0 && <div className="empty-box">暂无动作建议</div>}

            {result.action_plan.map((item, index) => (
              <article className="chunk-card" key={`${index}-${item}`}>
                <div className="chunk-meta">
                  <span>step: {index + 1}</span>
                </div>
                <p>{item}</p>
              </article>
            ))}
          </section>

          <section className="panel">
            <div className="panel-header">
              <div>
                <h2>Tool Calling 执行轨迹</h2>
                <p>展示 Agent 实际调用了哪些工具、耗时、成功状态和返回数据。</p>
              </div>
            </div>

            {result.tool_calls.map((tool) => (
              <article className="chunk-card" key={tool.tool_name}>
                <div className="chunk-meta">
                  <span>tool: {tool.tool_name}</span>
                  <span>success: {String(tool.success)}</span>
                  <span>latency_ms: {tool.latency_ms}</span>
                </div>

                <p>{tool.purpose}</p>

                {tool.error && <div className="error-box">{tool.error}</div>}

                <pre className="chunk-content">
                  {JSON.stringify(tool.data, null, 2)}
                </pre>
              </article>
            ))}
          </section>
        </>
      )}
    </>
  );
}

export function BadCaseCenter() {
  const [data, setData] = useState<ListResponse | null>(null);
  const [error, setError] = useState("");

  async function loadData() {
    setError("");

    try {
      const response = await fetch("/api/v1/ops/bad-cases?limit=50");
      if (!response.ok) {
        const text = await response.text();
        throw new Error(`加载 Bad Case 失败：HTTP ${response.status} ${text}`);
      }
      setData((await response.json()) as ListResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "未知错误");
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  return (
    <>
      {error && <div className="error-box">{error}</div>}

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Bad Case / 反馈复盘</h2>
            <p>展示 AI 问答、分类、推荐处理等场景中沉淀的问题样本，用于后续优化 Prompt 和规则。</p>
          </div>
          <button className="secondary-button" onClick={loadData}>刷新</button>
        </div>

        <section className="analytics-metrics doc-metrics">
          <div className="metric-card">
            <span>Bad Case 总数</span>
            <strong>{data?.total ?? "-"}</strong>
          </div>
          <div className="metric-card">
            <span>待复盘</span>
            <strong>{data?.items.filter((item) => String(item.status ?? "").includes("open") || String(item.status ?? "").includes("pending")).length ?? "-"}</strong>
          </div>
          <div className="metric-card">
            <span>已展示字段数</span>
            <strong>{data?.items.length ? Object.keys(data.items[0]).length : 0}</strong>
          </div>
        </section>

        <GenericTable rows={data?.items ?? []} maxColumns={10} />
      </section>
    </>
  );
}

export function MonitorCenter() {
  const [data, setData] = useState<MonitorResponse | null>(null);
  const [error, setError] = useState("");

  async function loadData() {
    setError("");

    try {
      const response = await fetch("/api/v1/ops/monitor");
      if (!response.ok) {
        const text = await response.text();
        throw new Error(`加载系统监控失败：HTTP ${response.status} ${text}`);
      }
      setData((await response.json()) as MonitorResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "未知错误");
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  return (
    <>
      {error && <div className="error-box">{error}</div>}

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>系统监控</h2>
            <p>展示核心业务表数量、最近 QA 日志和 AI 调用日志。当前是基础运营监控，后续可接 Prometheus/Grafana。</p>
          </div>
          <button className="secondary-button" onClick={loadData}>刷新</button>
        </div>

        <section className="analytics-metrics doc-metrics">
          <div className="metric-card">
            <span>系统状态</span>
            <strong>{data?.status ?? "-"}</strong>
          </div>
          <div className="metric-card">
            <span>监控表数量</span>
            <strong>{data?.table_counts.length ?? "-"}</strong>
          </div>
          <div className="metric-card">
            <span>最近 QA 日志</span>
            <strong>{data?.recent_qa_logs.length ?? "-"}</strong>
          </div>
        </section>

        <div className="ops-grid">
          <div className="analytics-card">
            <div className="card-title">核心表数量</div>
            <GenericTable rows={data?.table_counts ?? []} />
          </div>

          <div className="analytics-card">
            <div className="card-title">最近 QA Logs</div>
            <GenericTable rows={data?.recent_qa_logs ?? []} maxColumns={5} />
          </div>
        </div>

        <section className="analytics-card ops-full-card">
          <div className="card-title">最近 AI 调用</div>
          <GenericTable rows={data?.recent_ai_invocations ?? []} />
        </section>
      </section>
    </>
  );
}
