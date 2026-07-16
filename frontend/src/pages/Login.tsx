import { useState, useRef } from 'react'
import { Form, Input, Button, Card, Typography, Tabs, App } from 'antd'
import { UserOutlined, LockOutlined, MailOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/auth'
import request from '../api/request'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'

gsap.registerPlugin(useGSAP)
const { Title, Text } = Typography

export default function Login() {
  const [loading, setLoading] = useState(false)
  const [tab, setTab] = useState('login')
  const navigate = useNavigate()
  const { setToken, setUser } = useAuthStore()
  const { message } = App.useApp()
  const cardRef = useRef<HTMLDivElement>(null)

  useGSAP(() => { gsap.from(cardRef.current, { y: 40, autoAlpha: 0, duration: 0.7, ease: 'power3.out' }) }, { scope: cardRef })

  const onFinish = async (values: any) => {
    setLoading(true)
    try {
      const endpoint = tab === 'login' ? '/java/auth/login' : '/java/auth/register'
      const res: any = await request.post(endpoint, values)
      if (tab === 'login') {
        setToken(res.data.token); setUser(res.data.user); navigate('/dashboard')
      } else { message.success('Registered! Please login'); setTab('login') }
    } catch (err: any) { message.error(err.response?.data?.message || err.message || 'Failed') }
    finally { setLoading(false) }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #0f172a 100%)' }}>
      <Card ref={cardRef as any} style={{ width: 400, borderRadius: 16, border: 'none', boxShadow: '0 25px 60px rgba(0,0,0,0.3)' }} bodyStyle={{ padding: '32px 36px' }}>
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <div style={{ width: 52, height: 52, borderRadius: 14, background: 'linear-gradient(135deg, #818cf8, #4f46e5)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', marginBottom: 12 }}><ThunderboltOutlined style={{ color: '#fff', fontSize: 26 }} /></div>
          <Title level={3} style={{ margin: 0, fontWeight: 700 }}>NexusAI</Title>
          <Text style={{ color: '#94a3b8' }}>Agent-Powered Content Platform</Text>
        </div>
        <Tabs activeKey={tab} onChange={setTab} centered items={[{ key: 'login', label: 'Login' }, { key: 'register', label: 'Register' }]} />
        <Form onFinish={onFinish} layout='vertical' size='large'>
          <Form.Item name='username' rules={[{ required: true, message: 'Username required' }]}><Input prefix={<UserOutlined />} placeholder='Username' style={{ borderRadius: 10 }} /></Form.Item>
          {tab === 'register' && <Form.Item name='email' rules={[{ type: 'email', message: 'Valid email' }]}><Input prefix={<MailOutlined />} placeholder='Email' style={{ borderRadius: 10 }} /></Form.Item>}
          <Form.Item name='password' rules={[{ required: true, min: 6, message: 'Min 6 characters' }]}><Input.Password prefix={<LockOutlined />} placeholder='Password' style={{ borderRadius: 10 }} /></Form.Item>
          <Form.Item><Button type='primary' htmlType='submit' loading={loading} block style={{ borderRadius: 10, height: 44, background: 'linear-gradient(135deg, #818cf8, #4f46e5)', border: 'none', fontWeight: 600, fontSize: 15 }}>{tab === 'login' ? 'Sign In' : 'Sign Up'}</Button></Form.Item>
        </Form>
      </Card>
    </div>
  )
}
