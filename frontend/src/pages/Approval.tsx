import { useEffect, useState } from "react";
import {
  Alert,
  App,
  Button,
  Drawer,
  Input,
  Space,
  Table,
  Tag,
  Typography,
} from "antd";
import request from "../api/request";
import PageHeading from "../components/PageHeading";
export default function ApprovalPage() {
  const { message } = App.useApp(),
    [data, setData] = useState<any[]>([]),
    [loading, setLoading] = useState(false),
    [error, setError] = useState(""),
    [selected, setSelected] = useState<any>(null),
    [contents, setContents] = useState<any[]>([]),
    [comment, setComment] = useState(""),
    [busy, setBusy] = useState(false),
    [page, setPage] = useState(1),
    [total, setTotal] = useState(0);
  const load = async () => {
    setLoading(true);
    try {
      const r: any = await request.get("/java/approvals/pending", {
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
  const open = async (row: any) => {
    setSelected(row);
    setComment("");
    setContents([]);
    try {
      const context =
        typeof row.context === "string" ? JSON.parse(row.context) : row.context;
      const results: any[] = await Promise.all(
        (context?.content_ids || [])
          .slice(0, 20)
          .map((id: string) => request.get("/python/contents/pending/" + id)),
      );
      setContents(results.map((r) => r.data));
    } catch (e: any) {
      message.error(e.message);
    }
  };
  const decide = async (approved: boolean) => {
    if (!approved && !comment.trim()) {
      message.warning("请填写拒绝原因");
      return;
    }
    setBusy(true);
    try {
      await request.post(
        "/java/approvals/" + selected.id + (approved ? "/approve" : "/reject"),
        { comment },
      );
      message.success(
        approved ? "审批通过，任务继续执行" : "已拒绝，该批内容不会发布",
      );
      setSelected(null);
      load();
    } catch (e: any) {
      message.error(e.message);
      load();
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <PageHeading
        label="HUMAN REVIEW / 审批中心"
        title="关键决策，交给你确认"
        subtitle="高风险内容保持待审，只有通过审批后才会发布、生成简报和推送。"
      />
      {error && (
        <Alert type="error" message={error} style={{ marginBottom: 20 }} />
      )}
      <div className="panel">
        <Table
          rowKey="id"
          loading={loading}
          dataSource={data}
          pagination={{
            current: page,
            total,
            pageSize: 10,
            onChange: setPage,
            showSizeChanger: false,
          }}
          columns={[
            { title: "工单", dataIndex: "id" },
            {
              title: "任务",
              dataIndex: "taskId",
              render: (v) => <code>{v.slice(0, 12)}</code>,
            },
            {
              title: "风险",
              dataIndex: "riskLevel",
              render: (v) => (
                <Tag color={v === 3 ? "red" : "orange"}>
                  {v === 3 ? "高风险" : "中风险"}
                </Tag>
              ),
            },
            { title: "评估说明", dataIndex: "comment", ellipsis: true },
            {
              title: "操作",
              render: (_, r) => (
                <Button type="link" onClick={() => open(r)}>
                  查看并审批
                </Button>
              ),
            },
          ]}
        />
      </div>
      <Drawer
        title="内容审核"
        open={!!selected}
        onClose={() => setSelected(null)}
        width={Math.min(760, window.innerWidth)}
      >
        {selected && (
          <>
            <Alert type="warning" message={selected.comment} />
            {contents.map((c) => (
              <section key={c.id} style={{ margin: "24px 0" }}>
                <Typography.Title level={5}>{c.title}</Typography.Title>
                <Typography.Paragraph type="secondary">
                  {c.sourceUrl}
                </Typography.Paragraph>
                <div className="reading-body">{c.contentBody || c.summary}</div>
              </section>
            ))}
            <Input.TextArea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="填写审批意见，拒绝时必填"
              maxLength={500}
              rows={3}
            />
            <Space style={{ marginTop: 20 }}>
              <Button
                type="primary"
                loading={busy}
                onClick={() => decide(true)}
              >
                通过并发布
              </Button>
              <Button danger loading={busy} onClick={() => decide(false)}>
                拒绝发布
              </Button>
            </Space>
          </>
        )}
      </Drawer>
    </>
  );
}
