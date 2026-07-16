import { useEffect, useState, useRef } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, Badge, Avatar, Dropdown, Typography, Breadcrumb, Input, Button } from 'antd'
import {
  DashboardOutlined, UnorderedListOutlined, FileTextOutlined, CheckSquareOutlined,
  BellOutlined, LogoutOutlined, UserOutlined, ThunderboltOutlined, BulbOutlined,
  SearchOutlined, MenuFoldOutlined, MenuUnfoldOutlined,
} from '@ant-design/icons'
import { useAuthStore } from '../store/auth'
import { useThemeStore } from '../store/theme'
import request from '../api/request'
import gsap from 'gsap'
import { useGSAP } from '@gsap/react'

gsap.registerPlugin(useGSAP)

const { Header, Sider, Content } = Layout
const { Text } = Typography

const menuItems = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: 'Dashboard' },
  { key: '/subscriptions', icon: <UnorderedListOutlined />, label: 'Subscriptions' },
  { key: '/contents', icon: <FileTextOutlined />, label: 'Content' },
  { key: '/approvals', icon: <CheckSquareOutlined />, label: 'Approvals' },
  { key: '/notifications', icon: <BellOutlined />, label: 'Notifications' },
]

const breadcrumbMap: Record<string, string> = {
  '/dashboard': 'Dashboard', '/subscriptions': 'Subscriptions',
  '/contents': 'Content', '/approvals': 'Approvals',
  '/notifications': 'Notifications',
}

export default function BasicLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuthStore()
  const { dark, toggle } = useThemeStore()
  const [unreadCount, setUnreadCount] = useState(0)
  const [collapsed, setCollapsed] = useState(false)
  const [globalSearch, setGlobalSearch] = useState('')
  const container = useRef<HTMLDivElement>(null)
  const siderRef = useRef<HTMLDivElement>(null)
  const searchRef = useRef<any>(null)


  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') { e.preventDefault(); searchRef.current?.focus() }
      if (e.key === '/' && document.activeElement?.tagName !== 'INPUT' && document.activeElement?.tagName !== 'TEXTAREA') { e.preventDefault(); searchRef.current?.focus() }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  useEffect(() => {
    const f = async () => { try { const r: any = await request.get('/java/notifications/unread-count'); setUnreadCount(r.data ?? 0) } catch {} }
    f(); const t = setInterval(f, 30000); return () => clearInterval(t)
  }, [])

  useGSAP(() => { gsap.from(siderRef.current, { x: -60, opacity: 0, duration: 0.6, ease: 'power3.out' }) }, { scope: container })
  useGSAP(() => { gsap.from('.nexus-page', { y: 20, opacity: 0, duration: 0.4, ease: 'power2.out' }) }, [location.pathname])

  const handleGlobalSearch = () => {
    if (globalSearch.trim()) navigate('/contents?search=' + encodeURIComponent(globalSearch.trim()))
  }

  return (
    <Layout style={{ minHeight: '100vh' }} ref={container}>
      <Sider width={220} collapsedWidth={60} collapsible collapsed={collapsed} onCollapse={setCollapsed} trigger={null} ref={siderRef as any}
        style={{ background: 'linear-gradient(180deg, #0f172a 0%, #1e293b 100%)', boxShadow: '4px 0 24px rgba(0,0,0,0.2)' }}>
        <div style={{ height: 72, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, borderBottom: '1px solid rgba(255,255,255,0.06)', margin: '0 16px' }}>
          <div style={{ width: 38, height: 38, borderRadius: 12, background: 'linear-gradient(135deg, #818cf8, #4f46e5)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 16px rgba(99,102,241,0.4)' }}>
            <ThunderboltOutlined style={{ color: '#fff', fontSize: 20 }} />
          </div>
          {!collapsed && <span style={{ color: '#e2e8f0', fontWeight: 700, fontSize: 20, letterSpacing: 0.5 }}>NexusAI</span>}
        </div>
        <Menu mode='inline' theme='dark' selectedKeys={[location.pathname]}
          style={{ background: 'transparent', borderInlineEnd: 'none', marginTop: 8, padding: '0 8px' }}
          items={menuItems.map(item => ({
            ...item, className: 'menu-item',
            label: item.key === '/notifications' && unreadCount > 0 ? <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>{item.label}<Badge count={unreadCount} size='small' /></span> : item.label,
          }))}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{ background: dark ? '#141414' : '#fff', padding: '0 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: dark ? '1px solid #2a2a2a' : '1px solid #e2e8f0', height: 56 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <Button type='text' icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />} onClick={() => setCollapsed(!collapsed)} style={{ fontSize: 16 }} />
            <Breadcrumb items={[
              { title: <span style={{ color: '#6366f1', cursor: 'pointer' }} onClick={() => navigate('/dashboard')}>Home</span> },
              ...(location.pathname !== '/dashboard' ? [{ title: <span style={{ color: dark ? '#e2e8f0' : '#334155' }}>{breadcrumbMap[location.pathname] || location.pathname}</span> }] : []),
            ]} />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <Input ref={searchRef} prefix={<SearchOutlined />} placeholder='Ctrl+K to search...' value={globalSearch} onChange={e => setGlobalSearch(e.target.value)} onPressEnter={handleGlobalSearch} style={{ width: 220, borderRadius: 10 }} allowClear size='small' />
            <Dropdown menu={{ items: [
              { key: 'info', label: <div><div style={{ fontWeight: 600 }}>{user?.username || 'Guest'}</div><Text type='secondary' style={{ fontSize: 12 }}>{user?.role || ''}</Text></div>, disabled: true },
              { type: 'divider' },
              { key: 'theme', icon: <BulbOutlined />, label: dark ? 'Light Mode' : 'Dark Mode', onClick: toggle },
              { key: 'logout', icon: <LogoutOutlined />, label: 'Logout', onClick: logout, danger: true },
            ]}} placement='bottomRight'>
              <div style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 10 }}>
                <Avatar icon={<UserOutlined />} style={{ background: 'linear-gradient(135deg, #818cf8, #4f46e5)' }} />
                <span style={{ fontWeight: 500, color: dark ? '#e2e8f0' : '#1e293b' }}>{user?.username || 'Guest'}</span>
              </div>
            </Dropdown>
          </div>
        </Header>
        <Content style={{ margin: 24, minHeight: 280 }}>
          <div className='nexus-page'><Outlet /></div>
        </Content>
      </Layout>
    </Layout>
  )
}
