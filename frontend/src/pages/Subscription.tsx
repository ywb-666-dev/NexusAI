import { useEffect, useState } from 'react'
import { Table, Button, Tag, Modal, Form, Input, Select, Space, Popconfirm, Typography, Alert, List } from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  PauseCircleOutlined,
  SearchOutlined,
  LoadingOutlined,
  BulbOutlined,
  LinkOutlined,
  ApiOutlined,
  GlobalOutlined,
} from '@ant-design/icons'
import request from '../api/request'
import { App } from 'antd'

const { Title, Text } = Typography

interface DiscoveredSource {
  url: string
  name: string
  platform: string
}

interface DiscoveryResult {
  topic: string
  keywords: string[]
  suggested_name: string
  rss_urls: string[]
  web_sources: string[]
  api_sources: string[]
  recommended_platforms: string[]
  total_sources: number
  sources?: DiscoveredSource[]
}

const platformIcon: Record<string, React.ReactNode> = {
  rss: <LinkOutlined />,
  web: <GlobalOutlined />,
  api: <ApiOutlined />,
}

const platformColor: Record<string, string> = {
  rss: '#f59e0b',
  web: '#6366f1',
  api: '#10b981',
}

function SubscriptionPage() {
  const { message } = App.useApp()
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<any>(null)
  const [form] = Form.useForm()

  // AI discovery state
  const [discovering, setDiscovering] = useState(false)
  const [discoveryResult, setDiscoveryResult] = useState<DiscoveryResult | null>(null)
  const [discoveryApplied, setDiscoveryApplied] = useState(false)

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
    setDiscoveryResult(null)
    setDiscoveryApplied(false)
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
    setDiscoveryResult(null)
    setDiscoveryApplied(false)
    setModalOpen(true)
  }

  const handleDiscover = async () => {
    const name = form.getFieldValue('name') || ''
    const keywords = form.getFieldValue('keywords') || ''

    if (!name && !keywords) {
      message.warning('请先输入主题名称或关键词')
      return
    }

    // 从关键词字段和名称中提取关键词
    const kwList = keywords
      ? keywords.split(/[,;，；]\s*/).map((s: string) => s.trim()).filter(Boolean)
      : []
    // 也把名称中的词加进去
    const nameWords = name.replace(/[动态监控采集\s]+/g, ',').split(/[,;，；]\s*/).filter(Boolean)
    const allKw = [...new Set([...kwList, ...nameWords])]

    setDiscovering(true)
    setDiscoveryResult(null)
    setDiscoveryApplied(false)

    try {
      const res: any = await request.post('/python/subscriptions/discover-sources', {
        topic: name,
        keywords: allKw,
      })
      const d = res.data as DiscoveryResult
      setDiscoveryResult(d)

      if (d.total_sources === 0) {
        message.info('未找到匹配的源，请尝试更具体的关键词')
      } else {
        message.success(`AI 发现 ${d.total_sources} 个推荐源`)
      }
    } catch (err: any) {
      message.error(err.response?.data?.message || '发现源失败，请稍后重试')
    } finally {
      setDiscovering(false)
    }
  }

  const applyDiscovery = () => {
    if (!discoveryResult) return

    // 合并关键词
    const currentKw = form.getFieldValue('keywords') || ''
    const currentKwList = currentKw
      ? currentKw.split(/[,;，；]\s*/).map((s: string) => s.trim()).filter(Boolean)
      : []
    const mergedKeywords = [...new Set([...currentKwList, ...discoveryResult.rss_urls])]

    // 合并平台
    const currentPlat = form.getFieldValue('sourcePlatforms') || ''
    const currentPlatList = currentPlat
      ? currentPlat.split(/[,;，；]\s*/).map((s: string) => s.trim()).filter(Boolean)
      : []
    const mergedPlatforms = [...new Set([...currentPlatList, ...discoveryResult.recommended_platforms])]

    form.setFieldsValue({
      name: form.getFieldValue('name') || discoveryResult.suggested_name,
      keywords: mergedKeywords.join(', '),
      sourcePlatforms: mergedPlatforms.join(', '),
    })
    setDiscoveryApplied(true)
    message.success('已应用 AI 发现的源到表单')
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
      message.success('采集触发成功')
    } catch (err: any) {
      message.error(err.response?.data?.message || err.message)
    }
  }

  useEffect(() => { fetchData() }, [])

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    {
      title: '名称',
      dataIndex: 'name',
      render: (v: string) => <span style={{ fontWeight: 600 }}>{v}</span>,
    },
    {
      title: '关键词',
      dataIndex: 'keywords',
      render: (v: any) => {
        const list = Array.isArray(v) ? v : []
        return list.length > 0 ? (
          <Space size={4} wrap>
            {list.slice(0, 3).map((k: string, i: number) => (
              <Tag key={i} style={{ borderRadius: 6, background: '#f0f0ff', color: '#6366f1', border: 'none' }}>
                {k}
              </Tag>
            ))}
            {list.length > 3 && <Tag style={{ borderRadius: 6 }}>+{list.length - 3}</Tag>}
          </Space>
        ) : '-'
      },
    },
    {
      title: '平台',
      dataIndex: 'sourcePlatforms',
      width: 120,
      render: (v: any) => {
        const list = Array.isArray(v) ? v : []
        return list.length > 0 ? list.join(' / ') : '-'
      },
    },
    {
      title: '匹配',
      dataIndex: 'matchMode',
      width: 80,
      render: (v: number) => (
        <Tag style={{ borderRadius: 6 }}>{v === 1 ? '精确' : v === 2 ? '模糊' : '语义'}</Tag>
      ),
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      width: 80,
      render: (v: number) =>
        v === 1 ? (
          <Tag color="error" style={{ borderRadius: 6 }}>高</Tag>
        ) : v === 2 ? (
          <Tag color="warning" style={{ borderRadius: 6 }}>中</Tag>
        ) : (
          <Tag style={{ borderRadius: 6 }}>低</Tag>
        ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      render: (v: number) =>
        v === 1 ? (
          <Tag icon={<CheckCircleOutlined />} color="success" style={{ borderRadius: 6 }}>启用</Tag>
        ) : (
          <Tag icon={<PauseCircleOutlined />} style={{ borderRadius: 6 }}>暂停</Tag>
        ),
    },
    {
      title: '定时',
      dataIndex: 'cronExpression',
      width: 100,
      render: (v: string) =>
        v ? (
          <Tag icon={<ClockCircleOutlined />} style={{ borderRadius: 6, fontSize: 12 }}>
            {v}
          </Tag>
        ) : (
          <Text style={{ color: '#cbd5e1' }}>手动</Text>
        ),
    },
    {
      title: '操作',
      width: 220,
      render: (_: any, record: any) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<ThunderboltOutlined />}
            onClick={() => trigger(record.id)}
            style={{ color: '#6366f1' }}
          >
            触发
          </Button>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => openEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定删除？"
            description="删除后无法恢复"
            onConfirm={() => handleDelete(record.id)}
            okButtonProps={{ danger: true }}
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
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
        <Title level={4} style={{ margin: 0, fontWeight: 700 }}>订阅管理</Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={openCreate}
          style={{ borderRadius: 8, height: 38 }}
        >
          创建订阅
        </Button>
      </div>

      <Table
        rowKey="id"
        columns={columns}
        dataSource={data}
        loading={loading}
        pagination={{ pageSize: 15, showTotal: (t) => `共 ${t} 条规则` }}
        style={{ borderRadius: 12, overflow: 'hidden' }}
      />

      <Modal
        title={
          <span style={{ fontWeight: 600 }}>
            {editing ? '编辑订阅规则' : '创建订阅规则'}
          </span>
        }
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => { setModalOpen(false); setDiscoveryResult(null) }}
        destroyOnClose
        width={620}
        okText={editing ? '保存' : '创建'}
        cancelText="取消"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="规则名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="如：AI行业动态" style={{ borderRadius: 8 }} />
          </Form.Item>

          {/* 关键词 + AI 发现按钮 */}
          <Form.Item label="关键词 / RSS URL（逗号分隔）">
            <Space.Compact style={{ width: '100%' }}>
              <Form.Item noStyle name="keywords">
                <Input placeholder="如：LLM, Agent, RAG 或 https://..." style={{ borderRadius: '8px 0 0 8px' }} />
              </Form.Item>
              <Button
                icon={discovering ? <LoadingOutlined spin /> : <BulbOutlined />}
                onClick={handleDiscover}
                loading={discovering}
                style={{
                  borderRadius: '0 8px 8px 0',
                  background: 'linear-gradient(135deg, #818cf8, #6366f1)',
                  border: 'none',
                  color: '#fff',
                  fontWeight: 500,
                }}
              >
                AI 发现源
              </Button>
            </Space.Compact>
          </Form.Item>

          {/* 发现结果展示 */}
          {discoveryResult && (
            <div
              style={{
                background: 'linear-gradient(135deg, #f0f0ff, #faf5ff)',
                borderRadius: 12,
                padding: '16px 18px',
                marginBottom: 16,
                border: '1px solid #e0d7fe',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                <span style={{ fontWeight: 600, color: '#4338ca', fontSize: 14 }}>
                  <BulbOutlined style={{ marginRight: 6 }} />
                  AI 发现 {discoveryResult.total_sources} 个推荐源
                </span>
                {!discoveryApplied && (
                  <Button
                    size="small"
                    type="primary"
                    onClick={applyDiscovery}
                    style={{
                      borderRadius: 6,
                      background: '#6366f1',
                      border: 'none',
                    }}
                  >
                    应用到表单
                  </Button>
                )}
                {discoveryApplied && (
                  <Tag color="success" style={{ borderRadius: 6 }}>已应用</Tag>
                )}
              </div>

              {/* RSS 源列表 */}
              {discoveryResult.rss_urls.length > 0 && (
                <div style={{ marginBottom: 8 }}>
                  <Text strong style={{ fontSize: 12, color: '#64748b' }}>
                    <LinkOutlined style={{ marginRight: 4 }} /> RSS 源 ({discoveryResult.rss_urls.length})
                  </Text>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 4 }}>
                    {discoveryResult.rss_urls.slice(0, 5).map((url, i) => (
                      <Tag
                        key={i}
                        style={{
                          borderRadius: 6,
                          background: '#fef9c3',
                          color: '#92400e',
                          border: 'none',
                          fontSize: 11,
                          maxWidth: 280,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                        }}
                        title={url}
                      >
                        {url.length > 40 ? url.slice(0, 40) + '...' : url}
                      </Tag>
                    ))}
                    {discoveryResult.rss_urls.length > 5 && (
                      <Tag style={{ borderRadius: 6, fontSize: 11 }}>
                        +{discoveryResult.rss_urls.length - 5} 更多
                      </Tag>
                    )}
                  </div>
                </div>
              )}

              {/* 推荐平台 */}
              {discoveryResult.recommended_platforms.length > 0 && (
                <div>
                  <Text strong style={{ fontSize: 12, color: '#64748b' }}>
                    推荐平台：
                  </Text>
                  {discoveryResult.recommended_platforms.map((p) => (
                    <Tag
                      key={p}
                      icon={platformIcon[p] || <GlobalOutlined />}
                      color={platformColor[p] || 'default'}
                      style={{ borderRadius: 6, marginLeft: 4 }}
                    >
                      {p}
                    </Tag>
                  ))}
                </div>
              )}
            </div>
          )}

          <Form.Item name="sourcePlatforms" label="来源平台（逗号分隔）">
            <Input placeholder="如：rss, web, api" style={{ borderRadius: 8 }} />
          </Form.Item>
          <Space size="middle">
            <Form.Item name="matchMode" label="匹配模式">
              <Select style={{ width: 120 }}>
                <Select.Option value={1}>精确匹配</Select.Option>
                <Select.Option value={2}>模糊匹配</Select.Option>
                <Select.Option value={3}>语义匹配</Select.Option>
              </Select>
            </Form.Item>
            <Form.Item name="priority" label="优先级">
              <Select style={{ width: 100 }}>
                <Select.Option value={1}>高</Select.Option>
                <Select.Option value={2}>中</Select.Option>
                <Select.Option value={3}>低</Select.Option>
              </Select>
            </Form.Item>
          </Space>
          <Form.Item name="cronExpression" label="定时表达式（可选）">
            <Input placeholder="如：0 */2 * * *，留空则为手动触发" style={{ borderRadius: 8 }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default SubscriptionPage
