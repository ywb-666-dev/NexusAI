import { useEffect, useState, Suspense } from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import {
  Layout,
  Menu,
  Badge,
  Avatar,
  Dropdown,
  Input,
  Button,
  Space,
  Typography,
  Skeleton,
} from "antd";
import {
  DashboardOutlined,
  UnorderedListOutlined,
  FileTextOutlined,
  CheckSquareOutlined,
  BellOutlined,
  LogoutOutlined,
  UserOutlined,
  ThunderboltOutlined,
  BulbOutlined,
  SearchOutlined,
  DeploymentUnitOutlined,
  SendOutlined,
} from "@ant-design/icons";
import { useAuthStore } from "../store/auth";
import { useThemeStore } from "../store/theme";
import request from "../api/request";
const baseItems = [
  { key: "/dashboard", icon: <DashboardOutlined />, label: "运行总览" },
  { key: "/subscriptions", icon: <UnorderedListOutlined />, label: "我的订阅" },
  { key: "/sources", icon: <SearchOutlined />, label: "数据源中心" },
  { key: "/contents", icon: <FileTextOutlined />, label: "内容中心" },
  { key: "/tasks", icon: <DeploymentUnitOutlined />, label: "任务监控" },
  { key: "/notifications", icon: <BellOutlined />, label: "通知中心" },
  { key: "/push", icon: <SendOutlined />, label: "推送设置" },
];
export default function BasicLayout() {
  const navigate = useNavigate(),
    location = useLocation();
  const { user, logout } = useAuthStore(),
    { dark, toggle } = useThemeStore();
  const [unread, setUnread] = useState(0),
    [collapsed, setCollapsed] = useState(false);
  useEffect(() => {
    const refresh = () =>
      request
        .get("/java/notifications/unread-count")
        .then((r: any) => setUnread(r.data || 0))
        .catch(() => {});
    refresh();
    const timer = setInterval(refresh, 30000);
    window.addEventListener("nexus:notifications", refresh);
    return () => {
      clearInterval(timer);
      window.removeEventListener("nexus:notifications", refresh);
    };
  }, []);
  const items = [
    ...baseItems,
    ...(user?.role === "admin"
      ? [
          {
            key: "/approvals",
            icon: <CheckSquareOutlined />,
            label: "审批中心",
          },
        ]
      : []),
  ];
  return (
    <Layout
      className={"nexus-shell" + (dark ? "" : " light")}
      style={{ minHeight: "100vh" }}
    >
      <Layout.Sider
        width={224}
        collapsed={collapsed}
        breakpoint="lg"
        onBreakpoint={setCollapsed}
        collapsedWidth={64}
        style={{ background: dark ? "#0c1526" : "#fff" }}
      >
        <div className="nexus-brand">
          <span className="nexus-brand-mark">
            <ThunderboltOutlined />
          </span>
          {!collapsed && (
            <div>
              <strong>NexusAI</strong>
              <span className="eyebrow" style={{ fontSize: 8 }}>
                INTELLIGENCE IN FLOW
              </span>
            </div>
          )}
        </div>
        <Menu
          mode="inline"
          theme={dark ? "dark" : "light"}
          selectedKeys={[location.pathname]}
          items={items}
          style={{ background: "transparent", border: 0, padding: "0 8px" }}
          onClick={({ key }) => navigate(key)}
        />
        {!collapsed && (
          <div className="nexus-footer">订阅 · 理解 · 聚合 · 行动</div>
        )}
      </Layout.Sider>
      <Layout>
        <header className="nexus-topbar">
          <Typography.Text type="secondary">内容情报工作台</Typography.Text>
          <Space size={18}>
            <Input
              prefix={<SearchOutlined />}
              placeholder="搜索订阅内容"
              allowClear
              style={{ maxWidth: 230 }}
              onPressEnter={(e) =>
                navigate(
                  "/contents?search=" +
                    encodeURIComponent(e.currentTarget.value),
                )
              }
            />
            <Badge count={unread} size="small">
              <Button
                type="text"
                aria-label="打开通知"
                icon={<BellOutlined />}
                onClick={() => navigate("/notifications")}
              />
            </Badge>
            <Button
              type="text"
              aria-label="切换主题"
              icon={<BulbOutlined />}
              onClick={toggle}
            />
            <Dropdown
              menu={{
                items: [
                  { key: "name", label: user?.username, disabled: true },
                  {
                    key: "logout",
                    label: "退出登录",
                    icon: <LogoutOutlined />,
                    onClick: logout,
                  },
                ],
              }}
            >
              <Avatar
                style={{ background: "#177f91", cursor: "pointer" }}
                icon={<UserOutlined />}
              />
            </Dropdown>
          </Space>
        </header>
        <main className="nexus-main">
          <Suspense fallback={<Skeleton active paragraph={{ rows: 6 }} />}>
            <Outlet />
          </Suspense>
        </main>
      </Layout>
    </Layout>
  );
}
