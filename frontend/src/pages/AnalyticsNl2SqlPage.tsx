import { Button, Card, Input, Typography } from "antd";

export default function AnalyticsNl2SqlPage() {
  return (
    <Card>
      <Typography.Title level={3}>运营问数</Typography.Title>
      <Typography.Paragraph type="secondary">
        下一阶段接入 NL2SQL：自然语言生成 SQL、返回表格和分析摘要。
      </Typography.Paragraph>
      <Input.TextArea rows={4} placeholder="例如：最近 7 天物流异常类工单有多少？" />
      <Button type="primary" style={{ marginTop: 12 }}>生成分析</Button>
    </Card>
  );
}
