import { Button, Card, Form, Input, Typography } from "antd";

export default function TicketCreatePage() {
  return (
    <Card>
      <Typography.Title level={3}>创建工单</Typography.Title>
      <Typography.Paragraph type="secondary">
        下一阶段接入 AI 分类、摘要、优先级判断和创建工单接口。
      </Typography.Paragraph>

      <Form layout="vertical">
        <Form.Item label="订单号">
          <Input placeholder="可选，例如 ORDER-20260516-001" />
        </Form.Item>

        <Form.Item label="用户问题">
          <Input.TextArea rows={6} placeholder="例如：我的包裹三天没更新了，能不能退款或者补偿？" />
        </Form.Item>

        <Button type="primary">AI 生成并创建工单</Button>
      </Form>
    </Card>
  );
}
