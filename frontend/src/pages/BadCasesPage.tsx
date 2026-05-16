import { Button, Card, Space, Table, Tag, Typography, message } from "antd";
import { useEffect, useState } from "react";
import { listBadCases } from "../api/badCases";
import type { BadCaseItem } from "../types/badCase";

export default function BadCasesPage() {
  const [data, setData] = useState<BadCaseItem[]>([]);
  const [loading, setLoading] = useState(false);

  async function loadData() {
    setLoading(true);
    try {
      const rows = await listBadCases();
      setData(rows);
    } catch (err: any) {
      console.error(err);
      message.error(err?.response?.data?.detail || "Bad Case 接口调用失败");
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
          <Typography.Title level={3} style={{ marginBottom: 0 }}>Bad Case 复盘</Typography.Title>
          <Typography.Text type="secondary">
            沉淀 AI 错误案例，用于 Prompt、规则、知识库和流程优化。
          </Typography.Text>
        </div>
        <Button onClick={loadData}>刷新</Button>
      </Space>

      <Table
        rowKey={(row) => row.id || Math.random().toString()}
        loading={loading}
        dataSource={data}
        expandable={{
          expandedRowRender: (row) => (
            <div>
              <Typography.Text strong>根因：</Typography.Text>
              <Typography.Paragraph>{row.root_cause || "-"}</Typography.Paragraph>

              <Typography.Text strong>修正方案：</Typography.Text>
              <Typography.Paragraph>{row.correction || row.review_result || "-"}</Typography.Paragraph>

              <Typography.Text strong>标签：</Typography.Text>
              <Typography.Paragraph>{row.tags?.join(", ") || "-"}</Typography.Paragraph>
            </div>
          ),
        }}
        columns={[
          {
            title: "创建时间",
            dataIndex: "created_at",
            width: 190,
          },
          {
            title: "场景",
            dataIndex: "scene",
            width: 160,
          },
          {
            title: "问题",
            dataIndex: "question",
            ellipsis: true,
            render: (value) => value || "-",
          },
          {
            title: "优先级",
            width: 100,
            render: (_, row) => {
              const value = row.priority || row.risk_level || "unknown";
              const color = value === "high" ? "red" : value === "medium" ? "orange" : "blue";
              return <Tag color={color}>{value}</Tag>;
            },
          },
          {
            title: "状态",
            dataIndex: "status",
            width: 100,
            render: (value) => <Tag>{value || "unknown"}</Tag>,
          },
          {
            title: "根因",
            dataIndex: "root_cause",
            ellipsis: true,
            render: (value) => value || "-",
          },
          {
            title: "修正方案",
            dataIndex: "correction",
            ellipsis: true,
            render: (value) => value || "-",
          },
        ]}
      />
    </Card>
  );
}
