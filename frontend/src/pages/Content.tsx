import { useEffect, useState } from 'react'
import { Table, Tag, Input } from 'antd'
import request from '../api/request'

function stripHtml(html: string | undefined | null): string {
  if (!html) return ''
  const doc = new DOMParser().parseFromString(html, 'text/html')
  return doc.body.textContent || ''
}

function ContentPage() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')

  const fetchData = async () => {
    setLoading(true)
    try {
      const res: any = await request.get('/java/contents?size=50')
      setData(res.data?.records ?? res.data?.items ?? [])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const columns = [
    { title: '标题', dataIndex: 'title', width: 300 },
    { title: '平台', dataIndex: 'sourcePlatform', width: 80 },
    { title: '作者', dataIndex: 'author', width: 120 },
    { title: '摘要', dataIndex: 'summary', ellipsis: true, render: (v: string) => stripHtml(v) },
    {
      title: '重复',
      dataIndex: 'isDuplicate',
      width: 80,
      render: (v: number) => (v === 1 ? <Tag color="red">重复</Tag> : <Tag color="green">正常</Tag>),
    },
    { title: '采集时间', dataIndex: 'fetchedAt', width: 180 },
  ]

  const filtered = data.filter((item) =>
    (item.title || '').toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div>
      <h2>内容中心</h2>
      <Input.Search
        placeholder="搜索标题"
        style={{ width: 300, marginTop: 16, marginBottom: 16 }}
        onChange={(e) => setSearch(e.target.value)}
      />
      <Table
        rowKey="id"
        columns={columns}
        dataSource={filtered}
        loading={loading}
        expandable={{
          expandedRowRender: (record) => (
            <div style={{ padding: '8px 0' }}>
              <p style={{ marginBottom: 8 }}><strong>来源：</strong>
                <a href={record.sourceUrl} target="_blank" rel="noopener noreferrer">{record.sourceUrl}</a>
              </p>
              <div style={{ lineHeight: 1.7 }}>
                <div dangerouslySetInnerHTML={{ __html: record.summary || '' }} />
              </div>
            </div>
          ),
          rowExpandable: (record) => !!(record.summary || record.contentBody),
        }}
      />
    </div>
  )
}

export default ContentPage
