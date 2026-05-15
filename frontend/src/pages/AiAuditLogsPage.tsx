import { Card, Table, Typography } from "antd";

export default function AiAuditLogsPage() {
  return (
    <Card>
      <Typography.Title level={3}>AI 审计日志</Typography.Title>
      <Table
        rowKey="id"
        dataSource={[]}
        columns={[
          { title: "调用时间", dataIndex: "created_at" },
          { title: "场景", dataIndex: "scene" },
          { title: "模型/Provider", dataIndex: "provider" },
          { title: "耗时", dataIndex: "latency_ms" },
          { title: "状态", dataIndex: "status" },
        ]}
      />
    </Card>
  );
}
