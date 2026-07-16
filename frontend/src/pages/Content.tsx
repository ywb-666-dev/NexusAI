import { useEffect, useState, useRef } from 'react'
import { Card, Tag, Typography, Space, Button, Drawer, Row, Col, Input, Skeleton, Segmented, App } from 'antd'
import { FileTextOutlined, EyeOutlined, SearchOutlined, GlobalOutlined } from '@ant-design/icons'
import request from '../api/request'
import { useThemeStore } from '../store/theme'
import { useGSAP } from '@gsap/react'
import { useSearchParams } from 'react-router-dom'
import { timeAgo } from '../utils/time'
import gsap from 'gsap'

gsap.registerPlugin(useGSAP)
const { Title, Text, Paragraph } = Typography

const platColor: Record<string, string> = { rss: '#f59e0b', web: '#6366f1', api: '#10b981' }

export default function ContentPage() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [detail, setDetail] = useState<any>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [searchParams] = useSearchParams()
  const [search, setSearch] = useState(searchParams.get('search') || '')
  const dark = useThemeStore((s) => s.dark)
  const { message } = App.useApp()
  const [aiLoading, setAiLoading] = useState(false)
  const [aiResult, setAiResult] = useState('')
  const [filter, setFilter] = useState('all')
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => { fetchContent() }, [])

  const handleSummarize = async (text: string) => {
    if (!text) return; setAiLoading(true); setAiResult('')
    try { const r: any = await request.post('/python/skills/summarize/invoke', { text: text.slice(0, 3000), style: 'article_summary' }); setAiResult(r.data?.data?.summary || r.data?.summary || 'Summary not available') }
    catch { setAiResult('Failed to generate summary') }
    finally { setAiLoading(false) }
  }

  const handleTranslate = async (text: string) => {
    if (!text) return; setAiLoading(true); setAiResult('')
    try { const r: any = await request.post('/python/skills/translate/invoke', { text: text.slice(0, 3000) }); setAiResult(r.data?.data?.translated || r.data?.translated || 'Translation not available') }
    catch { setAiResult('Failed to translate') }
    finally { setAiLoading(false) }
  }
  const fetchContent = async () => { setLoading(true); try { const r: any = await request.get('/java/contents?size=50'); setData(r.data?.items ?? r.data?.records ?? []) } finally { setLoading(false) } }

  useGSAP(() => { gsap.from('.content-card', { y: 24, opacity: 0, duration: 0.4, stagger: 0.06, ease: 'power2.out' }) }, { scope: ref, dependencies: [loading] })

  const filtered = data.filter(d => { if (search && !(d.title || '').toLowerCase().includes(search.toLowerCase())) return false; if (filter !== 'all' && d.sourcePlatform !== filter) return false; return true })

  function CardComp({ item }: any) {
    const cardRef = useRef<HTMLDivElement>(null)
    return (
      <Col xs={24} sm={12} lg={8} xl={6}>
        <Card hoverable className='content-card' ref={cardRef as any} onClick={() => { setDetail(item); setDrawerOpen(true) }}
          style={{ borderRadius: 12, border: 'none', boxShadow: dark ? 'none' : '0 1px 3px rgba(0,0,0,0.06)', height: '100%', transition: 'all 0.2s ease', cursor: 'pointer' }}
          onMouseEnter={() => gsap.to(cardRef.current, { y: -4, duration: 0.3, ease: 'power2.out' })}
          onMouseLeave={() => gsap.to(cardRef.current, { y: 0, duration: 0.3, ease: 'power2.out' })}
          bodyStyle={{ padding: '18px 20px', display: 'flex', flexDirection: 'column', height: '100%' }}>
          <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
            <Tag color={platColor[item.sourcePlatform] || 'default'} style={{ borderRadius: 6, fontSize: 10, margin: 0 }}><GlobalOutlined style={{ marginRight: 4 }} />{item.sourcePlatform}</Tag>
            {item.author && <Tag style={{ borderRadius: 6, fontSize: 10, margin: 0, background: '#f1f5f9', border: 'none', color: '#64748b' }}>{item.author}</Tag>}
          </div>
          <Text strong style={{ fontSize: 14, lineHeight: 1.5, flex: 1, display: 'block', marginBottom: 8, color: dark ? '#e2e8f0' : '#1e293b' }}>{item.title}</Text>
          <Text style={{ fontSize: 12, color: '#94a3b8', lineHeight: 1.5, flexShrink: 0 }}>{(item.summary || '').slice(0, 120)}{item.summary && item.summary.length > 120 ? '...' : ''}</Text>
          <div style={{ marginTop: 'auto', paddingTop: 10, fontSize: 11, color: '#cbd5e1' }}>
            {item.fetchedAt ? timeAgo(item.fetchedAt) + ' . ' + Math.max(1, Math.ceil((item.contentBody || item.summary || '').length / 500)) + ' min read' : ''}
          </div>
        </Card>
      </Col>
    )
  }

  if (loading) {
    return (
      <div ref={ref}>
        <Skeleton.Input active style={{ width: 200, height: 28, marginBottom: 20 }} />
        <Segmented options={[{label:'All',value:'all'},{label:'RSS',value:'rss'},{label:'Web',value:'web'},{label:'API',value:'api'}]} value={filter} onChange={v => setFilter(v as string)} style={{ marginBottom: 16 }} />
      <Row gutter={[16, 16]}>
          {Array.from({length: 8}, (_, i) => (
            <Col xs={24} sm={12} lg={8} xl={6} key={i}>
              <Card style={{ borderRadius: 12 }}>
                <Skeleton active paragraph={{ rows: 3 }} />
              </Card>
            </Col>
          ))}
        </Row>
      </div>
    )
  }

  return (
    <div ref={ref}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <Title level={4} style={{ margin: 0, fontWeight: 700, color: dark ? '#e2e8f0' : '#1e293b' }}>Content Feed</Title>
        <Input prefix={<SearchOutlined />} placeholder='Search titles...' value={search} onChange={e => setSearch(e.target.value)} style={{ width: 260, borderRadius: 10 }} allowClear />
      </div>
      <Segmented options={[{label:'All',value:'all'},{label:'RSS',value:'rss'},{label:'Web',value:'web'},{label:'API',value:'api'}]} value={filter} onChange={v => setFilter(v as string)} style={{ marginBottom: 16 }} />
      <Row gutter={[16, 16]}>
        {filtered.map((item: any) => <CardComp key={item.id} item={item} />)}
      </Row>
      {filtered.length === 0 && !loading && <div style={{ textAlign: 'center', padding: 60, color: '#94a3b8' }}><FileTextOutlined style={{ fontSize: 48, marginBottom: 12 }} /><br />No content yet. Create a subscription to start collecting.</div>}
      <Drawer title={<span style={{ fontWeight: 600 }}>{detail?.title}</span>} extra={<Button type='primary' size='small' onClick={() => { if (detail?.sourceUrl) { navigator.clipboard.writeText(detail.sourceUrl); message.success('Link copied') } }} style={{ borderRadius: 6 }}>Copy Link</Button>} open={drawerOpen} onClose={() => setDrawerOpen(false)} width={640}>
        {detail && <>
          <Space size={4} style={{ marginBottom: 16 }}>
            <Button size='small' loading={aiLoading} onClick={() => handleSummarize(detail.contentBody || detail.summary || '')} style={{ borderRadius: 6 }}>AI Summarize</Button>
            <Button size='small' loading={aiLoading} onClick={() => handleTranslate(detail.contentBody || detail.summary || '')} style={{ borderRadius: 6 }}>Translate</Button>
          </Space>
          {aiResult && <Card size='small' style={{ marginBottom: 16, borderRadius: 8, background: '#f8faff', border: '1px solid #e0e7ff' }} bodyStyle={{ padding: '10px 14px' }}><Text style={{ fontSize: 13, color: '#4338ca', fontWeight: 600, display: 'block', marginBottom: 6 }}>AI Result</Text><div style={{ lineHeight: 1.8, fontSize: 13, color: '#334155' }}>{aiResult}</div></Card>}
          <Space size={4} style={{ marginBottom: 16 }}>
            <Tag color={platColor[detail.sourcePlatform]} style={{ borderRadius: 6 }}>{detail.sourcePlatform}</Tag>
            <Text style={{ fontSize: 12, color: '#94a3b8' }}>{detail.author || 'Unknown'} - {detail.fetchedAt ? timeAgo(detail.fetchedAt) : ''}</Text>
          </Space>
          <div style={{ lineHeight: 1.9, color: '#334155', whiteSpace: 'pre-wrap', fontSize: 14 }}>{detail.contentBody || detail.summary || 'No content available'}</div>
        </>}
      </Drawer>
    </div>
  )
}
