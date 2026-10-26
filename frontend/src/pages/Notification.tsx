import { useEffect, useState } from "react";
import {
  Alert,
  App,
  Button,
  Empty,
  List,
  Pagination,
  Space,
  Tag,
  Typography,
} from "antd";
import request from "../api/request";
import PageHeading from "../components/PageHeading";
export default function NotificationPage() {
  const [data, setData] = useState<any[]>([]),
    [page, setPage] = useState(1),
    [total, setTotal] = useState(0),
    [loading, setLoading] = useState(false),
    [error, setError] = useState("");
  const { message } = App.useApp();
  const load = async () => {
    setLoading(true);
    try {
      const r: any = await request.get("/java/notifications", {
        params: { current: page, size: 10 },
      });
      setData(r.data.records);
      setTotal(r.data.total);
      setError("");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    load();
  }, [page]);
  const mark = async (id?: number) => {
    try {
      await request.post(
        id
          ? "/java/notifications/" + id + "/read"
          : "/java/notifications/read-all",
      );
      window.dispatchEvent(new Event("nexus:notifications"));
      load();
    } catch (e: any) {
      message.error(e.message);
    }
  };
  return (
    <>
      <PageHeading
        label="INBOX / 通知中心"
        title="最新动态，不再错过"
        subtitle="采集结果和任务提醒集中查看。"
        extra={<Button onClick={() => mark()}>全部标记已读</Button>}
      />
      {error && (
        <Alert type="error" message={error} style={{ marginBottom: 20 }} />
      )}
      <div className="panel">
        <List
          loading={loading}
          dataSource={data}
          locale={{ emptyText: <Empty description="暂时没有通知" /> }}
          renderItem={(item) => (
            <List.Item
              actions={
                !item.isRead
                  ? [
                      <Button
                        key="read"
                        size="small"
                        onClick={() => mark(item.id)}
                      >
                        标记已读
                      </Button>,
                    ]
                  : []
              }
            >
              <List.Item.Meta
                title={
                  <Space>
                    {!item.isRead && <Tag color="cyan">未读</Tag>}
                    <Typography.Text strong={!item.isRead}>
                      {item.title}
                    </Typography.Text>
                  </Space>
                }
                description={
                  <>
                    <p>{item.content}</p>
                    <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                      {item.createdAt
                        ? new Date(item.createdAt + "Z").toLocaleString("zh-CN")
                        : ""}
                    </Typography.Text>
                  </>
                }
              />
            </List.Item>
          )}
        />
        <Pagination
          current={page}
          total={total}
          pageSize={10}
          onChange={setPage}
          showSizeChanger={false}
          hideOnSinglePage
          style={{ marginTop: 20 }}
        />
      </div>
    </>
  );
}
