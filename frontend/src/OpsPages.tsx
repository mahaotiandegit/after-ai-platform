import { useEffect, useState } from "react";

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

  useEffect(() => {
    loadData();
  }, []);

  return (
    <>
      {error && <div className="error-box">{error}</div>}

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>文档管理</h2>
            <p>展示已入库文档、文件类型、索引状态和切块数量。当前先做列表展示，上传解析后续接入。</p>
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
