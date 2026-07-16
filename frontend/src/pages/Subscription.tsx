import { useEffect, useState, useRef } from 'react'
import { Table, Button, Tag, Modal, Form, Input, Select, Space, Popconfirm, Typography, Steps, Checkbox, Collapse, Empty } from 'antd'
import {
  PlusOutlined, EditOutlined, DeleteOutlined, ThunderboltOutlined,
  ClockCircleOutlined, CheckCircleOutlined, PauseCircleOutlined, SearchOutlined,
  LoadingOutlined, BulbOutlined, LinkOutlined, ArrowLeftOutlined, ArrowRightOutlined, CheckOutlined,
} from '@ant-design/icons'
import request from '../api/request'
import { App } from 'antd'
import { useThemeStore } from '../store/theme'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'

gsap.registerPlugin(useGSAP)

const { Title, Text } = Typography
const platformColor: Record<string, string> = { rss: '#f59e0b', web: '#6366f1', api: '#10b981' }
const stLabel: Record<string, { label: string; color: string }> = {
  builtin: { label: 'Built-in', color: '#10b981' },
  web_search: { label: 'Web', color: '#6366f1' },
  llm: { label: 'AI', color: '#f59e0b' },
}

export default function SubscriptionPage() {
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
  const [manualUrl, setManualUrl] = useState('')
  const dark = useThemeStore((s) => s.dark)
  const [previewData, setPreviewData] = useState<any>(null)
  const [previewing, setPreviewing] = useState<string | null>(null)
  const [searchPhase, setSearchPhase] = useState('')
  const stepRef = useRef<HTMLDivElement>(null)

  useGSAP(() => { if (stepRef.current) gsap.from(stepRef.current, { y: 16, opacity: 0, duration: 0.35, ease: 'power2.out' }) }, [wizardStep])

  const fetchData = async () => { setLoading(true); try { const r: any = await request.get('/java/subscriptions'); setData(r.data?.items ?? r.data?.records ?? []) } finally { setLoading(false) } }
  const openCreate = () => { setEditing(null); form.resetFields(); form.setFieldsValue({ matchMode: 1, priority: 2 }); setWizardStep(0); setInterestInput(''); setDiscoveryResult(null); setSelectedSourceIds([]); setCreating(false); setModalOpen(true) }
  const openEdit = (rec: any) => { setEditing(rec); form.setFieldsValue({ name: rec.name, matchMode: rec.matchMode, priority: rec.priority, cronExpression: rec.cronExpression, keywords: Array.isArray(rec.keywords) ? rec.keywords.join(', ') : rec.keywords, sourcePlatforms: Array.isArray(rec.sourcePlatforms) ? rec.sourcePlatforms.join(', ') : rec.sourcePlatforms }); setModalOpen(true) }

  const handleDiscover = async () => {
    if (!interestInput.trim()) { message.warning('Please describe what you want to follow'); return }
    setDiscovering(true); setDiscoveryResult(null); setSelectedSourceIds([]); setSearchPhase('Scanning built-in sources...')
    try {
      const res: any = await request.post('/python/subscriptions/discover-sources', { topic: interestInput.trim(), keywords: [] })
      const d = res.data
      if (!d.sources || d.sources.length === 0) { message.info('No matching sources found') }
      setDiscoveryResult(d); setSelectedSourceIds((d.sources || []).map((s: any) => s.id)); setSearchPhase(''); setWizardStep(1)
    } catch (err: any) { message.error(err.response?.data?.message || err.message || 'Search failed') }
    finally { setDiscovering(false) }
  }

  const previewSource = async (url: string, id: string) => {
    setPreviewing(id); setPreviewData(null)
    try { const res: any = await request.get('/python/subscriptions/preview-feed', { params: { url } }); setPreviewData(res.data) }
    catch { setPreviewData(null) }
    finally { setPreviewing(null) }
  }

  const toggleSource = (id: string) => { setSelectedSourceIds(p => p.includes(id) ? p.filter(x => x !== id) : [...p, id]) }
  const selectAll = () => { if (discoveryResult) setSelectedSourceIds(discoveryResult.sources.map((s: any) => s.id)) }
  const deselectAll = () => { setSelectedSourceIds([]) }

  const handleCreate = async () => {
    if (!discoveryResult) return
    const sel = (discoveryResult.sources || []).filter((s: any) => selectedSourceIds.includes(s.id))
    const feeds = sel.map((s: any) => ({ url: s.url, name: s.name, platform: s.platform }))
    const av = form.getFieldsValue()
    const payload = { name: av.name || discoveryResult.suggested_name || interestInput.trim(), keywords: discoveryResult.keywords || [], sourcePlatforms: discoveryResult.recommended_platforms || ['rss'], rssFeeds: feeds, matchMode: av.matchMode ?? 1, priority: av.priority ?? 2, cronExpression: av.cronExpression || null }
    setCreating(true)
    try { await request.post('/java/subscriptions', payload); message.success('Created'); setModalOpen(false); fetchData() }
    catch (err: any) { message.error(err.response?.data?.message || 'Creation failed') }
    finally { setCreating(false) }
  }

  const handleSubmit = async () => {
    const values = await form.validateFields()
    const payload = { ...values, keywords: values.keywords ? values.keywords.split(/[,;,\uFF0C,\uFF1B]\s*/).map((s: string) => s.trim()).filter(Boolean) : [], sourcePlatforms: values.sourcePlatforms ? values.sourcePlatforms.split(/[,;,\uFF0C,\uFF1B]\s*/).map((s: string) => s.trim()).filter(Boolean) : [], rssFeeds: editing?.rssFeeds ?? [] }
    try { if (editing) { await request.put('/java/subscriptions/' + editing.id, payload); message.success('Updated') } else { await request.post('/java/subscriptions', payload); message.success('Created') }; setModalOpen(false); fetchData() }
    catch (err: any) { message.error(err.response?.data?.message || err.message) }
  }

  const handleDelete = async (id: number) => { try { await request.delete('/java/subscriptions/' + id); message.success('Deleted'); fetchData() } catch {} }
  const trigger = async (id: number) => { try { await request.post('/java/subscriptions/' + id + '/trigger'); message.success('Triggered') } catch {} }
  useEffect(() => { fetchData() }, [])

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: 'Name', dataIndex: 'name', render: (v: string) => <span style={{ fontWeight: 600 }}>{v}</span> },
    { title: 'Keywords', dataIndex: 'keywords', render: (v: any) => { const l = Array.isArray(v) ? v : []; return l.length > 0 ? <Space size={4} wrap>{l.slice(0, 3).map((k: string, i: number) => <Tag key={i} style={{ borderRadius: 6, background: '#f0f0ff', color: '#6366f1', border: 'none' }}>{k}</Tag>)}{l.length > 3 && <Tag style={{ borderRadius: 6 }}>+{l.length - 3}</Tag>}</Space> : '-' } },
    { title: 'Feeds', dataIndex: 'rssFeeds', width: 90, render: (v: any) => { const l = Array.isArray(v) ? v : []; return l.length > 0 ? <Tag color='orange' style={{ borderRadius: 6 }}>{l.length}</Tag> : '-' } },
    { title: 'Match', dataIndex: 'matchMode', width: 80, render: (v: number) => <Tag style={{ borderRadius: 6 }}>{v === 1 ? 'Exact' : v === 2 ? 'Fuzzy' : 'Semantic'}</Tag> },
    { title: 'Priority', dataIndex: 'priority', width: 80, render: (v: number) => v === 1 ? <Tag color='error' style={{ borderRadius: 6 }}>High</Tag> : v === 2 ? <Tag color='warning' style={{ borderRadius: 6 }}>Med</Tag> : <Tag style={{ borderRadius: 6 }}>Low</Tag> },
    { title: 'Status', dataIndex: 'status', width: 80, render: (v: number) => v === 1 ? <Tag icon={<CheckCircleOutlined />} color='success' style={{ borderRadius: 6 }}>Active</Tag> : <Tag icon={<PauseCircleOutlined />} style={{ borderRadius: 6 }}>Paused</Tag> },
    { title: 'Actions', width: 200, render: (_: any, rec: any) => <Space size='small'><Button type='link' size='small' icon={<ThunderboltOutlined />} onClick={() => trigger(rec.id)} style={{ color: '#6366f1' }}>Trigger</Button><Button type='link' size='small' icon={<EditOutlined />} onClick={() => openEdit(rec)}>Edit</Button><Popconfirm title='Delete?' onConfirm={() => handleDelete(rec.id)} okButtonProps={{ danger: true }}><Button type='link' size='small' danger icon={<DeleteOutlined />}>Delete</Button></Popconfirm></Space> },
  ]

  const wizardFooter = () => {
    if (wizardStep === 0) return <Button onClick={() => setModalOpen(false)}>Cancel</Button>
    return <Space><Button icon={<ArrowLeftOutlined />} onClick={() => setWizardStep(wizardStep - 1)}>Back</Button>
      {wizardStep === 1 && <Button type='primary' icon={<ArrowRightOutlined />} onClick={() => { if (selectedSourceIds.length === 0) { message.warning('Select at least one'); return }; setWizardStep(2) }} disabled={!discoveryResult || !discoveryResult.sources?.length} style={{ borderRadius: 8 }}>Next</Button>}
      {wizardStep === 2 && <Button type='primary' icon={<CheckOutlined />} onClick={handleCreate} loading={creating} style={{ borderRadius: 8, background: 'linear-gradient(135deg, #818cf8, #6366f1)', border: 'none' }}>Create Subscription</Button>}
    </Space>
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <Title level={4} style={{ margin: 0, fontWeight: 700, color: dark ? '#e2e8f0' : '#1e293b' }}>Subscriptions</Title>
        <Button type='primary' icon={<PlusOutlined />} onClick={openCreate} style={{ borderRadius: 8, height: 38 }}>Create Subscription</Button>
      </div>
      <Table rowKey='id' columns={columns} dataSource={data} loading={loading} pagination={{ pageSize: 15, showTotal: (t: any) => 'Total ' + t + ' rules' }} style={{ borderRadius: 12, overflow: 'hidden' }} />
      <Modal title={!editing ? <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}><span style={{ fontWeight: 600 }}>Create Subscription</span><Steps current={wizardStep} size='small' style={{ flex: 1, maxWidth: 360 }} items={[{ title: 'Describe' }, { title: 'Select' }, { title: 'Confirm' }]} /></div> : <span style={{ fontWeight: 600 }}>Edit Subscription</span>}
        open={modalOpen} onOk={editing ? handleSubmit : undefined} onCancel={() => { setModalOpen(false); setDiscoveryResult(null) }} destroyOnClose width={640} footer={!editing ? wizardFooter : undefined} okText={editing ? 'Save' : undefined} cancelText='Cancel'>
        {editing ? (
          <Form form={form} layout='vertical' style={{ marginTop: 16 }}>
            <Form.Item name='name' label='Name' rules={[{ required: true }]}><Input placeholder='Rule name' style={{ borderRadius: 8 }} /></Form.Item>
            <Form.Item name='keywords' label='Keywords'><Input placeholder='e.g. LLM, Agent' style={{ borderRadius: 8 }} /></Form.Item>
            <Form.Item name='sourcePlatforms' label='Platforms'><Input placeholder='e.g. rss, web' style={{ borderRadius: 8 }} /></Form.Item>
            <Space size='middle'><Form.Item name='matchMode' label='Match'><Select style={{ width: 120 }}><Select.Option value={1}>Exact</Select.Option><Select.Option value={2}>Fuzzy</Select.Option><Select.Option value={3}>Semantic</Select.Option></Select></Form.Item><Form.Item name='priority' label='Priority'><Select style={{ width: 100 }}><Select.Option value={1}>High</Select.Option><Select.Option value={2}>Medium</Select.Option><Select.Option value={3}>Low</Select.Option></Select></Form.Item></Space>
            <Form.Item name='cronExpression' label='Cron'><Input placeholder='e.g. 0 */2 * * *' style={{ borderRadius: 8 }} /></Form.Item>
          </Form>
        ) : (
          <div style={{ marginTop: 8 }} ref={stepRef}>
            {wizardStep === 0 && <div style={{ textAlign: 'center', padding: '24px 16px' }}><BulbOutlined style={{ fontSize: 48, color: '#6366f1', marginBottom: 16 }} /><Title level={5} style={{ fontWeight: 600 }}>What content do you want to follow?</Title><Text style={{ color: '#94a3b8', display: 'block', marginBottom: 20 }}>Describe your interests. AI will find RSS sources for you.</Text><Input.TextArea value={interestInput} onChange={e => setInterestInput(e.target.value)} placeholder='e.g. I want to follow AI Agent and RAG progress...' autoSize={{ minRows: 3, maxRows: 6 }} style={{ borderRadius: 10, fontSize: 14, maxWidth: 480 }} /><div style={{ marginTop: 20 }}><Button type='primary' size='large' icon={discovering ? <LoadingOutlined spin /> : <SearchOutlined />} onClick={handleDiscover} loading={discovering} style={{ borderRadius: 10, height: 44, paddingInline: 32, background: 'linear-gradient(135deg, #818cf8, #6366f1)', border: 'none' }}>{searchPhase || (discovering ? 'Searching...' : 'AI Search RSS Sources')}</Button></div>
              <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid #e2e8f0' }}><Text style={{ color: '#94a3b8', fontSize: 12 }}>Or paste a known RSS URL:</Text><Space.Compact style={{ width: '100%', maxWidth: 480, marginTop: 8 }}><Input value={manualUrl} onChange={e => setManualUrl(e.target.value)} placeholder='https://example.com/feed.xml' style={{ borderRadius: '8px 0 0 8px' }} /><Button icon={<LinkOutlined />} onClick={() => { if (!manualUrl.trim()) { message.warning('Enter a URL'); return }; const d = { topic: manualUrl, keywords: [], suggested_name: 'Custom', sources: [{ id: 'm', url: manualUrl.trim(), name: manualUrl.trim(), platform: 'rss', description: 'Manual', relevance: 1, source_type: 'builtin' }], total_sources: 1, recommended_platforms: ['rss'] }; setDiscoveryResult(d); setSelectedSourceIds(['m']); setWizardStep(1) }} style={{ borderRadius: '0 8px 8px 0', borderColor: '#6366f1', color: '#6366f1' }}>Add</Button></Space.Compact></div>
            </div>}
            {wizardStep === 1 && discoveryResult && <div><div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, padding: '12px 16px', background: 'linear-gradient(135deg, #f0f0ff, #faf5ff)', borderRadius: 10 }}><Text strong style={{ fontSize: 14, color: '#4338ca' }}><BulbOutlined style={{ marginRight: 6 }} />Found {(discoveryResult.sources || []).length} sources</Text><Space><Text style={{ color: '#6366f1', fontWeight: 600 }}>{selectedSourceIds.length}/{(discoveryResult.sources || []).length} selected</Text><Button size='small' type='link' onClick={selectAll}>All</Button><Button size='small' type='link' onClick={deselectAll}>None</Button></Space></div><div style={{ maxHeight: 340, overflow: 'auto', paddingRight: 4 }}>{(discoveryResult.sources || []).map((s: any) => <div key={s.id} onClick={() => toggleSource(s.id)} style={{ display: 'flex', alignItems: 'flex-start', padding: '10px 12px', marginBottom: 6, borderRadius: 8, border: '1px solid ' + (selectedSourceIds.includes(s.id) ? '#c7d2fe' : '#f1f5f9'), background: selectedSourceIds.includes(s.id) ? (dark ? '#1e1a3a' : '#f8faff') : (dark ? '#1a1a1a' : '#fff'), cursor: 'pointer' }}><Checkbox checked={selectedSourceIds.includes(s.id)} style={{ marginRight: 10, marginTop: 2 }} /><div style={{ flex: 1, minWidth: 0 }}><div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}><Text strong style={{ fontSize: 13 }}>{s.name}</Text><Tag color={platformColor[s.platform] || 'default'} style={{ borderRadius: 6, fontSize: 11 }}>{s.platform}</Tag><Tag style={{ borderRadius: 6, fontSize: 11, color: (stLabel[s.source_type] || {}).color }}>{(stLabel[s.source_type] || {}).label || s.source_type}</Tag></div><Text style={{ fontSize: 11, color: '#94a3b8', wordBreak: 'break-all' }}>{s.url}</Text></div></div>)}</div></div>}
            {wizardStep === 2 && discoveryResult && <div><div style={{ padding: '14px 16px', background: dark ? '#1a1a1a' : '#f8fafc', borderRadius: 10, border: dark ? '1px solid #2a2a2a' : '1px solid #e2e8f0', marginBottom: 16 }}><Text strong style={{ fontSize: 13, color: '#475569', display: 'block', marginBottom: 8 }}>Summary</Text><Space direction='vertical' size={6}><div><Text style={{ color: '#94a3b8', fontSize: 12 }}>Name: </Text><Text strong>{form.getFieldValue('name') || discoveryResult.suggested_name}</Text></div><div><Text style={{ color: '#94a3b8', fontSize: 12 }}>Sources: </Text><Text strong style={{ color: '#6366f1' }}>{(discoveryResult.sources || []).filter((s: any) => selectedSourceIds.includes(s.id)).length}</Text></div></Space></div><Collapse ghost items={[{ key: 'adv', label: <Text style={{ fontSize: 13, color: '#64748b' }}>Advanced</Text>, children: <Form form={form} layout='vertical'><Form.Item name='name' label='Name'><Input placeholder={discoveryResult.suggested_name} style={{ borderRadius: 8 }} /></Form.Item><Space size='middle'><Form.Item name='matchMode' label='Match'><Select style={{ width: 120 }}><Select.Option value={1}>Exact</Select.Option><Select.Option value={2}>Fuzzy</Select.Option><Select.Option value={3}>Semantic</Select.Option></Select></Form.Item><Form.Item name='priority' label='Priority'><Select style={{ width: 100 }}><Select.Option value={1}>High</Select.Option><Select.Option value={2}>Medium</Select.Option><Select.Option value={3}>Low</Select.Option></Select></Form.Item></Space><Form.Item name='cronExpression' label='Cron'><Input placeholder='Optional' style={{ borderRadius: 8 }} /></Form.Item></Form>}]} /></div>}
          </div>
        )}
      </Modal>
    </div>
  )
}
