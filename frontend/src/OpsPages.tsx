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
  const [error, setError] = useState("");
  const [uploadMessage, setUploadMessage] = useState("");
  const [uploading, setUploading] = useState(false);
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

  return (
    <>
      {error && <div className="error-box">{error}</div>}
      {uploadMessage && <div className="success-box">{uploadMessage}</div>}

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>文档上传</h2>
            <p>上传售后规则、SOP、活动政策等知识库文档。当前 MVP 先支持 txt / md / csv / json / log。</p>
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
            accept=".txt,.md,.markdown,.csv,.json,.log"
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
            <p>展示已入库文档、文件类型、索引状态和切块数量。</p>
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
            <strong>{data?.items.filter((item) => item.status === "indexed").length ?? "-"}</strong>
          </div>
          <div className="metric-card">
            <span>总切块数</span>
            <strong>{data?.items.reduce((sum, item) => sum + Number(item.chunk_count ?? 0), 0) ?? "-"}</strong>
          </div>
        </section>

        <GenericTable rows={data?.items ?? []} />
      </section>
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
