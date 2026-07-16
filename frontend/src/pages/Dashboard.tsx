import { useEffect, useState, useRef } from 'react'
import { Row, Col, Card, Statistic, Typography, Tag, Skeleton } from 'antd'
import { UserOutlined, UnorderedListOutlined, FileTextOutlined, CheckSquareOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import request from '../api/request'
import { useThemeStore } from '../store/theme'

gsap.registerPlugin(useGSAP)
const { Title, Text } = Typography

const grad: Record<string, string[]> = {
  users: ['#667eea', '#764ba2'],
  subs: ['#f093fb', '#f5576c'],
  contents: ['#4facfe', '#00f2fe'],
  approvals: ['#43e97b', '#38f9d7'],
}

function StatCard({ title, value, icon, keyName, delay }: any) {
  const ref = useRef<HTMLDivElement>(null)
  const [d, setD] = useState(0)
  useGSAP(() => { gsap.from(ref.current, { y: 30, opacity: 0, duration: 0.6, delay, ease: 'power2.out' }) }, { scope: ref })
  useEffect(() => {
    if (!value) return
    const o = { v: 0 }
    gsap.to(o, { v: value, duration: 1, delay: delay + 0.2, ease: 'power2.out', onUpdate: () => setD(Math.round(o.v)) })
  }, [value])
  const [c1, c2] = grad[keyName] || grad.users
  return (
    <Card ref={ref as any} style={{ borderRadius: 12, border: 'none', boxShadow: dark ? 'none' : '0 1px 3px rgba(0,0,0,0.06)' }}
      bodyStyle={{ padding: '20px 24px', background: dark ? '#1a1a1a' : (c1 + '08') }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div><Statistic title={<span style={{ fontSize: 13, color: '#64748b' }}>{title}</span>} value={d} valueStyle={{ fontSize: 32, fontWeight: 700, color: c1 }} /></div>
        <div style={{ width: 48, height: 48, borderRadius: 14, background: 'linear-gradient(135deg, ' + c1 + ', ' + c2 + ')', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 12px ' + c1 + '40' }}>{icon}</div>
      </div>
    </Card>
  )
}

export default function Dashboard() {
  const [metrics, setMetrics] = useState<any>({})
  const [charts, setCharts] = useState<any>({})
  const [loading, setLoading] = useState(true)
  const [added, setAdded] = useState<number[]>([])
  const dark = useThemeStore((s) => s.dark)
  const [subs, setSubs] = useState<any[]>([])
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    request.get('/java/subscriptions').then((r: any) => setSubs(r.data?.items ?? r.data?.records ?? [])).catch(() => {})
    Promise.all([
      request.get('/java/system/metrics').then((r: any) => setMetrics(r.data || {})),
      request.get('/java/system/charts').then((r: any) => setCharts(r.data || {})),
    ]).finally(() => setLoading(false))
  }, [])

  useGSAP(() => { gsap.from('.chart-box', { y: 30, opacity: 0, duration: 0.6, delay: 0.5, stagger: 0.15, ease: 'power2.out' }) }, { scope: ref, dependencies: [loading] })

  const pieData = (charts.platformDistribution || []).map((d: any) => ({ name: d.platform, value: d.count }))
  const xData = (charts.hourlyTrend || []).map((d: any) => d.hour)
  const yData = (charts.hourlyTrend || []).map((d: any) => d.count)

  if (loading) {
    return (
      <div ref={ref}>
        <Skeleton.Input active style={{ width: 200, height: 28, marginBottom: 24 }} />
        <Row gutter={[20, 20]}>
          {[0,1,2,3].map(i => <Col xs={24} sm={12} lg={6} key={i}><Card style={{ borderRadius: 12 }}><Skeleton active paragraph={{ rows: 1 }} /></Card></Col>)}
        </Row>
        <Row gutter={[20, 20]} style={{ marginTop: 20 }}>
          <Col xs={24} lg={10}><Card style={{ borderRadius: 12 }}><Skeleton active paragraph={{ rows: 4 }} /></Card></Col>
          <Col xs={24} lg={14}><Card style={{ borderRadius: 12 }}><Skeleton active paragraph={{ rows: 4 }} /></Card></Col>
        </Row>
      </div>
    )
  }

  return (
    <div ref={ref}>
      <Title level={4} style={{ marginBottom: 24, fontWeight: 700, color: dark ? '#e2e8f0' : '#1e293b' }}>Dashboard</Title>
      <Row gutter={[20, 20]}>
        <Col xs={24} sm={12} lg={6}><StatCard title='Total Users' value={metrics.totalUsers} icon={<UserOutlined style={{color:'#fff',fontSize:22}} />} keyName='users' delay={0} /></Col>
        <Col xs={24} sm={12} lg={6}><StatCard title='Subscriptions' value={metrics.totalSubscriptions} icon={<UnorderedListOutlined style={{color:'#fff',fontSize:22}} />} keyName='subs' delay={0.1} /></Col>
        <Col xs={24} sm={12} lg={6}><StatCard title='Total Content' value={metrics.totalContents} icon={<FileTextOutlined style={{color:'#fff',fontSize:22}} />} keyName='contents' delay={0.2} /></Col>
        <Col xs={24} sm={12} lg={6}><StatCard title='Pending' value={metrics.pendingApprovals} icon={<CheckSquareOutlined style={{color:'#fff',fontSize:22}} />} keyName='approvals' delay={0.3} /></Col>
      </Row>
      <Row gutter={[20, 20]} style={{ marginTop: 20 }}>
        <Col xs={24} lg={10}>
          <Card className='chart-box' style={{ borderRadius: 12, border: 'none', boxShadow: dark ? 'none' : '0 1px 3px rgba(0,0,0,0.06)' }} bodyStyle={{ padding: 20 }} title={<span style={{ fontWeight: 600, fontSize: 15 }}>Source Distribution</span>}>
            <ReactECharts option={{ tooltip: { trigger: 'item' }, series: [{ type: 'pie', radius: ['50%','78%'], center: ['50%','50%'], data: pieData, label: { show: false }, itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 } }], color: ['#818cf8','#6366f1','#4f46e5','#4338ca','#3730a3'] }} style={{ height: 260 }} />
          </Card>
        </Col>
        <Col xs={24} lg={14}>
          <Card className='chart-box' style={{ borderRadius: 12, border: 'none', boxShadow: dark ? 'none' : '0 1px 3px rgba(0,0,0,0.06)' }} bodyStyle={{ padding: 20 }} title={<span style={{ fontWeight: 600, fontSize: 15 }}>24h Trend</span>}>
            <ReactECharts option={{ tooltip: { trigger: 'axis' }, xAxis: { type: 'category', data: xData, axisLabel: { color: '#94a3b8', fontSize: 11 } }, yAxis: { type: 'value', splitLine: { lineStyle: { color: '#f1f5f9' } } }, series: [{ data: yData, type: 'line', smooth: true, symbol: 'circle', symbolSize: 6, lineStyle: { color: '#6366f1', width: 2.5 }, itemStyle: { color: '#6366f1' }, areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: '#818cf830' }, { offset: 1, color: '#818cf802' }] } } }], grid: { top: 20, right: 20, bottom: 30, left: 45 } }} style={{ height: 260 }} />
          </Card>
        </Col>
      </Row>
      <Title level={5} style={{ marginTop: 32, marginBottom: 16, fontWeight: 600, color: dark ? '#e2e8f0' : '#1e293b' }}>Quick Start - Subscribe Instantly</Title>
      <Text style={{ color: '#94a3b8', display: 'block', marginBottom: 20, fontSize: 13 }}>Click any template to instantly create a subscription with pre-configured RSS sources.</Text>
      <Row gutter={[16, 16]}>
        {[
          { icon: 'okay', name: 'AI Technology', desc: 'Latest AI papers, OpenAI, Anthropic, Google AI', color: '#6366f1', feeds: [{url:'https://hnrss.org/frontpage',name:'Hacker News',platform:'rss'},{url:'https://rss.arxiv.org/rss/cs.AI',name:'arXiv AI',platform:'rss'},{url:'https://openai.com/blog/rss.xml',name:'OpenAI Blog',platform:'rss'}], keywords:['AI','machine learning','LLM'] },
          { icon: 'okay', name: 'Tech News', desc: 'TechCrunch, Verge, Ars Technica, WIRED', color: '#0ea5e9', feeds: [{url:'https://techcrunch.com/feed/',name:'TechCrunch',platform:'rss'},{url:'https://www.theverge.com/rss/index.xml',name:'The Verge',platform:'rss'},{url:'https://arstechnica.com/feed/',name:'Ars Technica',platform:'rss'}], keywords:['tech','startup','gadgets'] },
          { icon: 'okay', name: 'Programming', desc: 'GitHub, Stack Overflow, Reddit programming', color: '#f59e0b', feeds: [{url:'https://hnrss.org/frontpage',name:'Hacker News',platform:'rss'},{url:'https://www.reddit.com/r/programming/.rss',name:'Reddit r/programming',platform:'rss'},{url:'https://github.blog/feed/',name:'GitHub Blog',platform:'rss'}], keywords:['programming','open source','github'] },
          { icon: 'okay', name: 'Cybersecurity', desc: 'Krebs, Schneier, Threatpost, Dark Reading', color: '#ef4444', feeds: [{url:'https://krebsonsecurity.com/feed/',name:'Krebs on Security',platform:'rss'},{url:'https://www.schneier.com/feed/',name:'Schneier',platform:'rss'},{url:'https://threatpost.com/feed/',name:'Threatpost',platform:'rss'}], keywords:['security','CVE','vulnerability'] },
          { icon: 'okay', name: 'Finance', desc: 'Bloomberg, CNBC, Reddit stocks', color: '#10b981', feeds: [{url:'https://feeds.bloomberg.com/markets/news.rss',name:'Bloomberg',platform:'rss'},{url:'https://www.cnbc.com/id/100003114/device/rss/rss.html',name:'CNBC Finance',platform:'rss'},{url:'https://www.reddit.com/r/stocks/.rss',name:'Reddit r/stocks',platform:'rss'}], keywords:['stocks','market','investing'] },
          { icon: 'okay', name: 'Gaming', desc: 'Reddit gaming, PC Gamer, IGN', color: '#8b5cf6', feeds: [{url:'https://www.reddit.com/r/gaming/.rss',name:'Reddit r/gaming',platform:'rss'},{url:'https://www.reddit.com/r/Games/.rss',name:'Reddit r/Games',platform:'rss'},{url:'https://www.pcgamer.com/rss/',name:'PC Gamer',platform:'rss'}], keywords:['gaming','video games','esports'] },
          { icon: 'okay', name: 'Science', desc: 'Nature, Science Daily, arXiv Physics', color: '#06b6d4', feeds: [{url:'https://www.reddit.com/r/science/.rss',name:'Reddit r/science',platform:'rss'},{url:'https://www.sciencedaily.com/rss/all.xml',name:'Science Daily',platform:'rss'},{url:'https://rss.arxiv.org/rss/physics',name:'arXiv Physics',platform:'rss'}], keywords:['science','research','physics'] },
          { icon: 'okay', name: 'Python Dev', desc: 'Reddit Python, Real Python, PyPI', color: '#f59e0b', feeds: [{url:'https://www.reddit.com/r/Python/.rss',name:'Reddit r/Python',platform:'rss'},{url:'https://realpython.com/feed/',name:'Real Python',platform:'rss'},{url:'https://pypi.org/rss/updates.xml',name:'PyPI Updates',platform:'rss'}], keywords:['python','django','fastapi'] },
        ].map((t, i) => (
          <Col xs={24} sm={12} lg={6} key={i}>
            <Card className='template-card' hoverable onClick={async () => {
              try {
                await request.post('/java/subscriptions', { name: t.name, keywords: t.keywords, sourcePlatforms: ['rss'], rssFeeds: t.feeds, matchMode: 1, priority: 2 })
                setAdded(prev => [...prev, i])
                setTimeout(() => setAdded(prev => prev.filter(x => x !== i)), 2000)
              } catch {}
            }} style={{ borderRadius: 12, border: 'none', boxShadow: dark ? 'none' : '0 1px 3px rgba(0,0,0,0.06)', cursor: 'pointer', transition: 'all 0.2s', background: added.includes(i) ? t.color + '10' : (dark ? '#1a1a1a' : '#fff') }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                <div style={{ width: 36, height: 36, borderRadius: 10, background: t.color + '18', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <span style={{ fontSize: 18 }}>{['og','og','og','og','og','og','og','og'][i] || 'og'}</span>
                </div>
                <Text strong style={{ fontSize: 14, flex: 1 }}>{t.name}</Text>
                <Tag color={added.includes(i) ? 'success' : 'default'} style={{ borderRadius: 6, fontSize: 10 }}>{added.includes(i) ? 'Subscribed!' : 'Free'}</Tag>
              </div>
              <Text style={{ fontSize: 12, color: '#94a3b8', lineHeight: 1.5 }}>{t.desc}</Text>
            </Card>
          </Col>
        ))}
      </Row>
      {subs.length > 0 && (
        <>
          <Title level={5} style={{ marginTop: 32, marginBottom: 16, fontWeight: 600, color: dark ? '#e2e8f0' : '#1e293b' }}>You Might Also Like</Title>
          <Row gutter={[16, 16]}>
            {(() => {
              const existing = subs.map((s: any) => s.name || '')
              const recos = [
                { name: 'Python Dev', desc: 'Reddit Python, Real Python, PyPI', color: '#f59e0b', feeds: [{url:'https://www.reddit.com/r/Python/.rss',name:'Reddit r/Python',platform:'rss'},{url:'https://realpython.com/feed/',name:'Real Python',platform:'rss'}], keywords:['python','django'] },
                { name: 'Science', desc: 'Nature, Science Daily, Physics', color: '#06b6d4', feeds: [{url:'https://www.reddit.com/r/science/.rss',name:'Reddit r/science',platform:'rss'},{url:'https://www.sciencedaily.com/rss/all.xml',name:'Science Daily',platform:'rss'}], keywords:['science','research'] },
                { name: 'Gaming', desc: 'Reddit gaming, PC Gamer, IGN', color: '#8b5cf6', feeds: [{url:'https://www.reddit.com/r/gaming/.rss',name:'Reddit r/gaming',platform:'rss'},{url:'https://www.pcgamer.com/rss/',name:'PC Gamer',platform:'rss'}], keywords:['gaming','esports'] },
              ].filter(r => !existing.includes(r.name)).slice(0, 3)
              return recos.map((t, i) => (
                <Col xs={24} sm={12} lg={8} key={'reco' + i}>
                  <Card className='template-card' hoverable onClick={async () => {
                    try { await request.post('/java/subscriptions', { name: t.name, keywords: t.keywords, sourcePlatforms: ['rss'], rssFeeds: t.feeds, matchMode: 1, priority: 2 }); setAdded(prev => [...prev, 999 + i]); setTimeout(() => setAdded(prev => prev.filter(x => x !== 999 + i)), 2000) } catch {}
                  }} style={{ borderRadius: 12, border: '1px dashed ' + t.color + '40', boxShadow: 'none', cursor: 'pointer', background: added.includes(999 + i) ? t.color + '10' : '#fff' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <div style={{ width: 32, height: 32, borderRadius: 8, background: t.color + '20', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <span style={{ fontSize: 14 }}>og</span>
                      </div>
                      <div style={{ flex: 1 }}>
                        <Text strong style={{ fontSize: 13 }}>{t.name}</Text>
                        <br /><Text style={{ fontSize: 11, color: '#94a3b8' }}>{t.desc}</Text>
                      </div>
                      <Tag color={added.includes(999 + i) ? 'success' : 'default'} style={{ borderRadius: 6, fontSize: 10 }}>{added.includes(999 + i) ? 'Added!' : '+ Add'}</Tag>
                    </div>
                  </Card>
                </Col>
              ))
            })()}
          </Row>
        </>
      )}
    </div>
  )
}
