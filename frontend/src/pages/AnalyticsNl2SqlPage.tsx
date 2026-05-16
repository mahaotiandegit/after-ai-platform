import { Button, Card, Input, Space, Table, Typography, message } from "antd";
import { useState } from "react";
import { askAnalytics } from "../api/analytics";
import type { AnalyticsAskResponse } from "../types/analytics";

export default function AnalyticsNl2SqlPage() {
  const [question, setQuestion] = useState("最近7天物流延迟类工单有多少？");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalyticsAskResponse | null>(null);

  async function handleAsk() {
    if (!question.trim()) {
      message.warning("请输入运营问题");
      return;
    }

    setLoading(true);
    try {
      const data = await askAnalytics({ question, limit: 20 });
      setResult(data);
      message.success("分析完成");
    } catch (err: any) {
      console.error(err);
      message.error(err?.response?.data?.detail || "运营问数接口调用失败");
    } finally {
      setLoading(false);
    }
  }

  const rows = result?.rows || [];
  const columns = result?.columns?.length
    ? result.columns
    : rows.length
      ? Object.keys(rows[0])
      : [];

  const tableColumns = columns.map((key) => ({
    title: key,
    dataIndex: key,
    key,
    render: (value: any) => {
      if (value === null || value === undefined) return "-";
      if (typeof value === "object") return JSON.stringify(value);
      return String(value);
    },
  }));

  return (
    <div>
      <Typography.Title level={3}>运营问数</Typography.Title>
      <Typography.Paragraph type="secondary">
        输入自然语言问题，后端生成 SQL，执行查询并返回表格与摘要。
      </Typography.Paragraph>

      <Card>
        <Input.TextArea
          rows={4}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="例如：最近 7 天物流延迟类工单有多少？"
        />

        <Space style={{ marginTop: 12 }}>
          <Button type="primary" loading={loading} onClick={handleAsk}>
            生成分析
          </Button>
          <Button onClick={() => setQuestion("最近7天售后问题类型分布怎么样？")}>
            问题类型分布
          </Button>
          <Button onClick={() => setQuestion("最近7天高优先级工单多吗？按优先级统计一下")}>
            优先级统计
          </Button>
        </Space>
      </Card>

      {result && (
        <Card title="分析结果" style={{ marginTop: 16 }}>
          <Typography.Title level={5}>摘要</Typography.Title>
          <Typography.Paragraph>{result.summary || "暂无摘要"}</Typography.Paragraph>

          <Typography.Title level={5}>生成 SQL</Typography.Title>
          <pre
            style={{
              background: "#f6f8fa",
              padding: 12,
              borderRadius: 6,
              overflowX: "auto",
            }}
          >
            {result.sql || "暂无 SQL"}
          </pre>

          <Typography.Title level={5}>查询结果</Typography.Title>
          <Table
            rowKey={(_, index) => String(index)}
            dataSource={rows}
            columns={tableColumns}
            pagination={false}
          />
        </Card>
      )}
    </div>
  );
}
