import { Card, Table, Tag, Typography } from "antd";

const data = [
  {
    id: "TICKET-001",
    title: "物流延迟退款补偿处理",
    category: "logistics_delay_refund",
    priority: "high",
    status: "open",
    createdAt: "2026-05-16",
  },
];

export default function TicketListPage() {
  return (
    <Card>
      <Typography.Title level={3}>工单列表</Typography.Title>
      <Table
        rowKey="id"
        dataSource={data}
        columns={[
          { title: "工单号", dataIndex: "id" },
          { title: "标题", dataIndex: "title" },
          { title: "分类", dataIndex: "category" },
          {
            title: "优先级",
            dataIndex: "priority",
            render: (value) => <Tag color={value === "high" ? "red" : "blue"}>{value}</Tag>,
          },
          { title: "状态", dataIndex: "status" },
          { title: "创建时间", dataIndex: "createdAt" },
        ]}
      />
    </Card>
  );
}
