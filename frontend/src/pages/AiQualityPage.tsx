import { Button, Card, Col, Row, Space, Statistic, Table, Tag, Typography, message } from "antd";
import { useEffect, useMemo, useState } from "react";
import { listAiAuditLogs } from "../api/aiAudit";
import { listBadCases } from "../api/badCases";
import type { AiAuditLogItem } from "../types/aiAudit";
import type { BadCaseItem } from "../types/badCase";

export default function AiQualityPage() {
  const [logs, setLogs] = useState<AiAuditLogItem[]>([]);
  const [badCases, setBadCases] = useState<BadCaseItem[]>([]);
  const [loading, setLoading] = useState(false);

  async function loadData() {
    setLoading(true);
    try {
      const [auditRows, badCaseRows] = await Promise.all([
        listAiAuditLogs(),
        listBadCases(),
      ]);
      setLogs(auditRows);
      setBadCases(badCaseRows);
    } catch (err: any) {
      console.error(err);
      message.error(err?.response?.data?.detail || "AI 质量数据加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  const stats = useMemo(() => {
    const total = logs.length;
    const success = logs.filter((x) => x.success === true || x.status === "success").length;
    const failed = total - success;
    const avgLatency =
      total === 0
        ? 0
        : Math.round(logs.reduce((sum, x) => sum + (x.latency_ms || 0), 0) / total);

    const successRate = total === 0 ? 0 : Math.round((success / total) * 1000) / 10;
    const qualityScore = Math.max(0, Math.round(successRate - badCases.length * 1.5));

    return {
      total,
      success,
      failed,
      avgLatency,
      successRate,
      qualityScore,
      badCaseCount: badCases.length,
    };
  }, [logs, badCases]);

  const sceneRows = useMemo(() => {
    const map = new Map<string, { scene: string; total: number; success: number; failed: number; badCases: number }>();

    for (const log of logs) {
      const scene = log.scene || "unknown";
      const row = map.get(scene) || { scene, total: 0, success: 0, failed: 0, badCases: 0 };
      row.total += 1;
      if (log.success === true || log.status === "success") row.success += 1;
      else row.failed += 1;
      map.set(scene, row);
    }

    for (const bc of badCases) {
      const scene = bc.scene || "unknown";
      const row = map.get(scene) || { scene, total: 0, success: 0, failed: 0, badCases: 0 };
      row.badCases += 1;
      map.set(scene, row);
    }

    return Array.from(map.values()).map((row) => {
      const successRate = row.total === 0 ? 0 : Math.round((row.success / row.total) * 1000) / 10;
      const score = Math.max(0, Math.round(successRate - row.badCases * 3));
      const risk = row.badCases >= 3 || row.failed >= 3 ? "high" : row.badCases >= 1 || row.failed >= 1 ? "medium" : "low";
      return { ...row, successRate, score, risk };
    });
  }, [logs, badCases]);

  return (
    <Card>
      <Space style={{ width: "100%", justifyContent: "space-between", marginBottom: 16 }}>
        <div>
          <Typography.Title level={3} style={{ marginBottom: 0 }}>AI 质量看板</Typography.Title>
          <Typography.Text type="secondary">
            后端暂未提供独立 ai-quality 接口，当前页面基于 AI 审计日志和 Bad Case 聚合质量指标。
          </Typography.Text>
        </div>
        <Button onClick={loadData}>刷新</Button>
      </Space>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic title="AI 调用总数" value={stats.total} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="成功率" value={stats.successRate} suffix="%" />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="平均耗时" value={stats.avgLatency} suffix="ms" />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="Bad Case 数" value={stats.badCaseCount} />
          </Card>
        </Col>
      </Row>

      <Card title={`综合质量分：${stats.qualityScore}`}>
        <Table
          rowKey="scene"
          loading={loading}
          dataSource={sceneRows}
          columns={[
            { title: "业务场景", dataIndex: "scene" },
            { title: "调用次数", dataIndex: "total" },
            { title: "成功次数", dataIndex: "success" },
            { title: "失败次数", dataIndex: "failed" },
            { title: "Bad Case", dataIndex: "badCases" },
            {
              title: "成功率",
              dataIndex: "successRate",
              render: (value) => `${value}%`,
            },
            {
              title: "质量分",
              dataIndex: "score",
            },
            {
              title: "风险等级",
              dataIndex: "risk",
              render: (value) => {
                const color = value === "high" ? "red" : value === "medium" ? "orange" : "green";
                return <Tag color={color}>{value}</Tag>;
              },
            },
          ]}
        />
      </Card>
    </Card>
  );
}
