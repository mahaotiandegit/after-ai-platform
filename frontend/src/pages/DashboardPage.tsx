import { Card, Col, Row, Statistic, Typography } from "antd";
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer } from "recharts";

const trendData = [
  { date: "D-6", tickets: 18 },
  { date: "D-5", tickets: 24 },
  { date: "D-4", tickets: 20 },
  { date: "D-3", tickets: 31 },
  { date: "D-2", tickets: 28 },
  { date: "D-1", tickets: 36 },
  { date: "Today", tickets: 42 },
];

export default function DashboardPage() {
  return (
    <div>
      <Typography.Title level={3}>Dashboard 首页</Typography.Title>
      <Typography.Paragraph type="secondary">
        当前页面用于演示系统整体概览：知识问答、工单、AI 质量、Bad Case。
      </Typography.Paragraph>

      <Row gutter={16}>
        <Col span={6}>
          <Card>
            <Statistic title="今日工单" value={42} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="知识问答次数" value={128} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="AI 平均质量分" value={86.5} suffix="分" />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="Bad Case 数" value={7} />
          </Card>
        </Col>
      </Row>

      <Card title="近 7 天工单趋势" style={{ marginTop: 16 }}>
        <div style={{ width: "100%", height: 320 }}>
          <ResponsiveContainer>
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="tickets" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </div>
  );
}
