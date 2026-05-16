import { Button, Card, Form, Input, Select, Typography, message } from "antd";
import { useState } from "react";
import { createTicket } from "../api/tickets";

const uuidPattern =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export default function TicketCreatePage() {
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();

  async function handleSubmit(values: any) {
    const rawOrderId = String(values.order_id || "").trim();

    if (rawOrderId && !uuidPattern.test(rawOrderId)) {
      message.warning("订单号如果填写，必须使用后端已有的 UUID 订单号；测试时可以先留空。");
      return;
    }

    setLoading(true);
    try {
      const payload = {
        order_id: rawOrderId || undefined,
        customer_question: values.customer_question,
        category: values.category || undefined,
        priority: values.priority || undefined,
      };

      const result = await createTicket(payload);
      message.success("工单创建成功");
      console.log("create ticket result:", result);
      form.resetFields();
    } catch (err: any) {
      console.error("create ticket error:", err);
      message.error(err?.response?.data?.detail || "工单创建接口调用失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <Typography.Title level={3}>创建工单</Typography.Title>
      <Typography.Paragraph type="secondary">
        输入用户问题，调用后端 AI 创建售后工单。订单号可先留空；如果填写，必须是后端已有 UUID。
      </Typography.Paragraph>

      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{
          order_id: "",
          customer_question: "我的包裹三天没更新了，能不能退款或者补偿？",
          priority: "high",
          category: "logistics_delay_refund",
        }}
      >
        <Form.Item label="订单号" name="order_id">
          <Input placeholder="可选；例如 22222222-2222-2222-2222-222222222201" />
        </Form.Item>

        <Form.Item
          label="用户问题"
          name="customer_question"
          rules={[{ required: true, message: "请输入用户问题" }]}
        >
          <Input.TextArea rows={6} placeholder="例如：我的包裹三天没更新了，能不能退款或者补偿？" />
        </Form.Item>

        <Form.Item label="问题分类" name="category">
          <Select
            allowClear
            options={[
              { label: "物流延迟/退款补偿", value: "logistics_delay_refund" },
              { label: "退款问题", value: "refund" },
              { label: "换货问题", value: "exchange" },
              { label: "商品质量投诉", value: "quality_complaint" },
              { label: "发票问题", value: "invoice" },
            ]}
          />
        </Form.Item>

        <Form.Item label="优先级" name="priority">
          <Select
            allowClear
            options={[
              { label: "高", value: "high" },
              { label: "中", value: "medium" },
              { label: "低", value: "low" },
            ]}
          />
        </Form.Item>

        <Button type="primary" htmlType="submit" loading={loading}>
          创建工单
        </Button>
      </Form>
    </Card>
  );
}
