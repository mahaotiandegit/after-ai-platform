import { Card, Table, Typography } from "antd";

export default function BadCasesPage() {
  return (
    <Card>
      <Typography.Title level={3}>Bad Case 复盘</Typography.Title>
      <Table
        rowKey="id"
        dataSource={[]}
        columns={[
          { title: "创建时间", dataIndex: "created_at" },
          { title: "问题类型", dataIndex: "case_type" },
          { title: "风险等级", dataIndex: "risk_level" },
          { title: "状态", dataIndex: "status" },
          { title: "复盘结论", dataIndex: "review_result" },
        ]}
      />
    </Card>
  );
}
