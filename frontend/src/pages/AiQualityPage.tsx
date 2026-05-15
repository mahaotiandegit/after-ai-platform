import { Card, Table, Typography } from "antd";

export default function AiQualityPage() {
  return (
    <Card>
      <Typography.Title level={3}>AI 质量看板</Typography.Title>
      <Table
        rowKey="id"
        dataSource={[]}
        columns={[
          { title: "评估时间", dataIndex: "created_at" },
          { title: "业务场景", dataIndex: "scene" },
          { title: "质量分", dataIndex: "score" },
          { title: "风险等级", dataIndex: "risk_level" },
          { title: "是否转 Bad Case", dataIndex: "bad_case_created" },
        ]}
      />
    </Card>
  );
}
