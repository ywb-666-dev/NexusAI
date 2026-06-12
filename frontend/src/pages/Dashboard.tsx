import { useEffect, useState } from 'react'
import { Row, Col, Card, Statistic, Typography, Space, Tag, Spin } from 'antd'
import {
  UserOutlined,
  UnorderedListOutlined,
  FileTextOutlined,
  CheckSquareOutlined,
  RiseOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import request from '../api/request'

const { Title, Text } = Typography

const statGradients: Record<string, string> = {
  users: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  subscriptions: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
  contents: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
  approvals: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
}

function Dashboard() {
  const [metrics, setMetrics] = useState<any>({})
  const [charts, setCharts] = useState<any>({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      request.get('/java/system/metrics').then((res: any) => setMetrics(res.data || {})),
      request.get('/java/system/charts').then((res: any) => setCharts(res.data || {})),
    ]).finally(() => setLoading(false))
  }, [])

  const pieData = charts.platformDistribution?.map((d: any) => ({
    name: d.platform,
    value: d.count,
  })) ?? []

  const xData = charts.hourlyTrend?.map((d: any) => d.hour) ?? []
  const yData = charts.hourlyTrend?.map((d: any) => d.count) ?? []

  const pieOption = {
    title: {
      text: '来源平台分布',
      left: 'center',
      top: 8,
      textStyle: { fontSize: 15, fontWeight: 600, color: '#334155' },
    },
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0, textStyle: { color: '#64748b' } },
    color: ['#818cf8', '#34d399', '#fbbf24', '#f472b6', '#38bdf8'],
    series: [{
      type: 'pie',
      radius: ['50%', '75%'],
      center: ['50%', '48%'],
      data: pieData,
      label: { show: false },
      emphasis: {
        label: { show: true, fontWeight: 'bold' },
        itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.1)' },
      },
      itemStyle: { borderColor: '#fff', borderWidth: 3 },
    }],
  }

  const lineOption = {
    title: {
      text: '24小时采集趋势',
      left: 'center',
      top: 8,
      textStyle: { fontSize: 15, fontWeight: 600, color: '#334155' },
    },
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: xData,
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisLabel: { rotate: 30, fontSize: 10, color: '#94a3b8' },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      splitLine: { lineStyle: { color: '#f1f5f9' } },
      axisLabel: { color: '#94a3b8' },
    },
    series: [{
      type: 'line',
      data: yData,
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(99,102,241,0.25)' },
            { offset: 1, color: 'rgba(99,102,241,0.02)' },
          ],
        },
      },
      lineStyle: { color: '#6366f1', width: 2.5 },
      itemStyle: { color: '#6366f1' },
    }],
    grid: { left: 45, right: 25, top: 50, bottom: 55 },
  }

  const statCards = [
    { key: 'users', icon: <UserOutlined />, label: '总用户数', value: metrics.totalUsers || 0, gradient: statGradients.users },
    { key: 'subscriptions', icon: <UnorderedListOutlined />, label: '订阅规则数', value: metrics.totalSubscriptions || 0, gradient: statGradients.subscriptions },
    { key: 'contents', icon: <FileTextOutlined />, label: '内容总数', value: metrics.totalContents || 0, gradient: statGradients.contents },
    { key: 'approvals', icon: <CheckSquareOutlined />, label: '待审批工单', value: metrics.pendingApprovals || 0, gradient: statGradients.approvals },
  ]

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 400 }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div>
      {/* Welcome header */}
      <div
        style={{
          background: 'linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4338ca 100%)',
          borderRadius: 16,
          padding: '28px 32px',
          marginBottom: 24,
          boxShadow: '0 8px 32px rgba(30,27,75,0.15)',
        }}
      >
        <Row align="middle" justify="space-between">
          <Col>
            <Title level={3} style={{ color: '#fff', margin: 0, fontWeight: 700 }}>
              仪表盘
            </Title>
            <Space style={{ marginTop: 8 }}>
              <Tag
                icon={<ClockCircleOutlined />}
                color="rgba(255,255,255,0.2)"
                style={{ color: '#e2e8f0', border: 'none', background: 'rgba(255,255,255,0.12)' }}
              >
                {new Date().toLocaleDateString('zh-CN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
              </Tag>
              <Tag
                icon={<RiseOutlined />}
                color="rgba(255,255,255,0.2)"
                style={{ color: '#e2e8f0', border: 'none', background: 'rgba(255,255,255,0.12)' }}
              >
                实时监控中
              </Tag>
            </Space>
          </Col>
        </Row>
      </div>

      {/* Stat cards */}
      <Row gutter={[20, 20]}>
        {statCards.map((card) => (
          <Col xs={24} sm={12} lg={6} key={card.key}>
            <Card
              style={{
                borderRadius: 14,
                border: 'none',
                boxShadow: '0 2px 12px rgba(0,0,0,0.04)',
                height: '100%',
              }}
              bodyStyle={{ padding: '22px 24px' }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                <div>
                  <Text type="secondary" style={{ fontSize: 13, fontWeight: 500 }}>
                    {card.label}
                  </Text>
                  <div style={{ fontSize: 32, fontWeight: 700, marginTop: 8, color: '#1e293b' }}>
                    {card.value.toLocaleString()}
                  </div>
                </div>
                <div
                  style={{
                    width: 48,
                    height: 48,
                    borderRadius: 14,
                    background: card.gradient,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                  }}
                >
                  <span style={{ color: '#fff', fontSize: 22 }}>{card.icon}</span>
                </div>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      {/* Charts */}
      <Row gutter={[20, 20]} style={{ marginTop: 20 }}>
        <Col xs={24} lg={10}>
          <Card
            style={{
              borderRadius: 14,
              border: 'none',
              boxShadow: '0 2px 12px rgba(0,0,0,0.04)',
              height: '100%',
            }}
            bodyStyle={{ padding: '16px 12px' }}
          >
            {pieData.length > 0 ? (
              <ReactECharts option={pieOption} style={{ height: 340 }} />
            ) : (
              <div style={{ height: 340, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Text type="secondary">暂无平台分布数据</Text>
              </div>
            )}
          </Card>
        </Col>
        <Col xs={24} lg={14}>
          <Card
            style={{
              borderRadius: 14,
              border: 'none',
              boxShadow: '0 2px 12px rgba(0,0,0,0.04)',
              height: '100%',
            }}
            bodyStyle={{ padding: '16px 12px' }}
          >
            {xData.length > 0 ? (
              <ReactECharts option={lineOption} style={{ height: 340 }} />
            ) : (
              <div style={{ height: 340, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Text type="secondary">暂无采集趋势数据</Text>
              </div>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default Dashboard
