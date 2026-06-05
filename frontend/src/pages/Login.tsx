import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Form, Input, Button, Tabs, message } from 'antd'
import { useAuthStore } from '../store/auth'
import request from '../api/request'

function Login() {
  const navigate = useNavigate()
  const { setToken, setUser } = useAuthStore()
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
    <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f0f2f5' }}>
      <Card style={{ width: 420 }}>
        <h2 style={{ textAlign: 'center', marginBottom: 24 }}>NexusAI</h2>
        <Tabs activeKey={activeTab} onChange={setActiveTab} centered>
          <Tabs.TabPane tab="登录" key="login">
            <Form form={loginForm} layout="vertical" onFinish={handleLogin}>
              <Form.Item label="用户名" name="username" rules={[{ required: true, message: '请输入用户名' }]}>
                <Input placeholder="请输入用户名" />
              </Form.Item>
              <Form.Item label="密码" name="password" rules={[{ required: true, message: '请输入密码' }]}>
                <Input.Password placeholder="请输入密码" />
              </Form.Item>
              <Form.Item>
                <Button type="primary" htmlType="submit" block loading={loading}>登录</Button>
              </Form.Item>
            </Form>
          </Tabs.TabPane>
          <Tabs.TabPane tab="注册" key="register">
            <Form form={registerForm} layout="vertical" onFinish={handleRegister}>
              <Form.Item label="用户名" name="username" rules={[{ required: true, message: '请输入用户名' }]}>
                <Input placeholder="请输入用户名" />
              </Form.Item>
              <Form.Item label="邮箱（可选）" name="email">
                <Input placeholder="请输入邮箱" />
              </Form.Item>
              <Form.Item label="密码" name="password" rules={[{ required: true, min: 6, message: '密码至少6位' }]}>
                <Input.Password placeholder="请输入密码" />
              </Form.Item>
              <Form.Item>
                <Button type="primary" htmlType="submit" block loading={loading}>注册</Button>
              </Form.Item>
            </Form>
          </Tabs.TabPane>
        </Tabs>
      </Card>
    </div>
  )
}

export default Login
