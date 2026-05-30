import { useEffect, useState } from 'react'
import { Table, Button, Tag, message, Popconfirm } from 'antd'
import request from '../api/request'

function SubscriptionPage() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  const fetchData = async () => {
    setLoading(true)
    try {
      const res: any = await request.get('/java/subscriptions')
      setData(res.data?.items || [])
    } finally {
      setLoading(false)
    }
  }

  const trigger = async (id: number) => {
    try {
      await request.post(`/java/subscriptions/${id}/trigger`)
      message.success('触发成功')
    } catch (err: any) {
      message.error(err.message)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const columns = [
    { title: 'ID', dataIndex: 'id' },
    { title: '名称', dataIndex: 'name' },
    { title: '匹配模式', dataIndex: 'matchMode', render: (v: number) => (v === 1 ? '精确' : v === 2 ? '模糊' : '语义') },
    { title: '优先级', dataIndex: 'priority', render: (v: number) => (v === 1 ? <Tag color="red">高</Tag> : v === 2 ? <Tag color="orange">中</Tag> : <Tag>低</Tag>) },
    { title: '状态', dataIndex: 'status', render: (v: number) => (v === 1 ? <Tag color="green">启用</Tag> : <Tag>暂停</Tag>) },
    {
      title: '操作',
      render: (_: any, record: any) => (
        <Button type="link" onClick={() => trigger(record.id)}>
          触发采集
        </Button>
      ),
    },
  ]

  return (
    <div>
      <h2>订阅管理</h2>
      <Table rowKey="id" columns={columns} dataSource={data} loading={loading} style={{ marginTop: 16 }} />
    </div>
  )
}

export default SubscriptionPage
