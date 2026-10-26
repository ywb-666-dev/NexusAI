import { useState, useRef } from "react";
import { Form, Input, Button, Card, Typography, Tabs, App } from "antd";
import {
  UserOutlined,
  LockOutlined,
  MailOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/auth";
import request from "../api/request";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";

gsap.registerPlugin(useGSAP);
const { Title, Text } = Typography;

export default function Login() {
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState("login");
  const navigate = useNavigate();
  const { setToken, setUser } = useAuthStore();
  const { message } = App.useApp();
  const cardRef = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      gsap.from(cardRef.current, {
        y: 40,
        autoAlpha: 0,
        duration: 0.7,
        ease: "power3.out",
      });
    },
    { scope: cardRef },
  );

  const onFinish = async (values: any) => {
    setLoading(true);
    try {
      const endpoint =
        tab === "login" ? "/java/auth/login" : "/java/auth/register";
      const res: any = await request.post(endpoint, values);
      if (tab === "login") {
        setToken(res.data.token);
        setUser(res.data.user);
        navigate("/dashboard");
      } else {
        message.success("注册成功，请登录");
        setTab("login");
      }
    } catch (err: any) {
      message.error(err.response?.data?.message || err.message || "操作失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background:
          "linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #0f172a 100%)",
      }}
    >
      <Card
        ref={cardRef as any}
        style={{
          width: 400,
          maxWidth: "calc(100vw - 32px)",
          borderRadius: 16,
          border: "none",
          boxShadow: "0 25px 60px rgba(0,0,0,0.3)",
        }}
        styles={{ body: { padding: "32px 36px" } }}
      >
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <div
            style={{
              width: 52,
              height: 52,
              borderRadius: 14,
              background: "linear-gradient(135deg, #30c8da, #107b93)",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              marginBottom: 12,
            }}
          >
            <ThunderboltOutlined style={{ color: "#fff", fontSize: 26 }} />
          </div>
          <Title level={3} style={{ margin: 0, fontWeight: 700 }}>
            NexusAI
          </Title>
          <Text style={{ color: "#94a3b8" }}>
            订阅驱动 · 智能聚合 · 即时洞察
          </Text>
        </div>
        <Tabs
          activeKey={tab}
          onChange={setTab}
          centered
          items={[
            { key: "login", label: "登录" },
            { key: "register", label: "注册" },
          ]}
        />
        <Form onFinish={onFinish} layout="vertical" size="large">
          <Form.Item
            name="username"
            rules={[{ required: true, message: "请输入用户名" }]}
          >
            <Input
              prefix={<UserOutlined />}
              placeholder="用户名"
              style={{ borderRadius: 10 }}
            />
          </Form.Item>
          {tab === "register" && (
            <Form.Item
              name="email"
              rules={[{ type: "email", message: "请输入有效邮箱" }]}
            >
              <Input
                prefix={<MailOutlined />}
                placeholder="邮箱（可选）"
                style={{ borderRadius: 10 }}
              />
            </Form.Item>
          )}
          <Form.Item
            name="password"
            rules={[{ required: true, min: 6, message: "密码至少 6 位" }]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="密码"
              style={{ borderRadius: 10 }}
            />
          </Form.Item>
          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              block
              style={{
                borderRadius: 10,
                height: 44,
                background: "linear-gradient(135deg, #30c8da, #107b93)",
                border: "none",
                fontWeight: 600,
                fontSize: 15,
              }}
            >
              {tab === "login" ? "进入工作台" : "创建账号"}
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
