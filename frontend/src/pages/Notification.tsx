import { useEffect, useState } from 'react'
import { Table, Button, Badge, message } from 'antd'
import { useAuthStore } from '../store/auth'
import request from '../api/request'

function NotificationPage() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const { user } = useAuthStore()

  const fetchData = async () => {
    if (!user?.id) return
    setLoading(true)
    try {
      const res: any = await request.get('/java/notifications', { params: { userId: user.id } })
      setData(res.data?.items || [])
    } finally {
      setLoading(false)
    }
  }

  const markRead = async (id: number) => {
    try {
      await request.post(`/java/notifications/${id}/read`)
      message.success('已标记为已读')
      fetchData()
    } catch (err: any) {
      message.error(err.message)
    }
  }

  const markAllRead = async () => {
    if (!user?.id) return
    try {
      await request.post('/java/notifications/read-all', {}, { params: { userId: user.id } })
      message.success('全部已读')
      fetchData()
    } catch (err: any) {
      message.error(err.message)
    }
  }

  useEffect(() => {
    fetchData()
  }, [user?.id])

  const columns = [
    { title: 'ID', dataIndex: 'id' },
    { title: '类型', dataIndex: 'type' },
    { title: '标题', dataIndex: 'title' },
    { title: '内容', dataIndex: 'content', ellipsis: true },
    {
      title: '状态',
      dataIndex: 'isRead',
      render: (v: number) => (v === 0 ? <Badge status="processing" text="未读" /> : <Badge status="default" text="已读" />),
    },
    {
      title: '操作',
      render: (_: any, record: any) =>
        record.isRead === 0 ? (
          <Button type="link" onClick={() => markRead(record.id)}>
            标记已读
          </Button>
        ) : null,
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>通知中心</h2>
        <Button onClick={markAllRead}>全部已读</Button>
      </div>
      <Table rowKey="id" columns={columns} dataSource={data} loading={loading} style={{ marginTop: 16 }} />
    </div>
  )
}

export default NotificationPage
