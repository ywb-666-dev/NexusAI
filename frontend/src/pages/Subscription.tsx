import { useEffect, useState } from 'react'
import { Table, Button, Tag, Modal, Form, Input, Select, Space, Popconfirm, Typography, Steps, Checkbox, Collapse, Empty } from 'antd'
import {
  PlusOutlined, EditOutlined, DeleteOutlined, ThunderboltOutlined,
  ClockCircleOutlined, CheckCircleOutlined, PauseCircleOutlined, SearchOutlined,
  LoadingOutlined, BulbOutlined, LinkOutlined, ApiOutlined, GlobalOutlined,
  ArrowLeftOutlined, ArrowRightOutlined, CheckOutlined,
} from '@ant-design/icons'
import request from '../api/request'
import { App } from 'antd'

const { Title, Text } = Typography

const platformIcon: Record<string, any> = { rss: null, web: null, api: null }
const platformIconEl: Record<string, any> = { rss: 'link', web: 'global', api: 'api' }
const platformColor: Record<string, string> = { rss: '#f59e0b', web: '#6366f1', api: '#10b981' }
const sourceTypeLabel: Record<string, { label: string; color: string }> = {
  builtin: { label: 'Built-in', color: '#10b981' },
  web_search: { label: 'Web', color: '#6366f1' },
  llm: { label: 'AI', color: '#f59e0b' },
}

