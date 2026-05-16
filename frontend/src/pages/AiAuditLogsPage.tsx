import { Button, Card, Space, Table, Tag, Typography, message } from "antd";
import { useEffect, useState } from "react";
import { listAiAuditLogs } from "../api/aiAudit";
import type { AiAuditLogItem } from "../types/aiAudit";

export default function AiAuditLogsPage() {
  const [data, setData] = useState<AiAuditLogItem[]>([]);
  const [loading, setLoading] = useState(false);

  async function loadData() {
    setLoading(true);
    try {
      const rows = await listAiAuditLogs();
      setData(rows);
    } catch (err: any) {
      console.error(err);
      message.error(err?.response?.data?.detail || "AI 审计日志接口调用失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  return (
    <Card>
      <Space style={{ width: "100%", justifyContent: "space-between", marginBottom: 16 }}>
        <div>
          <Typography.Title level={3} style={{ marginBottom: 0 }}>AI 审计日志</Typography.Title>
          <Typography.Text type="secondary">
            记录 RAG、工单分类、NL2SQL 等 AI 调用的输入、输出、耗时和结果。
          </Typography.Text>
        </div>
        <Button onClick={loadData}>刷新</Button>
      </Space>

      <Table
        rowKey={(row) => row.id || Math.random().toString()}
        loading={loading}
        dataSource={data}
        columns={[
          {
            title: "调用时间",
            dataIndex: "created_at",
            width: 190,
          },
          {
            title: "场景",
            dataIndex: "scene",
            width: 180,
          },
          {
            title: "模型/Provider",
            width: 220,
            render: (_, row) => `${row.provider || "-"} / ${row.model || "-"}`,
          },
          {
            title: "耗时",
            dataIndex: "latency_ms",
            width: 100,
            render: (value) => value !== undefined && value !== null ? `${value} ms` : "-",
          },
          {
            title: "状态",
            width: 100,
            render: (_, row) => {
              const ok = row.success === true || row.status === "success";
              return <Tag color={ok ? "green" : "red"}>{ok ? "success" : "failed"}</Tag>;
            },
          },
          {
            title: "输入摘要",
            dataIndex: "input_summary",
            ellipsis: true,
          },
          {
            title: "错误",
            dataIndex: "error_message",
            ellipsis: true,
            render: (value) => value || "-",
          },
        ]}
      />
    </Card>
  );
}
