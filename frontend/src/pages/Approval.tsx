import { useEffect, useState, useRef } from 'react'
import { Table, Button, Tag, Typography, Space, Popconfirm, message, Skeleton } from 'antd'
import { CheckOutlined, CloseOutlined } from '@ant-design/icons'
import request from '../api/request'
import { useThemeStore } from '../store/theme'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
gsap.registerPlugin(useGSAP)
const { Title } = Typography

export default function ApprovalPage() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const dark = useThemeStore((s) => s.dark)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => { fetchData() }, [])
  const fetchData = async () => { setLoading(true); try { const r: any = await request.get('/java/approvals/pending'); setData(r.data?.items ?? r.data?.records ?? []) } finally { setLoading(false) } }
  useGSAP(() => { gsap.from(ref.current, { y: 20, opacity: 0, duration: 0.45, ease: 'power2.out' }) }, { scope: ref })

  const approve = async (id: number) => { try { await request.post('/java/approvals/' + id + '/approve'); message.success('Approved'); fetchData() } catch {} }
  const reject = async (id: number) => { try { await request.post('/java/approvals/' + id + '/reject'); message.success('Rejected'); fetchData() } catch {} }

  const cols = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: 'Task', dataIndex: 'taskId', ellipsis: true },
    { title: 'Type', dataIndex: 'actionType', width: 120 },
    { title: 'Risk', dataIndex: 'riskLevel', width: 80, render: (v: number) => v === 1 ? <Tag color='green' style={{ borderRadius: 6 }}>Low</Tag> : v === 2 ? <Tag color='orange' style={{ borderRadius: 6 }}>Med</Tag> : <Tag color='red' style={{ borderRadius: 6 }}>High</Tag> },
    { title: 'Status', dataIndex: 'status', width: 80, render: (v: number) => v === 0 ? <Tag color='processing' style={{ borderRadius: 6 }}>Pending</Tag> : v === 1 ? <Tag color='success' style={{ borderRadius: 6 }}>OK</Tag> : <Tag color='error' style={{ borderRadius: 6 }}>Rejected</Tag> },
    { title: 'Actions', width: 160, render: (_: any, r: any) => r.status === 0 ? <Space><Button type='primary' size='small' icon={<CheckOutlined />} onClick={() => approve(r.id)}>Approve</Button><Popconfirm title='Reject?' onConfirm={() => reject(r.id)}><Button size='small' danger icon={<CloseOutlined />}>Reject</Button></Popconfirm></Space> : '-' },
  ]
  if (loading) {
    return (
      <div ref={ref}>
        <Skeleton.Input active style={{ width: 200, height: 28, marginBottom: 20 }} />
        <Card style={{ borderRadius: 12 }}><Skeleton active paragraph={{ rows: 6 }} /></Card>
      </div>
    )
  }

  if (data.length === 0 && !loading) {
    return <div ref={ref} style={{ textAlign: 'center', padding: 80 }}>
      <CheckSquareOutlined style={{ fontSize: 56, color: '#cbd5e1', marginBottom: 16 }} />
      <div style={{ fontSize: 16, color: '#94a3b8', marginBottom: 8 }}>No pending approvals</div>
      <Text style={{ fontSize: 13, color: '#cbd5e1' }}>All content has been reviewed. Great work!</Text>
    </div>
  }
  return <div ref={ref}><Title level={4} style={{ marginBottom: 20, fontWeight: 700, color: dark ? '#e2e8f0' : '#1e293b' }}>Approvals</Title><Table rowKey='id' columns={cols} dataSource={data} loading={loading} pagination={{ pageSize: 15 }} style={{ borderRadius: 12, overflow: 'hidden' }} /></div>
}
