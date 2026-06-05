import { useEffect, useState } from 'react'
import { Row, Col, Card, Statistic } from 'antd'
import { UserOutlined, UnorderedListOutlined, FileTextOutlined, CheckSquareOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import request from '../api/request'

function Dashboard() {
  const [metrics, setMetrics] = useState<any>({})
  const [charts, setCharts] = useState<any>({})

  useEffect(() => {
    request.get('/java/system/metrics').then((res: any) => setMetrics(res.data))
    request.get('/java/system/charts').then((res: any) => setCharts(res.data))
  }, [])

  const pieData = charts.platformDistribution?.map((d: any) => ({
    name: d.platform,
    value: d.count,
  })) ?? []

  const xData = charts.hourlyTrend?.map((d: any) => d.hour) ?? []
  const yData = charts.hourlyTrend?.map((d: any) => d.count) ?? []

  const pieOption = {
    title: { text: '平台分布', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'item' },
    legend: { bottom: '0%' },
    series: [{
      type: 'pie',
      radius: ['45%', '70%'],
      center: ['50%', '50%'],
      data: pieData,
      label: { show: false },
      emphasis: { label: { show: true } },
    }],
  }

  const lineOption = {
    title: { text: '24小时采集趋势', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: xData, axisLabel: { rotate: 30, fontSize: 10 } },
    yAxis: { type: 'value', minInterval: 1 },
    series: [{
      type: 'line',
      data: yData,
      smooth: true,
      areaStyle: { opacity: 0.15 },
      itemStyle: { color: '#1677ff' },
    }],
    grid: { left: 40, right: 20, top: 40, bottom: 50 },
  }

  return (
    <div>
      <h2>仪表盘</h2>
      <Row gutter={16} style={{ marginTop: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic title="总用户数" value={metrics.totalUsers || 0} prefix={<UserOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="订阅规则数" value={metrics.totalSubscriptions || 0} prefix={<UnorderedListOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="内容总数" value={metrics.totalContents || 0} prefix={<FileTextOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="待审批工单" value={metrics.pendingApprovals || 0} prefix={<CheckSquareOutlined />} />
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginTop: 24 }}>
        <Col span={10}>
          <Card>
            <ReactECharts option={pieOption} style={{ height: 320 }} />
          </Card>
        </Col>
        <Col span={14}>
          <Card>
            <ReactECharts option={lineOption} style={{ height: 320 }} />
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default Dashboard
