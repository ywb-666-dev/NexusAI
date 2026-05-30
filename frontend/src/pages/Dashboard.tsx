import { useEffect, useState } from 'react'
import { Row, Col, Card, Statistic } from 'antd'
import { UserOutlined, UnorderedListOutlined, FileTextOutlined, CheckSquareOutlined } from '@ant-design/icons'
import request from '../api/request'

function Dashboard() {
  const [metrics, setMetrics] = useState<any>({})

  useEffect(() => {
    request.get('/java/system/metrics').then((res: any) => {
      setMetrics(res.data)
    })
  }, [])

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
    </div>
  )
}

export default Dashboard
