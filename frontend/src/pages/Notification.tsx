import { useEffect, useState, useRef } from 'react'
import { List, Tag, Typography, Button, Space, message } from 'antd'
import { BellOutlined, CheckOutlined } from '@ant-design/icons'
import request from '../api/request'
import { useThemeStore } from '../store/theme'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import { timeAgo } from '../utils/time'
gsap.registerPlugin(useGSAP)
const { Title, Text } = Typography

export default function NotificationPage() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const dark = useThemeStore((s) => s.dark)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => { fetchData() }, [])
  const fetchData = async () => { setLoading(true); try { const r: any = await request.get('/java/notifications'); setData(r.data?.items ?? r.data?.records ?? []) } finally { setLoading(false) } }
  useGSAP(() => { gsap.from(ref.current, { y: 20, opacity: 0, duration: 0.45, ease: 'power2.out' }) }, { scope: ref })

  const markRead = async (id: number) => { try { await request.post('/java/notifications/' + id + '/read'); message.success('Marked read'); fetchData() } catch {} }
  const markAll = async () => { try { await request.post('/java/notifications/read-all'); message.success('All marked read'); fetchData() } catch {} }

  if (loading) {
    return (
      <div ref={ref}>
        <Skeleton.Input active style={{ width: 200, height: 28, marginBottom: 20 }} />
        {[0,1,2,3,4].map(i => (
          <Card key={i} style={{ borderRadius: 12, marginBottom: 8 }}>
            <Skeleton active paragraph={{ rows: 1 }} avatar />
          </Card>
        ))}
      </div>
    )
  }

  if (data.length === 0 && !loading) {
    return <div ref={ref} style={{ textAlign: 'center', padding: 80 }}>
      <BellOutlined style={{ fontSize: 56, color: '#cbd5e1', marginBottom: 16 }} />
      <div style={{ fontSize: 16, color: '#94a3b8', marginBottom: 8 }}>No notifications</div>
      <Text style={{ fontSize: 13, color: '#cbd5e1' }}>New notifications will appear here when content is collected or approved.</Text>
    </div>
  }
  return <div ref={ref}><div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}><Title level={4} style={{ margin: 0, fontWeight: 700, color: dark ? '#e2e8f0' : '#1e293b' }}>Notifications</Title><Button icon={<CheckOutlined />} onClick={markAll}>Mark All Read</Button></div><List loading={loading} dataSource={data} renderItem={(item: any) => <List.Item style={{ padding: '14px 20px', borderRadius: 12, marginBottom: 8, background: item.isRead ? (dark ? '#1a1a1a' : '#fff') : (dark ? '#1e1a3a' : '#f8faff'), border: '1px solid ' + (item.isRead ? '#f1f5f9' : '#e0e7ff') }}><List.Item.Meta avatar={<BellOutlined style={{ fontSize: 20, color: item.isRead ? '#94a3b8' : '#6366f1' }} />} title={<span style={{ fontWeight: item.isRead ? 400 : 600 }}>{item.title}</span>} description={<span><Text style={{ color: '#64748b' }}>{item.content}</Text><br /><Text style={{ fontSize: 11, color: '#94a3b8' }}>{timeAgo(item.createdAt)}</Text></span>} />{!item.isRead && <Button size='small' onClick={() => markRead(item.id)}>Read</Button>}</List.Item>} /></div>
}
