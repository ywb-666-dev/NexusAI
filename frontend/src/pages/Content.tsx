import { useEffect, useState } from 'react'
import { Table, Button, Tag, Input } from 'antd'
import request from '../api/request'

function ContentPage() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')

  const fetchData = async () => {
    setLoading(true)
    try {
      const res: any = await request.get('/java/contents')
      setData(res.data?.items || [])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 280 },
    { title: '标题', dataIndex: 'title' },
    { title: '平台', dataIndex: 'sourcePlatform' },
    { title: '作者', dataIndex: 'author' },
    {
      title: '重复',
      dataIndex: 'isDuplicate',
      render: (v: number) => (v === 1 ? <Tag color="red">重复</Tag> : <Tag color="green">正常</Tag>),
    },
    { title: '采集时间', dataIndex: 'fetchedAt' },
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
      <Table rowKey="id" columns={columns} dataSource={filtered} loading={loading} />
    </div>
  )
}

export default ContentPage
