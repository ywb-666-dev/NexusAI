import { useEffect, useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, Badge, Avatar, Dropdown, Breadcrumb, Typography } from 'antd'
import {
  DashboardOutlined,
  UnorderedListOutlined,
  FileTextOutlined,
  CheckSquareOutlined,
  BellOutlined,
  LogoutOutlined,
  UserOutlined,
  ApartmentOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import { useAuthStore } from '../store/auth'
import request from '../api/request'

const { Header, Sider, Content } = Layout
const { Text } = Typography

const menuItems = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: '仪表盘' },
  { key: '/subscriptions', icon: <UnorderedListOutlined />, label: '订阅管理' },
  { key: '/contents', icon: <FileTextOutlined />, label: '内容中心' },
  { key: '/approvals', icon: <CheckSquareOutlined />, label: '审批工单' },
  { key: '/notifications', icon: <BellOutlined />, label: '通知中心' },
  { key: '/agent-monitor', icon: <ApartmentOutlined />, label: 'Agent监控' },
]

const breadcrumbMap: Record<string, string> = {
  '/dashboard': '仪表盘',
  '/subscriptions': '订阅管理',
  '/contents': '内容中心',
  '/approvals': '审批工单',
  '/notifications': '通知中心',
  '/agent-monitor': 'Agent监控',
}

function BasicLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuthStore()
  const [unreadCount, setUnreadCount] = useState(0)

  useEffect(() => {
    const fetchUnread = async () => {
      try {
        const res: any = await request.get('/java/notifications/unread-count')
        setUnreadCount(res.data ?? 0)
      } catch { /* ignore */ }
    }
    fetchUnread()
    const timer = setInterval(fetchUnread, 30000)
    return () => clearInterval(timer)
  }, [])

  const breadcrumbItems = [
    { title: '首页', path: '/dashboard' },
    ...(location.pathname !== '/dashboard'
      ? [{ title: breadcrumbMap[location.pathname] || location.pathname, path: location.pathname }]
      : []),
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        width={220}
        style={{
          background: 'linear-gradient(180deg, #1e1b4b 0%, #312e81 100%)',
          boxShadow: '4px 0 24px rgba(30,27,75,0.12)',
        }}
      >
        <div
          style={{
            height: 72,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 10,
            borderBottom: '1px solid rgba(255,255,255,0.08)',
            margin: '0 16px',
          }}
        >
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 10,
              background: 'linear-gradient(135deg, #818cf8, #6366f1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 4px 12px rgba(99,102,241,0.4)',
            }}
          >
            <ThunderboltOutlined style={{ color: '#fff', fontSize: 18 }} />
          </div>
          <span style={{ color: '#fff', fontWeight: 700, fontSize: 20, letterSpacing: 1 }}>
            NexusAI
          </span>
        </div>

        <Menu
          mode="inline"
          theme="dark"
          selectedKeys={[location.pathname]}
          style={{
            background: 'transparent',
            borderInlineEnd: 'none',
            marginTop: 8,
            padding: '0 8px',
          }}
          items={menuItems.map((item) => ({
            ...item,
            label: item.key === '/notifications' && unreadCount > 0 ? (
              <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                {item.label}
                <Badge
                  count={unreadCount}
                  size="small"
                  style={{ boxShadow: 'none' }}
                />
              </span>
            ) : item.label,
          }))}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>

      <Layout>
        <Header
          style={{
            background: '#fff',
            padding: '0 28px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid #f1f5f9',
            boxShadow: '0 1px 4px rgba(0,0,0,0.03)',
            height: 56,
          }}
        >
          <Breadcrumb
            items={breadcrumbItems.map((b) => ({
              title: (
                <a
                  style={{ cursor: 'pointer', color: '#6366f1' }}
                  onClick={() => b.path !== location.pathname && navigate(b.path)}
                >
                  {b.title}
                </a>
              ),
            }))}
          />

          <Dropdown
            menu={{
              items: [
                {
                  key: 'user-info',
                  label: (
                    <div style={{ padding: '4px 0', cursor: 'default' }}>
                      <div style={{ fontWeight: 600 }}>{user?.username || '访客'}</div>
                      <Text type="secondary" style={{ fontSize: 12 }}>{user?.role || ''}</Text>
                    </div>
                  ),
                  disabled: true,
                },
                { type: 'divider' },
                { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: logout, danger: true },
              ],
            }}
            placement="bottomRight"
          >
            <div style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 10 }}>
              <Avatar
                icon={<UserOutlined />}
                style={{
                  background: 'linear-gradient(135deg, #818cf8, #6366f1)',
                  boxShadow: '0 2px 8px rgba(99,102,241,0.3)',
                }}
              />
              <span style={{ fontWeight: 500, color: '#334155' }}>{user?.username || '访客'}</span>
            </div>
          </Dropdown>
        </Header>

        <Content style={{ margin: 24, minHeight: 280 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}

export default BasicLayout
