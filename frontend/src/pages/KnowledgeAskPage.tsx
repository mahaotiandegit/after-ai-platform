import { Button, Card, Input, Space, Typography } from "antd";

export default function KnowledgeAskPage() {
  return (
    <Card>
      <Typography.Title level={3}>知识问答</Typography.Title>
      <Typography.Paragraph type="secondary">
        下一阶段接入 /api/v1/knowledge/ask 或增强版 RAG 接口，展示 answer、citations、chunks。
      </Typography.Paragraph>
      <Space.Compact style={{ width: "100%" }}>
        <Input placeholder="例如：物流延迟应该怎么补偿？" />
        <Button type="primary">提问</Button>
      </Space.Compact>
    </Card>
  );
}
