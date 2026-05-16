import { Button, Card, Space, Table, Tag, Typography, message } from "antd";
import { useEffect, useState } from "react";
import { listTickets } from "../api/tickets";
import type { TicketItem } from "../types/ticket";

export default function TicketListPage() {
  const [data, setData] = useState<TicketItem[]>([]);
  const [loading, setLoading] = useState(false);

  async function loadData() {
    setLoading(true);
    try {
      const rows = await listTickets();
      setData(rows);
    } catch (err: any) {
      message.error(err?.response?.data?.detail || "工单列表接口调用失败");
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
          <Typography.Title level={3} style={{ marginBottom: 0 }}>工单列表</Typography.Title>
          <Typography.Text type="secondary">展示 AI 创建或人工创建的售后工单。</Typography.Text>
        </div>
        <Button onClick={loadData}>刷新</Button>
      </Space>

      <Table
        rowKey={(row) => row.id || row.ticket_no || Math.random().toString()}
        loading={loading}
        dataSource={data}
        columns={[
          {
            title: "工单号",
            render: (_, row) => row.ticket_no || row.id || "-",
          },
          {
            title: "标题",
            render: (_, row) => row.title || row.summary || row.customer_question || "-",
          },
          {
            title: "分类",
            dataIndex: "category",
            render: (value) => value || "-",
          },
          {
            title: "优先级",
            dataIndex: "priority",
            render: (value) => {
              const color = value === "high" ? "red" : value === "medium" ? "orange" : "blue";
              return <Tag color={color}>{value || "unknown"}</Tag>;
            },
          },
          {
            title: "状态",
            dataIndex: "status",
            render: (value) => <Tag>{value || "unknown"}</Tag>,
          },
          {
            title: "创建时间",
            render: (_, row) => row.created_at || row.createdAt || "-",
          },
        ]}
      />
    </Card>
  );
}
