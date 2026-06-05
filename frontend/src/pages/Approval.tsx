import { useEffect, useState } from 'react'
import { Table, Button, Tag, message } from 'antd'
import request from '../api/request'

function ApprovalPage() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  const fetchData = async () => {
    setLoading(true)
    try {
      const res: any = await request.get('/java/approvals/pending')
      setData(res.data?.records ?? res.data?.items ?? [])
    } finally {
      setLoading(false)
    }
  }

  const handleAction = async (id: number, action: 'approve' | 'reject') => {
    try {
      await request.post(`/java/approvals/${id}/${action}`, { comment: '' })
      message.success(action === 'approve' ? '已通过' : '已拒绝')
      fetchData()
    } catch (err: any) {
      message.error(err.message)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const columns = [
    { title: 'ID', dataIndex: 'id' },
    { title: '任务ID', dataIndex: 'taskId' },
    { title: '动作类型', dataIndex: 'actionType' },
    {
      title: '风险等级',
      dataIndex: 'riskLevel',
      render: (v: number) =>
        v === 1 ? <Tag color="green">低</Tag> : v === 2 ? <Tag color="orange">中</Tag> : <Tag color="red">高</Tag>,
    },
    {
      title: '操作',
      render: (_: any, record: any) => (
        <>
          <Button type="link" onClick={() => handleAction(record.id, 'approve')}>
            通过
          </Button>
          <Button type="link" danger onClick={() => handleAction(record.id, 'reject')}>
            拒绝
          </Button>
        </>
      ),
    },
  ]

  return (
    <div>
      <h2>审批工单</h2>
      <Table rowKey="id" columns={columns} dataSource={data} loading={loading} style={{ marginTop: 16 }} />
    </div>
  )
}

export default ApprovalPage
