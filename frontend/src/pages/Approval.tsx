import { useEffect, useState } from 'react'
import { Table, Button, Tag, Modal, Input, Space, Typography, Tooltip } from 'antd'
import {
  CheckOutlined,
  CloseOutlined,
  SafetyOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons'
import request from '../api/request'
import { App } from 'antd'

const { Title, Text } = Typography

const riskColors: Record<number, string> = { 1: 'success', 2: 'warning', 3: 'error' }
const riskLabels: Record<number, string> = { 1: '低风险', 2: '中风险', 3: '高风险' }

function ApprovalPage() {
  const { message } = App.useApp()
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [rejectModal, setRejectModal] = useState<{ open: boolean; id: number | null }>({ open: false, id: null })
  const [rejectReason, setRejectReason] = useState('')

  const fetchData = async () => {
    setLoading(true)
    try {
      const res: any = await request.get('/java/approvals/pending')
      setData(res.data?.records ?? res.data?.items ?? [])
    } finally {
      setLoading(false)
    }
  }

  const handleApprove = async (id: number) => {
    try {
      await request.post(`/java/approvals/${id}/approve`, { comment: '' })
      message.success('已通过')
      fetchData()
    } catch (err: any) {
      message.error(err.message)
    }
  }

  const handleReject = async () => {
    const id = rejectModal.id
    if (!id) return
    try {
      await request.post(`/java/approvals/${id}/reject`, { comment: rejectReason })
      message.success('已拒绝')
      setRejectModal({ open: false, id: null })
      setRejectReason('')
      fetchData()
    } catch (err: any) {
      message.error(err.message)
    }
  }

  useEffect(() => { fetchData() }, [])

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    {
      title: '任务ID',
      dataIndex: 'taskId',
      render: (v: string) => <Text code>{v?.slice(0, 12)}...</Text>,
    },
    {
      title: '动作类型',
      dataIndex: 'actionType',
      render: (v: string) => (
        <Tag style={{ borderRadius: 6, border: 'none', background: '#f0f0ff', color: '#6366f1' }}>
          {v}
        </Tag>
      ),
    },
    {
      title: '风险等级',
      dataIndex: 'riskLevel',
      width: 100,
      render: (v: number) => (
        <Tag
          icon={v === 3 ? <ExclamationCircleOutlined /> : <SafetyOutlined />}
          color={riskColors[v]}
          style={{ borderRadius: 6 }}
        >
          {riskLabels[v] || `Level ${v}`}
        </Tag>
      ),
    },
    {
      title: '创建时间',
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
      width: 200,
      render: (_: any, record: any) => (
        <Space>
          <Button
            type="primary"
            size="small"
            icon={<CheckOutlined />}
            onClick={() => handleApprove(record.id)}
            style={{ borderRadius: 6 }}
          >
            通过
          </Button>
          <Button
            danger
            size="small"
            icon={<CloseOutlined />}
            onClick={() => { setRejectModal({ open: true, id: record.id }); setRejectReason('') }}
            style={{ borderRadius: 6 }}
          >
            拒绝
          </Button>
        </Space>
      ),
    },
  ]

  const highRiskCount = data.filter((d) => d.riskLevel === 3).length

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <Title level={4} style={{ margin: 0, fontWeight: 700 }}>审批工单</Title>
        <Space style={{ marginTop: 8 }}>
          <Tag style={{ borderRadius: 6 }}>
            <ClockCircleOutlined /> {data.length} 条待审批
          </Tag>
          {highRiskCount > 0 && (
            <Tag color="error" style={{ borderRadius: 6 }}>
              <ExclamationCircleOutlined /> {highRiskCount} 条高风险
            </Tag>
          )}
        </Space>
      </div>

      <Table
        rowKey="id"
        columns={columns}
        dataSource={data}
        loading={loading}
        pagination={{ pageSize: 15, showTotal: (t) => `共 ${t} 条工单` }}
        style={{ borderRadius: 12, overflow: 'hidden' }}
        locale={{ emptyText: '暂无待审批工单' }}
      />

      <Modal
        title={
          <Space>
            <ExclamationCircleOutlined style={{ color: '#f59e0b' }} />
            <span style={{ fontWeight: 600 }}>拒绝原因</span>
          </Space>
        }
        open={rejectModal.open}
        onOk={handleReject}
        onCancel={() => { setRejectModal({ open: false, id: null }); setRejectReason('') }}
        okText="确认拒绝"
        cancelText="取消"
        okButtonProps={{ danger: true }}
        destroyOnClose
      >
        <div
          style={{
            background: '#fef3c7',
            borderRadius: 8,
            padding: '10px 14px',
            marginBottom: 16,
            color: '#92400e',
            fontSize: 13,
          }}
        >
          此操作将拒绝该审批工单，相关任务将不会继续执行
        </div>
        <Input.TextArea
          rows={3}
          placeholder="请输入拒绝原因（选填）"
          value={rejectReason}
          onChange={(e) => setRejectReason(e.target.value)}
          style={{ borderRadius: 8 }}
        />
      </Modal>
    </div>
  )
}

export default ApprovalPage
