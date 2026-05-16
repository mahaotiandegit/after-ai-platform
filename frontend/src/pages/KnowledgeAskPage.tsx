import { Button, Card, Divider, Input, List, Space, Typography, message } from "antd";
import { useState } from "react";
import { askKnowledge } from "../api/knowledge";
import type { KnowledgeAskResponse } from "../types/knowledge";

export default function KnowledgeAskPage() {
  const [question, setQuestion] = useState("物流延迟应该怎么补偿？");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<KnowledgeAskResponse | null>(null);

  async function handleAsk() {
    if (!question.trim()) {
      message.warning("请输入问题");
      return;
    }

    setLoading(true);
    try {
      const data = await askKnowledge({ question, top_k: 5 });
      setResult(data);
      message.success("问答完成");
    } catch (err: any) {
      message.error(err?.response?.data?.detail || "知识问答接口调用失败");
    } finally {
      setLoading(false);
    }
  }

  const answer = result?.answer || result?.answer_summary || "";
  const chunks = result?.chunks || result?.hits || [];

  return (
    <div>
      <Typography.Title level={3}>知识问答</Typography.Title>
      <Typography.Paragraph type="secondary">
        输入售后问题，系统调用 RAG 接口返回答案、引用来源和命中文档片段。
      </Typography.Paragraph>

      <Card>
        <Space.Compact style={{ width: "100%" }}>
          <Input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="例如：物流延迟应该怎么补偿？"
            onPressEnter={handleAsk}
          />
          <Button type="primary" loading={loading} onClick={handleAsk}>
            提问
          </Button>
        </Space.Compact>
      </Card>

      {result && (
        <Card title="AI 回答" style={{ marginTop: 16 }}>
          <Typography.Paragraph style={{ whiteSpace: "pre-wrap" }}>
            {answer || "接口已返回，但没有 answer / answer_summary 字段。"}
          </Typography.Paragraph>

          <Divider />

          <Typography.Title level={5}>引用 / 命中片段</Typography.Title>
          <List
            bordered
            dataSource={chunks}
            locale={{ emptyText: "暂无 chunks / hits" }}
            renderItem={(item, index) => (
              <List.Item>
                <div>
                  <Typography.Text strong>
                    #{index + 1} {item.document_title || item.source || item.id || "未命名来源"}
                  </Typography.Text>
                  <Typography.Paragraph style={{ marginTop: 8, marginBottom: 0 }}>
                    {item.content || JSON.stringify(item)}
                  </Typography.Paragraph>
                </div>
              </List.Item>
            )}
          />
        </Card>
      )}
    </div>
  );
}
