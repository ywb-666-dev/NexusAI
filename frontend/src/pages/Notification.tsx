import { useEffect, useState } from 'react'
import { Table, Button, Badge, Space, Tag, Typography, Tooltip } from 'antd'
import {
  CheckOutlined,
  MailOutlined,
  BellOutlined,
  InfoCircleOutlined,
  ClockCircleOutlined,
  ThunderboltOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import { useAuthStore } from '../store/auth'
import request from '../api/request'
import { App } from 'antd'

const { Title, Text } = Typography

const typeIcons: Record<string, React.ReactNode> = {
  task: <ThunderboltOutlined />,
  approval: <CheckOutlined />,
  system: <SettingOutlined />,
}

const typeColors: Record<string, string> = {
  task: '#818cf8',
  approval: '#34d399',
  system: '#fbbf24',
}

function NotificationPage() {
  const { message } = App.useApp()
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const { user } = useAuthStore()

  const fetchData = async () => {
    if (!user?.id) return
    setLoading(true)
    try {
      const res: any = await request.get('/java/notifications')
      setData(res.data?.records ?? res.data?.items ?? [])
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
      await request.post('/java/notifications/read-all')
      message.success('全部已读')
      fetchData()
    } catch (err: any) {
      message.error(err.message)
    }
  }

  useEffect(() => { fetchData() }, [user?.id])

  const unreadCount = data.filter((d) => d.isRead === 0).length

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    {
      title: '类型',
      dataIndex: 'type',
      width: 90,
      render: (v: string) => (
        <Tag
          icon={typeIcons[v] || <InfoCircleOutlined />}
          color={typeColors[v] || 'default'}
          style={{ borderRadius: 6, border: 'none' }}
        >
          {v === 'task' ? '任务' : v === 'approval' ? '审批' : v === 'system' ? '系统' : v}
        </Tag>
      ),
    },
    {
      title: '标题',
      dataIndex: 'title',
      render: (v: string, record: any) => (
        <Space>
          {record.isRead === 0 && <Badge status="processing" />}
          <span style={{ fontWeight: record.isRead === 0 ? 600 : 400 }}>{v}</span>
        </Space>
      ),
    },
    {
      title: '内容',
      dataIndex: 'content',
      ellipsis: true,
      render: (v: string) => (
        <Text style={{ color: '#64748b', maxWidth: 360 }} ellipsis>{v}</Text>
      ),
    },
    {
      title: '时间',
      dataIndex: 'createdAt',
      width: 170,
      render: (v: string) => (
        <Text style={{ color: '#94a3b8', fontSize: 13 }}>
          <ClockCircleOutlined style={{ marginRight: 6 }} />{v}
        </Text>
      ),
    },
    {
      title: '操作',
      width: 100,
      render: (_: any, record: any) =>
        record.isRead === 0 ? (
          <Button
            type="link"
            size="small"
            icon={<MailOutlined />}
            onClick={() => markRead(record.id)}
            style={{ color: '#6366f1' }}
          >
            已读
          </Button>
        ) : (
          <Text style={{ color: '#cbd5e1', fontSize: 13 }}>已读</Text>
        ),
    },
  ]

  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 20,
        }}
      >
        <div>
          <Title level={4} style={{ margin: 0, fontWeight: 700 }}>
            <BellOutlined style={{ marginRight: 8 }} />
            通知中心
          </Title>
          <Space style={{ marginTop: 8 }}>
            {unreadCount > 0 ? (
              <Tag color="processing" style={{ borderRadius: 6 }}>
                {unreadCount} 条未读
              </Tag>
            ) : (
              <Tag style={{ borderRadius: 6, color: '#94a3b8' }}>全部已读</Tag>
            )}
          </Space>
        </div>
        {unreadCount > 0 && (
          <Tooltip title="标记所有通知为已读">
            <Button
              icon={<CheckOutlined />}
              onClick={markAllRead}
              style={{ borderRadius: 8 }}
            >
              全部已读
            </Button>
          </Tooltip>
        )}
      </div>

      <Table
        rowKey="id"
        columns={columns}
        dataSource={data}
        loading={loading}
        pagination={{ pageSize: 15, showTotal: (t) => `共 ${t} 条通知` }}
        style={{ borderRadius: 12, overflow: 'hidden' }}
        locale={{ emptyText: '暂无通知' }}
        rowClassName={(record) => record.isRead === 0 ? '' : 'read-row'}
      />
    </div>
  )
}

export default NotificationPage
