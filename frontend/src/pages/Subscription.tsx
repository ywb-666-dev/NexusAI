import { useEffect, useState } from 'react'
import { Table, Button, Tag, Modal, Form, Input, Select, Space, Popconfirm, message } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import request from '../api/request'

function SubscriptionPage() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<any>(null)
  const [form] = Form.useForm()

  const fetchData = async () => {
    setLoading(true)
    try {
      const res: any = await request.get('/java/subscriptions')
      setData(res.data?.items ?? res.data?.records ?? [])
    } finally {
      setLoading(false)
    }
  }

  const openCreate = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({ matchMode: 1, priority: 2 })
    setModalOpen(true)
  }

  const openEdit = (record: any) => {
    setEditing(record)
    form.setFieldsValue({
      name: record.name,
      matchMode: record.matchMode,
      priority: record.priority,
      cronExpression: record.cronExpression,
      keywords: Array.isArray(record.keywords) ? record.keywords.join(', ') : record.keywords,
      sourcePlatforms: Array.isArray(record.sourcePlatforms) ? record.sourcePlatforms.join(', ') : record.sourcePlatforms,
    })
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    const values = await form.validateFields()
    const payload = {
      ...values,
      keywords: values.keywords ? values.keywords.split(/[,;，；]\s*/).map((s: string) => s.trim()).filter(Boolean) : [],
      sourcePlatforms: values.sourcePlatforms ? values.sourcePlatforms.split(/[,;，；]\s*/).map((s: string) => s.trim()).filter(Boolean) : [],
    }
    try {
      if (editing) {
        await request.put(`/java/subscriptions/${editing.id}`, payload)
        message.success('更新成功')
      } else {
        await request.post('/java/subscriptions', payload)
        message.success('创建成功')
      }
      setModalOpen(false)
      fetchData()
    } catch (err: any) {
      message.error(err.response?.data?.message || err.message)
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await request.delete(`/java/subscriptions/${id}`)
      message.success('删除成功')
      fetchData()
    } catch (err: any) {
      message.error(err.response?.data?.message || err.message)
    }
  }

  const trigger = async (id: number) => {
    try {
      await request.post(`/java/subscriptions/${id}/trigger`)
      message.success('触发成功')
    } catch (err: any) {
      message.error(err.response?.data?.message || err.message)
    }
  }

  // re-fetch when page becomes visible (e.g. after login redirect)
  useEffect(() => {
    fetchData()
  }, [])

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '名称', dataIndex: 'name' },
    {
      title: '关键词',
      dataIndex: 'keywords',
      render: (v: any) => (Array.isArray(v) ? v.join(', ') : v ?? '-'),
    },
    {
      title: '平台',
      dataIndex: 'sourcePlatforms',
      render: (v: any) => (Array.isArray(v) ? v.join(', ') : v ?? '-'),
    },
    {
      title: '匹配模式',
      dataIndex: 'matchMode',
      render: (v: number) => (v === 1 ? '精确' : v === 2 ? '模糊' : '语义'),
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      render: (v: number) => (v === 1 ? <Tag color="red">高</Tag> : v === 2 ? <Tag color="orange">中</Tag> : <Tag>低</Tag>),
    },
    {
      title: '状态',
      dataIndex: 'status',
      render: (v: number) => (v === 1 ? <Tag color="green">启用</Tag> : <Tag>暂停</Tag>),
    },
    {
      title: '操作',
      width: 220,
      render: (_: any, record: any) => (
        <Space>
          <Button type="link" size="small" onClick={() => trigger(record.id)}>触发采集</Button>
          <Button type="link" size="small" onClick={() => openEdit(record)}>编辑</Button>
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>订阅管理</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>创建订阅</Button>
      </div>
      <Table rowKey="id" columns={columns} dataSource={data} loading={loading} style={{ marginTop: 16 }} />

      <Modal
        title={editing ? '编辑订阅' : '创建订阅'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="规则名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="如：AI行业动态" />
          </Form.Item>
          <Form.Item name="keywords" label="关键词（逗号分隔）">
            <Input placeholder="如：LLM, Agent, RAG" />
          </Form.Item>
          <Form.Item name="sourcePlatforms" label="来源平台（逗号分隔）">
            <Input placeholder="如：rss, web" />
          </Form.Item>
          <Form.Item name="matchMode" label="匹配模式">
            <Select>
              <Select.Option value={1}>精确</Select.Option>
              <Select.Option value={2}>模糊</Select.Option>
              <Select.Option value={3}>语义</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="priority" label="优先级">
            <Select>
              <Select.Option value={1}>高</Select.Option>
              <Select.Option value={2}>中</Select.Option>
              <Select.Option value={3}>低</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="cronExpression" label="定时表达式（可选）">
            <Input placeholder="如：0 0 8 * * ?" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default SubscriptionPage