function SubscriptionPage() {
  const { message } = App.useApp()
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<any>(null)
  const [form] = Form.useForm()
  const [wizardStep, setWizardStep] = useState(0)
  const [interestInput, setInterestInput] = useState('')
  const [discovering, setDiscovering] = useState(false)
  const [discoveryResult, setDiscoveryResult] = useState<any>(null)
  const [selectedSourceIds, setSelectedSourceIds] = useState<string[]>([])
  const [creating, setCreating] = useState(false)

  const fetchData = async () => {
    setLoading(true)
    try {
      const res: any = await request.get('/java/subscriptions')
      setData(res.data?.items ?? res.data?.records ?? [])
    } finally { setLoading(false) }
  }

  const openCreate = () => {
    setEditing(null); form.resetFields(); form.setFieldsValue({ matchMode: 1, priority: 2 })
    setWizardStep(0); setInterestInput(''); setDiscoveryResult(null); setSelectedSourceIds([])
    setCreating(false); setModalOpen(true)
  }

  const openEdit = (record: any) => {
    setEditing(record)
    form.setFieldsValue({
      name: record.name, matchMode: record.matchMode, priority: record.priority,
      cronExpression: record.cronExpression,
      keywords: Array.isArray(record.keywords) ? record.keywords.join(', ') : record.keywords,
      sourcePlatforms: Array.isArray(record.sourcePlatforms) ? record.sourcePlatforms.join(', ') : record.sourcePlatforms,
    })
    setModalOpen(true)
  }

  const handleDiscover = async () => {
    if (!interestInput.trim()) { message.warning('Please describe what you want to follow'); return }
    setDiscovering(true); setDiscoveryResult(null); setSelectedSourceIds([])
    try {
      const res: any = await request.post('/python/subscriptions/discover-sources', { topic: interestInput.trim(), keywords: [] })
      const d = res.data
      if (!d.sources || d.sources.length === 0) { message.info('No matching sources found') }
      setDiscoveryResult(d)
      setSelectedSourceIds((d.sources || []).map((s: any) => s.id))
      setWizardStep(1)
    } catch (err: any) {
      message.error(err.response?.data?.message || err.message || 'Search failed')
    } finally { setDiscovering(false) }
  }

  const toggleSource = (id: string) => {
    setSelectedSourceIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])
  }

  const selectAll = () => { if (discoveryResult) setSelectedSourceIds(discoveryResult.sources.map((s: any) => s.id)) }
  const deselectAll = () => { setSelectedSourceIds([]) }

  const handleCreate = async () => {
    if (!discoveryResult) return
    const selectedSources = (discoveryResult.sources || []).filter((s: any) => selectedSourceIds.includes(s.id))
    const rssFeeds = selectedSources.map((s: any) => ({ url: s.url, name: s.name, platform: s.platform }))
    const advValues = form.getFieldsValue()
    const payload = {
      name: advValues.name || discoveryResult.suggested_name || interestInput.trim(),
      keywords: discoveryResult.keywords || [],
      sourcePlatforms: discoveryResult.recommended_platforms || ['rss'],
      rssFeeds, matchMode: advValues.matchMode ?? 1, priority: advValues.priority ?? 2,
      cronExpression: advValues.cronExpression || null,
    }
    setCreating(true)
    try {
      await request.post('/java/subscriptions', payload)
      message.success('Subscription created'); setModalOpen(false); fetchData()
    } catch (err: any) { message.error(err.response?.data?.message || 'Creation failed') }
    finally { setCreating(false) }
  }

  const handleSubmit = async () => {
    const values = await form.validateFields()
    const payload = {
      ...values,
      keywords: values.keywords ? values.keywords.split(/[,;,\uFF0C,\uFF1B]\s*/).map((s: string) => s.trim()).filter(Boolean) : [],
      sourcePlatforms: values.sourcePlatforms ? values.sourcePlatforms.split(/[,;,\uFF0C,\uFF1B]\s*/).map((s: string) => s.trim()).filter(Boolean) : [],
      rssFeeds: editing?.rssFeeds ?? [],
    }
    try {
      if (editing) { await request.put('/java/subscriptions/' + editing.id, payload); message.success('Updated') }
      else { await request.post('/java/subscriptions', payload); message.success('Created') }
      setModalOpen(false); fetchData()
    } catch (err: any) { message.error(err.response?.data?.message || err.message) }
  }

  const handleDelete = async (id: number) => {
    try { await request.delete('/java/subscriptions/' + id); message.success('Deleted'); fetchData() }
    catch (err: any) { message.error(err.response?.data?.message || err.message) }
  }

  const trigger = async (id: number) => {
    try { await request.post('/java/subscriptions/' + id + '/trigger'); message.success('Triggered') }
    catch (err: any) { message.error(err.response?.data?.message || err.message) }
  }

  useEffect(() => { fetchData() }, [])

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: 'Name', dataIndex: 'name', render: (v: string) => <span style={{ fontWeight: 600 }}>{v}</span> },
    {
      title: 'Keywords', dataIndex: 'keywords',
      render: (v: any) => {
        const list = Array.isArray(v) ? v : []
        return list.length > 0 ? (
          <Space size={4} wrap>
            {list.slice(0, 3).map((k: string, i: number) => <Tag key={i} style={{ borderRadius: 6, background: '#f0f0ff', color: '#6366f1', border: 'none' }}>{k}</Tag>)}
            {list.length > 3 && <Tag style={{ borderRadius: 6 }}>+{list.length - 3}</Tag>}
          </Space>
        ) : '-'
      },
    },
    { title: 'RSS Feeds', dataIndex: 'rssFeeds', width: 100,
      render: (v: any) => {
        const list = Array.isArray(v) ? v : []
        return list.length > 0 ? <Tag color='orange' style={{ borderRadius: 6 }}>{list.length} sources</Tag> : <Text style={{ color: '#cbd5e1' }}>-</Text>
      },
    },
    { title: 'Platforms', dataIndex: 'sourcePlatforms', width: 100,
      render: (v: any) => { const list = Array.isArray(v) ? v : []; return list.length > 0 ? list.join(' / ') : '-' },
    },
    { title: 'Match', dataIndex: 'matchMode', width: 80, render: (v: number) => <Tag style={{ borderRadius: 6 }}>{v === 1 ? 'Exact' : v === 2 ? 'Fuzzy' : 'Semantic'}</Tag> },
    { title: 'Priority', dataIndex: 'priority', width: 80,
      render: (v: number) => v === 1 ? <Tag color='error' style={{ borderRadius: 6 }}>High</Tag> : v === 2 ? <Tag color='warning' style={{ borderRadius: 6 }}>Medium</Tag> : <Tag style={{ borderRadius: 6 }}>Low</Tag>,
    },
    { title: 'Status', dataIndex: 'status', width: 80,
      render: (v: number) => v === 1 ? <Tag icon={<CheckCircleOutlined />} color='success' style={{ borderRadius: 6 }}>Active</Tag> : <Tag icon={<PauseCircleOutlined />} style={{ borderRadius: 6 }}>Paused</Tag>,
    },
    { title: 'Schedule', dataIndex: 'cronExpression', width: 100,
      render: (v: string) => v ? <Tag icon={<ClockCircleOutlined />} style={{ borderRadius: 6, fontSize: 12 }}>{v}</Tag> : <Text style={{ color: '#cbd5e1' }}>Manual</Text>,
    },
    {
      title: 'Actions', width: 220,
      render: (_: any, record: any) => (
        <Space size='small'>
          <Button type='link' size='small' icon={<ThunderboltOutlined />} onClick={() => trigger(record.id)} style={{ color: '#6366f1' }}>Trigger</Button>
          <Button type='link' size='small' icon={<EditOutlined />} onClick={() => openEdit(record)}>Edit</Button>
          <Popconfirm title='Confirm delete?' description='This cannot be undone' onConfirm={() => handleDelete(record.id)} okButtonProps={{ danger: true }}>
            <Button type='link' size='small' danger icon={<DeleteOutlined />}>Delete</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const isWizardMode = !editing

  const wizardFooter = () => {
    if (wizardStep === 0) return <Button onClick={() => setModalOpen(false)}>Cancel</Button>
    return (
      <Space>
        <Button icon={<ArrowLeftOutlined />} onClick={() => setWizardStep(wizardStep - 1)}>Back</Button>
        {wizardStep === 1 && (
          <Button type='primary' icon={<ArrowRightOutlined />} onClick={() => { if (selectedSourceIds.length === 0) { message.warning('Please select at least one source'); return } setWizardStep(2) }} disabled={!discoveryResult || !discoveryResult.sources || discoveryResult.sources.length === 0} style={{ borderRadius: 8 }}>Next</Button>
        )}
        {wizardStep === 2 && (
          <Button type='primary' icon={<CheckOutlined />} onClick={handleCreate} loading={creating} style={{ borderRadius: 8, background: 'linear-gradient(135deg, #818cf8, #6366f1)', border: 'none' }}>Create Subscription</Button>
        )}
      </Space>
    )
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <Title level={4} style={{ margin: 0, fontWeight: 700 }}>Subscriptions</Title>
        <Button type='primary' icon={<PlusOutlined />} onClick={openCreate} style={{ borderRadius: 8, height: 38 }}>Create Subscription</Button>
      </div>
      <Table rowKey='id' columns={columns} dataSource={data} loading={loading} pagination={{ pageSize: 15, showTotal: (t: any) => 'Total ' + t + ' rules' }} style={{ borderRadius: 12, overflow: 'hidden' }} />
      <Modal
        title={isWizardMode ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <span style={{ fontWeight: 600 }}>Create Subscription</span>
            <Steps current={wizardStep} size='small' style={{ flex: 1, maxWidth: 360 }}
              items={[{ title: 'Describe' }, { title: 'Select Sources' }, { title: 'Confirm' }]}
            />
          </div>
        ) : <span style={{ fontWeight: 600 }}>Edit Subscription</span>}
        open={modalOpen}
        onOk={isWizardMode ? undefined : handleSubmit}
        onCancel={() => { setModalOpen(false); setDiscoveryResult(null) }}
        destroyOnClose width={640}
        footer={isWizardMode ? wizardFooter : undefined}
        okText={isWizardMode ? undefined : 'Save'} cancelText='Cancel'
      >
        {!isWizardMode ? (
          <Form form={form} layout='vertical' style={{ marginTop: 16 }}>
            <Form.Item name='name' label='Rule Name' rules={[{ required: true, message: 'Please enter a name' }]}>
              <Input placeholder='e.g. AI Industry Trends' style={{ borderRadius: 8 }} />
            </Form.Item>
            <Form.Item name='keywords' label='Keywords (comma separated)'>
              <Input placeholder='e.g. LLM, Agent, RAG' style={{ borderRadius: 8 }} />
            </Form.Item>
            <Form.Item name='sourcePlatforms' label='Source Platforms (comma separated)'>
              <Input placeholder='e.g. rss, web, api' style={{ borderRadius: 8 }} />
            </Form.Item>
            <Space size='middle'>
              <Form.Item name='matchMode' label='Match Mode'>
                <Select style={{ width: 120 }}>
                  <Select.Option value={1}>Exact</Select.Option>
                  <Select.Option value={2}>Fuzzy</Select.Option>
                  <Select.Option value={3}>Semantic</Select.Option>
                </Select>
              </Form.Item>
              <Form.Item name='priority' label='Priority'>
                <Select style={{ width: 100 }}>
                  <Select.Option value={1}>High</Select.Option>
                  <Select.Option value={2}>Medium</Select.Option>
                  <Select.Option value={3}>Low</Select.Option>
                </Select>
              </Form.Item>
            </Space>
            <Form.Item name='cronExpression' label='Cron Expression (optional)'>
              <Input placeholder='e.g. 0 */2 * * *' style={{ borderRadius: 8 }} />
            </Form.Item>
          </Form>
        ) : (
          <div style={{ marginTop: 8 }}>
            {wizardStep === 0 && (
              <div style={{ textAlign: 'center', padding: '32px 16px' }}>
                <BulbOutlined style={{ fontSize: 48, color: '#6366f1', marginBottom: 16 }} />
                <Title level={5} style={{ marginBottom: 8, fontWeight: 600 }}>What content do you want to follow?</Title>
                <Text style={{ color: '#94a3b8', display: 'block', marginBottom: 20 }}>Describe your interests in natural language.</Text>
                <Input.TextArea value={interestInput} onChange={e => setInterestInput(e.target.value)}
                  placeholder='e.g. I want to follow the latest progress on AI Agent, RAG, and LLM...'
                  autoSize={{ minRows: 3, maxRows: 6 }} style={{ borderRadius: 10, fontSize: 14, maxWidth: 480 }}
                />
                <div style={{ marginTop: 20 }}>
                  <Button type='primary' size='large' icon={discovering ? <LoadingOutlined spin /> : <SearchOutlined />}
                    onClick={handleDiscover} loading={discovering}
                    style={{ borderRadius: 10, height: 44, paddingInline: 32, background: 'linear-gradient(135deg, #818cf8, #6366f1)', border: 'none' }}>
                    {discovering ? 'Searching...' : 'AI Search RSS Sources'}
                  </Button>
                </div>
              </div>
            )}
            {wizardStep === 1 && discoveryResult && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, padding: '12px 16px', background: 'linear-gradient(135deg, #f0f0ff, #faf5ff)', borderRadius: 10, border: '1px solid #e0d7fe' }}>
                  <div>
                    <Text strong style={{ fontSize: 14, color: '#4338ca' }}>
                      <BulbOutlined style={{ marginRight: 6 }} />
                      Found {(discoveryResult.sources || []).length} sources
                    </Text>
                  </div>
                  <Space>
                    <Text style={{ color: '#6366f1', fontWeight: 600 }}>{selectedSourceIds.length}/{(discoveryResult.sources || []).length} selected</Text>
                    <Button size='small' type='link' onClick={selectAll}>Select All</Button>
                    <Button size='small' type='link' onClick={deselectAll}>Deselect All</Button>
                  </Space>
                </div>
                <div style={{ maxHeight: 340, overflow: 'auto', paddingRight: 4 }}>
                  {(discoveryResult.sources || []).map((source: any) => (
                    <div key={source.id} onClick={() => toggleSource(source.id)}
                      style={{ display: 'flex', alignItems: 'flex-start', padding: '10px 12px', marginBottom: 6, borderRadius: 8,
                        border: '1px solid ' + (selectedSourceIds.includes(source.id) ? '#c7d2fe' : '#f1f5f9'),
                        background: selectedSourceIds.includes(source.id) ? '#f8faff' : '#fff', cursor: 'pointer', transition: 'all 0.15s' }}>
                      <Checkbox checked={selectedSourceIds.includes(source.id)} style={{ marginRight: 10, marginTop: 2 }} />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
                          <Text strong style={{ fontSize: 13 }}>{source.name}</Text>
                          <Tag color={platformColor[source.platform] || 'default'} style={{ borderRadius: 6, fontSize: 11 }}>{source.platform}</Tag>
                          <Tag style={{ borderRadius: 6, fontSize: 11, color: (sourceTypeLabel[source.source_type] || {}).color || '#94a3b8', background: '#f8fafc', border: 'none' }}>{(sourceTypeLabel[source.source_type] || {}).label || source.source_type}</Tag>
                        </div>
                        <Text style={{ fontSize: 11, color: '#94a3b8', display: 'block', wordBreak: 'break-all' }}>{source.url}</Text>
                        {source.description && <Text style={{ fontSize: 11, color: '#64748b' }}>{source.description}</Text>}
                      </div>
                    </div>
                  ))}
                  {(!discoveryResult.sources || discoveryResult.sources.length === 0) && (
                    <Empty description='No sources found' style={{ padding: '24px 0' }} />
                  )}
                </div>
              </div>
            )}
            {wizardStep === 2 && discoveryResult && (
              <div>
                <div style={{ padding: '14px 16px', background: '#f8fafc', borderRadius: 10, border: '1px solid #e2e8f0', marginBottom: 16 }}>
                  <Text strong style={{ fontSize: 13, color: '#475569', display: 'block', marginBottom: 8 }}>Subscription Summary</Text>
                  <Space direction='vertical' size={6} style={{ width: '100%' }}>
                    <div><Text style={{ color: '#94a3b8', fontSize: 12 }}>Name: </Text><Text strong>{form.getFieldValue('name') || discoveryResult.suggested_name}</Text></div>
                    <div><Text style={{ color: '#94a3b8', fontSize: 12 }}>Keywords: </Text>{(discoveryResult.keywords || []).slice(0, 5).map((k: string, i: number) => <Tag key={i} style={{ borderRadius: 6, background: '#f0f0ff', color: '#6366f1', border: 'none' }}>{k}</Tag>)}</div>
                    <div><Text style={{ color: '#94a3b8', fontSize: 12 }}>Selected RSS Sources: </Text><Text strong style={{ color: '#6366f1' }}>{(discoveryResult.sources || []).filter((s: any) => selectedSourceIds.includes(s.id)).length}</Text></div>
                  </Space>
                </div>
                <Collapse ghost items={[{ key: 'advanced', label: <Text style={{ fontSize: 13, color: '#64748b' }}>Advanced Settings</Text>, children: (
                  <Form form={form} layout='vertical'>
                    <Form.Item name='name' label='Rule Name'><Input placeholder={discoveryResult.suggested_name} style={{ borderRadius: 8 }} /></Form.Item>
                    <Space size='middle'>
                      <Form.Item name='matchMode' label='Match Mode'><Select style={{ width: 120 }}><Select.Option value={1}>Exact</Select.Option><Select.Option value={2}>Fuzzy</Select.Option><Select.Option value={3}>Semantic</Select.Option></Select></Form.Item>
                      <Form.Item name='priority' label='Priority'><Select style={{ width: 100 }}><Select.Option value={1}>High</Select.Option><Select.Option value={2}>Medium</Select.Option><Select.Option value={3}>Low</Select.Option></Select></Form.Item>
                    </Space>
                    <Form.Item name='cronExpression' label='Cron Expression'><Input placeholder='e.g. 0 */2 * * * (leave empty for manual)' style={{ borderRadius: 8 }} /></Form.Item>
                  </Form>
                )}]} />
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}

export default SubscriptionPage
