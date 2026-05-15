import { Button, Card, Form, Input, Typography, message } from "antd";
import { useNavigate } from "react-router-dom";
import { setToken } from "../utils/token";

export default function LoginPage() {
  const navigate = useNavigate();

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#f5f5f5",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <Card style={{ width: 420 }}>
        <Typography.Title level={3}>售后 AI 工作台</Typography.Title>
        <Typography.Paragraph type="secondary">
          MVP 阶段先使用本地登录，下一阶段接入后端登录接口。
        </Typography.Paragraph>

        <Form
          layout="vertical"
          initialValues={{ username: "admin", password: "admin123" }}
          onFinish={() => {
            setToken("dev-local-token");
            message.success("登录成功");
            navigate("/dashboard");
          }}
        >
          <Form.Item label="账号" name="username" rules={[{ required: true, message: "请输入账号" }]}>
            <Input placeholder="admin" />
          </Form.Item>

          <Form.Item label="密码" name="password" rules={[{ required: true, message: "请输入密码" }]}>
            <Input.Password placeholder="admin123" />
          </Form.Item>

          <Button type="primary" htmlType="submit" block>
            登录
          </Button>
        </Form>
      </Card>
    </div>
  );
}
