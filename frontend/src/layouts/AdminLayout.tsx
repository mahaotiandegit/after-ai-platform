import {
  DashboardOutlined,
  DatabaseOutlined,
  FileSearchOutlined,
  FormOutlined,
  MessageOutlined,
  ProfileOutlined,
  SafetyCertificateOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import { Button, Layout, Menu, Typography } from "antd";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { clearToken } from "../utils/token";

const { Header, Sider, Content } = Layout;

export default function AdminLayout() {
  const navigate = useNavigate();
  const location = useLocation();

  const menuItems = [
    {
      key: "/dashboard",
      icon: <DashboardOutlined />,
      label: "Dashboard",
    },
    {
      key: "/knowledge/ask",
      icon: <FileSearchOutlined />,
      label: "知识问答",
    },
    {
      key: "/tickets",
      icon: <ProfileOutlined />,
      label: "工单列表",
    },
    {
      key: "/tickets/create",
      icon: <FormOutlined />,
      label: "创建工单",
    },
    {
      key: "/analytics/nl2sql",
      icon: <DatabaseOutlined />,
      label: "运营问数",
    },
    {
      key: "/ai-audit-logs",
      icon: <MessageOutlined />,
      label: "AI 审计日志",
    },
    {
      key: "/ai-quality",
      icon: <SafetyCertificateOutlined />,
      label: "AI 质量看板",
    },
    {
      key: "/bad-cases",
      icon: <WarningOutlined />,
      label: "Bad Case 复盘",
    },
  ];

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider width={230}>
        <div style={{ height: 56, color: "#fff", display: "flex", alignItems: "center", paddingLeft: 20 }}>
          <Typography.Text style={{ color: "#fff", fontWeight: 700 }}>
            售后 AI 工作台
          </Typography.Text>
        </div>

        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={(item) => navigate(item.key)}
        />
      </Sider>

      <Layout>
        <Header
          style={{
            background: "#fff",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "0 24px",
            borderBottom: "1px solid #eee",
          }}
        >
          <Typography.Text strong>电商售后知识与工单自动化平台</Typography.Text>

          <Button
            onClick={() => {
              clearToken();
              navigate("/login");
            }}
          >
            退出登录
          </Button>
        </Header>

        <Content style={{ padding: 24, background: "#f5f5f5" }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
