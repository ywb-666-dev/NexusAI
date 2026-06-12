import { useEffect, useState } from 'react'
import { Table, Tag, Input, Drawer, Button, Spin, List, Typography, Divider, Descriptions, Space, Tooltip } from 'antd'
import {
  LinkOutlined,
  EyeOutlined,
  SearchOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons'
import request from '../api/request'

const { Text, Paragraph, Title } = Typography

function stripHtml(html: string | undefined | null): string {
  if (!html) return ''
  const doc = new DOMParser().parseFromString(html, 'text/html')
  return doc.body.textContent || ''
}

function ContentPage() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [selectedContent, setSelectedContent] = useState<any>(null)
  const [relatedContents, setRelatedContents] = useState<any[]>([])
  const [relatedLoading, setRelatedLoading] = useState(false)

  const fetchData = async () => {
    setLoading(true)
    try {
      const res: any = await request.get('/java/contents?size=50')
      setData(res.data?.records ?? res.data?.items ?? [])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchData() }, [])

  const openDetail = async (record: any) => {
    setSelectedContent(record)
    setDrawerOpen(true)
    setRelatedContents([])
    if (record.id) {
      setRelatedLoading(true)
      try {
        const res: any = await request.post(`/python/contents/${record.id}/search-similar`)
        setRelatedContents(res.data || [])
      } catch {
        if (record.relatedContents) {
          try {
            const ids = typeof record.relatedContents === 'string'
              ? JSON.parse(record.relatedContents)
              : record.relatedContents
            setRelatedContents(ids.map((id: string) => ({ id, title: '关联内容', source_platform: '-' })))
          } catch { /* ignore */ }
        }
      } finally {
        setRelatedLoading(false)
      }
    }
  }

  const columns = [
    {
      title: '标题',
      dataIndex: 'title',
      width: 280,
      ellipsis: true,
      render: (v: string) => <span style={{ fontWeight: 500 }}>{v}</span>,
    },
    {
      title: '平台',
      dataIndex: 'sourcePlatform',
      width: 80,
      render: (v: string) => (
        <Tag style={{ borderRadius: 6, border: 'none', background: '#f0f0ff', color: '#6366f1' }}>
          {v}
        </Tag>
      ),
    },
    { title: '作者', dataIndex: 'author', width: 100, ellipsis: true },
    {
      title: '摘要',
      dataIndex: 'summary',
      ellipsis: true,
      width: 300,
      render: (v: string) => (
        <Text ellipsis style={{ maxWidth: 280, color: '#64748b' }}>
          {stripHtml(v)}
        </Text>
      ),
    },
    {
      title: '状态',
      dataIndex: 'isDuplicate',
      width: 90,
      render: (v: number, record: any) =>
        v === 1 ? (
          <Tooltip title="点击查看原始内容">
            <Tag
              icon={<ExclamationCircleOutlined />}
              color="error"
              style={{ cursor: 'pointer', borderRadius: 6 }}
              onClick={() => openDetail(record)}
            >
              重复
            </Tag>
          </Tooltip>
        ) : (
          <Tag
            icon={<CheckCircleOutlined />}
            color="success"
            style={{ borderRadius: 6 }}
          >
            正常
          </Tag>
        ),
    },
    {
      title: '采集时间',
      dataIndex: 'fetchedAt',
      width: 170,
      render: (v: string) => <Text style={{ color: '#94a3b8', fontSize: 13 }}>{v}</Text>,
    },
    {
      title: '操作',
      width: 80,
      render: (_: any, record: any) => (
        <Button
          type="primary"
          ghost
          size="small"
          icon={<EyeOutlined />}
          onClick={() => openDetail(record)}
          style={{ borderRadius: 6 }}
        >
          详情
        </Button>
      ),
    },
  ]

  const filtered = data.filter((item) =>
    (item.title || '').toLowerCase().includes(search.toLowerCase())
  )

  const dupCount = data.filter((d) => d.isDuplicate === 1).length
  const normalCount = data.length - dupCount

  return (
    <div>
      {/* Page header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: 20,
        }}
      >
        <div>
          <Title level={4} style={{ margin: 0, fontWeight: 700 }}>
            内容中心
          </Title>
          <Space style={{ marginTop: 8 }}>
            <Tag icon={<CheckCircleOutlined />} color="success" style={{ borderRadius: 6 }}>
              {normalCount} 正常
            </Tag>
            {dupCount > 0 && (
              <Tag icon={<ExclamationCircleOutlined />} color="error" style={{ borderRadius: 6 }}>
                {dupCount} 重复
              </Tag>
            )}
          </Space>
        </div>
        <Input
          prefix={<SearchOutlined style={{ color: '#94a3b8' }} />}
          placeholder="搜索标题..."
          style={{ width: 280, borderRadius: 8 }}
          onChange={(e) => setSearch(e.target.value)}
          allowClear
        />
      </div>

      <Table
        rowKey="id"
        columns={columns}
        dataSource={filtered}
        loading={loading}
        pagination={{ pageSize: 20, showSizeChanger: false, showTotal: (t) => `共 ${t} 条` }}
        style={{ borderRadius: 12, overflow: 'hidden' }}
      />

      <Drawer
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ fontSize: 18 }}>内容详情</div>
            {selectedContent?.isDuplicate === 1 && (
              <Tag color="error" style={{ borderRadius: 6 }}>重复内容</Tag>
            )}
          </div>
        }
        placement="right"
        width={680}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      >
        {selectedContent && (
          <>
            <Descriptions
              column={1}
              size="small"
              bordered
              labelStyle={{ fontWeight: 600, background: '#f8fafc', width: 100 }}
            >
              <Descriptions.Item label="标题">
                <strong style={{ fontSize: 15 }}>{selectedContent.title}</strong>
              </Descriptions.Item>
              <Descriptions.Item label="平台">
                <Tag style={{ borderRadius: 6 }}>{selectedContent.sourcePlatform}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="作者">{selectedContent.author || '-'}</Descriptions.Item>
              <Descriptions.Item label="来源">
                <a href={selectedContent.sourceUrl} target="_blank" rel="noopener noreferrer" style={{ color: '#6366f1' }}>
                  <LinkOutlined /> {selectedContent.sourceUrl}
                </a>
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                {selectedContent.isDuplicate === 1 ? (
                  <Tag icon={<ExclamationCircleOutlined />} color="error">重复内容</Tag>
                ) : (
                  <Tag icon={<CheckCircleOutlined />} color="success">正常</Tag>
                )}
              </Descriptions.Item>
              {selectedContent.duplicateOf && (
                <Descriptions.Item label="关联原始ID">
                  <Text code>{selectedContent.duplicateOf}</Text>
                </Descriptions.Item>
              )}
              <Descriptions.Item label="采集时间">{selectedContent.fetchedAt}</Descriptions.Item>
              <Descriptions.Item label="内容哈希">
                <Text code style={{ fontSize: 12 }}>
                  {selectedContent.contentHash?.slice(0, 24)}...
                </Text>
              </Descriptions.Item>
            </Descriptions>

            <Divider orientation="left" plain>
              <Text type="secondary" style={{ fontSize: 13 }}>摘要</Text>
            </Divider>
            <div
              style={{
                background: '#f8fafc',
                borderRadius: 10,
                padding: '16px 20px',
                lineHeight: 1.8,
                fontSize: 14,
                color: '#475569',
              }}
              dangerouslySetInnerHTML={{ __html: selectedContent.summary || '无摘要' }}
            />

            {selectedContent.contentBody && (
              <>
                <Divider orientation="left" plain>
                  <Text type="secondary" style={{ fontSize: 13 }}>正文</Text>
                </Divider>
                <div
                  style={{
                    borderRadius: 10,
                    padding: '16px 20px',
                    lineHeight: 1.8,
                    fontSize: 14,
                    color: '#334155',
                    border: '1px solid #f1f5f9',
                  }}
                  dangerouslySetInnerHTML={{ __html: selectedContent.contentBody }}
                />
              </>
            )}

            <Divider orientation="left" plain>
              <Text type="secondary" style={{ fontSize: 13 }}>语义关联推荐</Text>
            </Divider>
            {relatedLoading ? (
              <div style={{ textAlign: 'center', padding: 24 }}><Spin /></div>
            ) : relatedContents.length > 0 ? (
              <List
                size="small"
                dataSource={relatedContents}
                renderItem={(item: any) => (
                  <List.Item
                    style={{
                      padding: '12px 16px',
                      borderRadius: 10,
                      background: '#fafbff',
                      marginBottom: 8,
                      border: '1px solid #f0f0ff',
                    }}
                  >
                    <List.Item.Meta
                      title={<span style={{ fontWeight: 500 }}>{item.title}</span>}
                      description={
                        <Space>
                          <Tag style={{ borderRadius: 6, fontSize: 11 }}>
                            {item.source_platform || item.sourcePlatform || '-'}
                          </Tag>
                          {item.source_url ? (
                            <a href={item.source_url} target="_blank" rel="noopener noreferrer" style={{ color: '#6366f1' }}>
                              查看原文 <LinkOutlined />
                            </a>
                          ) : null}
                        </Space>
                      }
                    />
                    {item.summary && (
                      <Text type="secondary" ellipsis style={{ maxWidth: 220, fontSize: 12 }}>
                        {stripHtml(item.summary)}
                      </Text>
                    )}
                  </List.Item>
                )}
              />
            ) : (
              <div
                style={{
                  textAlign: 'center',
                  padding: 32,
                  color: '#94a3b8',
                  background: '#f8fafc',
                  borderRadius: 10,
                }}
              >
                暂无语义相似内容
              </div>
            )}
          </>
        )}
      </Drawer>
    </div>
  )
}

export default ContentPage
