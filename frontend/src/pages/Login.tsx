import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Form, Input, Button, Tabs, Typography } from 'antd'
import { ThunderboltOutlined, LockOutlined, UserOutlined, MailOutlined } from '@ant-design/icons'
import { useAuthStore } from '../store/auth'
import request from '../api/request'
import { App } from 'antd'

const { Title, Text } = Typography

function Login() {
  const navigate = useNavigate()
  const { setToken, setUser } = useAuthStore()
  const { message } = App.useApp()
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('login')
  const [loginForm] = Form.useForm()
  const [registerForm] = Form.useForm()

  const handleLogin = async (values: { username: string; password: string }) => {
    setLoading(true)
    try {
      const res: any = await request.post('/java/auth/login', values)
      setToken(res.data.token)
      setUser(res.data.user)
      message.success('登录成功')
      navigate('/dashboard')
    } catch (err: any) {
      const msg = err.response?.data?.message || err.message || '登录失败'
      message.error(msg)
    } finally {
      setLoading(false)
    }
  }

  const handleRegister = async (values: { username: string; password: string; email?: string }) => {
    setLoading(true)
    try {
      await request.post('/java/auth/register', values)
      message.success('注册成功，请登录')
      setActiveTab('login')
      loginForm.setFieldsValue({ username: values.username, password: '' })
      registerForm.resetFields()
    } catch (err: any) {
      const msg = err.response?.data?.message || err.message || '注册失败'
      message.error(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #0f172a 0%, #1e1b4b 30%, #312e81 60%, #4338ca 100%)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Animated background blobs */}
      <div
        style={{
          position: 'absolute',
          top: -120,
          right: -80,
          width: 500,
          height: 500,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(99,102,241,0.3) 0%, transparent 70%)',
          animation: 'pulse 8s ease-in-out infinite',
        }}
      />
      <div
        style={{
          position: 'absolute',
          bottom: -100,
          left: -60,
          width: 400,
          height: 400,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(129,140,248,0.2) 0%, transparent 70%)',
          animation: 'pulse 10s ease-in-out infinite alternate',
        }}
      />

      {/* Floating particles */}
      {[...Array(6)].map((_, i) => (
        <div
          key={i}
          style={{
            position: 'absolute',
            width: 4 + Math.random() * 6,
            height: 4 + Math.random() * 6,
            borderRadius: '50%',
            background: 'rgba(255,255,255,0.3)',
            top: `${15 + Math.random() * 70}%`,
            left: `${5 + Math.random() * 90}%`,
            animation: `float ${3 + Math.random() * 5}s ease-in-out infinite`,
            animationDelay: `${Math.random() * 3}s`,
          }}
        />
      ))}

      <Card
        style={{
          width: 440,
          borderRadius: 20,
          background: 'rgba(255,255,255,0.95)',
          backdropFilter: 'blur(20px)',
          boxShadow: '0 25px 60px rgba(0,0,0,0.25), 0 0 0 1px rgba(255,255,255,0.1)',
          border: 'none',
        }}
        bodyStyle={{ padding: '40px 36px' }}
      >
        {/* Logo header */}
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: 16,
              background: 'linear-gradient(135deg, #818cf8, #6366f1)',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 8px 24px rgba(99,102,241,0.35)',
              marginBottom: 16,
            }}
          >
            <ThunderboltOutlined style={{ color: '#fff', fontSize: 28 }} />
          </div>
          <Title level={3} style={{ margin: 0, color: '#1e1b4b', fontWeight: 700 }}>
            NexusAI
          </Title>
          <Text type="secondary" style={{ fontSize: 13 }}>
            AI 驱动的内容聚合与智能分析平台
          </Text>
        </div>

        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          centered
          size="large"
          style={{ marginBottom: 8 }}
          items={[
            {
              key: 'login',
              label: '登录',
              children: (
                <Form form={loginForm} layout="vertical" onFinish={handleLogin} size="large">
                  <Form.Item
                    name="username"
                    rules={[{ required: true, message: '请输入用户名' }]}
                  >
                    <Input
                      prefix={<UserOutlined style={{ color: '#94a3b8' }} />}
                      placeholder="用户名"
                    />
                  </Form.Item>
                  <Form.Item
                    name="password"
                    rules={[{ required: true, message: '请输入密码' }]}
                  >
                    <Input.Password
                      prefix={<LockOutlined style={{ color: '#94a3b8' }} />}
                      placeholder="密码"
                    />
                  </Form.Item>
                  <Form.Item style={{ marginBottom: 0 }}>
                    <Button
                      type="primary"
                      htmlType="submit"
                      block
                      loading={loading}
                      style={{
                        height: 44,
                        borderRadius: 10,
                        fontWeight: 600,
                        fontSize: 15,
                      }}
                    >
                      登 录
                    </Button>
                  </Form.Item>
                </Form>
              ),
            },
            {
              key: 'register',
              label: '注册',
              children: (
                <Form form={registerForm} layout="vertical" onFinish={handleRegister} size="large">
                  <Form.Item
                    name="username"
                    rules={[{ required: true, message: '请输入用户名' }]}
                  >
                    <Input
                      prefix={<UserOutlined style={{ color: '#94a3b8' }} />}
                      placeholder="用户名"
                    />
                  </Form.Item>
                  <Form.Item name="email">
                    <Input
                      prefix={<MailOutlined style={{ color: '#94a3b8' }} />}
                      placeholder="邮箱（可选）"
                    />
                  </Form.Item>
                  <Form.Item
                    name="password"
                    rules={[{ required: true, min: 6, message: '密码至少6位' }]}
                  >
                    <Input.Password
                      prefix={<LockOutlined style={{ color: '#94a3b8' }} />}
                      placeholder="密码"
                    />
                  </Form.Item>
                  <Form.Item style={{ marginBottom: 0 }}>
                    <Button
                      type="primary"
                      htmlType="submit"
                      block
                      loading={loading}
                      style={{
                        height: 44,
                        borderRadius: 10,
                        fontWeight: 600,
                        fontSize: 15,
                      }}
                    >
                      注 册
                    </Button>
                  </Form.Item>
                </Form>
              ),
            },
          ]}
        />
      </Card>

      {/* CSS animations */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.6; transform: scale(1); }
          50% { opacity: 0.3; transform: scale(1.15); }
        }
        @keyframes float {
          0%, 100% { transform: translateY(0); opacity: 0.2; }
          50% { transform: translateY(-20px); opacity: 0.6; }
        }
      `}</style>
    </div>
  )
}

export default Login
