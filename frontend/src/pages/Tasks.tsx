import { useEffect, useState } from "react";
import {
  Alert,
  App,
  Button,
  Drawer,
  Empty,
  Space,
  Table,
  Tag,
  Typography,
} from "antd";
import request from "../api/request";
import PageHeading from "../components/PageHeading";
import { activeTask, nodeNames, statusName } from "../utils/task";
import { useAuthStore } from "../store/auth";

export default function Tasks() {
  const [items, setItems] = useState<any[]>([]),
    [page, setPage] = useState(1),
    [total, setTotal] = useState(0),
    [loading, setLoading] = useState(false),
    [error, setError] = useState(""),
    [selected, setSelected] = useState<any>(null);
  const { message } = App.useApp(),
    user = useAuthStore((s) => s.user);
  const load = async () => {
    setError("");
    try {
      const r: any = await request.get("/python/agent/tasks", {
        params: { page, size: 10 },
      });
      setItems(r.data.items);
      setTotal(r.data.total);
      setSelected((old: any) =>
        old
          ? r.data.items.find((t: any) => t.task_id === old.task_id) || old
          : null,
      );
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    setLoading(true);
    load();
    const timer = setInterval(load, 3000);
    return () => clearInterval(timer);
  }, [page]);
  const retry = async (task: any) => {
    try {
      await request.post("/python/agent/tasks/" + task.task_id + "/retry");
      message.success("已创建重试任务");
      load();
    } catch (e: any) {
      message.error(e.message);
    }
  };
  return (
    <>
      <PageHeading
        label="AGENT PIPELINE / 任务监控"
        title="每一步都有迹可循"
        subtitle="查看采集、解析、去重、审批和推送进度；错误会保留，失败可重试。"
        extra={<Button onClick={load}>刷新任务</Button>}
      />
      {error && (
        <Alert
          type="error"
          showIcon
          message={error}
          style={{ marginBottom: 20 }}
        />
      )}
      <div className="panel">
        <Table
          rowKey="task_id"
          loading={loading}
          dataSource={items}
          scroll={{ x: 800 }}
          pagination={{
            current: page,
            total,
            pageSize: 10,
            onChange: setPage,
            showSizeChanger: false,
          }}
          columns={[
            {
              title: "任务 ID",
              dataIndex: "task_id",
              render: (v) => <code>{v.slice(0, 12)}</code>,
            },
            { title: "订阅", dataIndex: "subscription_id" },
            {
              title: "状态",
              dataIndex: "status",
              render: (v) => (
                <Tag
                  color={
                    activeTask(v)
                      ? "processing"
                      : v === "completed"
                        ? "success"
                        : v === "failed" || v.startsWith("error")
                          ? "error"
                          : "warning"
                  }
                >
                  {statusName(v)}
                </Tag>
              ),
            },
            {
              title: "新增 / 去重",
              render: (_, r) =>
                `${r.counts?.stored_count ?? 0} / ${r.counts?.duplicate_count ?? 0}`,
            },
            {
              title: "开始时间",
              dataIndex: "created_at",
              render: (v) => new Date(v + "Z").toLocaleString("zh-CN"),
            },
            {
              title: "操作",
              render: (_, r) => (
                <Space>
                  <Button type="link" onClick={() => setSelected(r)}>
                    执行详情
                  </Button>
                  {(r.status === "failed" || r.status.startsWith("error")) && (
                    <Button type="link" onClick={() => retry(r)}>
                      重试
                    </Button>
                  )}
                </Space>
              ),
            },
          ]}
        />
      </div>
      <Drawer
        open={!!selected}
        onClose={() => setSelected(null)}
        title="任务执行链路"
        width={Math.min(1000, window.innerWidth)}
      >
        {selected && (
          <>
            <Space>
              <Tag color="cyan">{statusName(selected.status)}</Tag>
              <Typography.Text copyable>{selected.task_id}</Typography.Text>
            </Space>
            <div className="task-node-grid">
              {Object.entries(nodeNames).map(([key, name], i) => {
                const state: string = selected.nodes?.[key]?.status || "idle";
                return (
                  <div key={key} className={"task-node " + state}>
                    <span className="eyebrow">
                      0{i + 1} / {key}
                    </span>
                    <h4>{name}</h4>
                    <Tag
                      color={
                        state === "success"
                          ? "success"
                          : state === "running"
                            ? "processing"
                            : state === "failed"
                              ? "error"
                              : "default"
                      }
                    >
                      {{
                        idle: "待执行",
                        running: "执行中",
                        success: "已完成",
                        failed: "失败",
                        interrupted: "等待审批",
                      }[state] || state}
                    </Tag>
                  </div>
                );
              })}
            </div>
            {selected.error && (
              <Alert
                showIcon
                type="error"
                message="执行失败"
                description={selected.error}
                style={{ marginBottom: 20 }}
              />
            )}
            {!!selected.source_errors?.length && (
              <Alert
                type="warning"
                showIcon
                message="部分来源未采集成功，其他来源已继续处理"
                description={selected.source_errors.map((e: any) => (
                  <div key={e.url}>
                    {e.url}：{e.error}
                  </div>
                ))}
                style={{ marginBottom: 20 }}
              />
            )}
            {!!selected.quality?.rejected_count && (
              <Alert
                type="warning"
                showIcon
                message={`正文质量检查拦截了 ${selected.quality.rejected_count} 条异常内容`}
                description={selected.quality.rejected?.map((item: any) => (
                  <div key={item.url}>
                    {item.title || item.url}：{item.quality.reasons.join("；")}
                  </div>
                ))}
                style={{ marginBottom: 20 }}
              />
            )}
            {selected.status.startsWith("interrupted") && (
              <Alert
                type="warning"
                showIcon
                message="内容尚未发布"
                description="该批内容需要管理员在审批中心确认，通过后将发布并继续生成简报。"
                style={{ marginBottom: 20 }}
              />
            )}
            {user?.role === "admin" &&
              selected.status.startsWith("interrupted") && (
                <Button
                  onClick={async () => {
                    try {
                      await request.post(
                        "/python/agent/tasks/" + selected.task_id + "/resume",
                      );
                      message.success("恢复请求已提交");
                      load();
                    } catch (e: any) {
                      message.error(e.message);
                    }
                  }}
                >
                  重试恢复已审批任务
                </Button>
              )}
            <Typography.Title level={5}>本次采集简报</Typography.Title>
            {selected.report ? (
              <div className="reading-body">{selected.report}</div>
            ) : (
              <Empty description="简报将在内容审核通过后生成" />
            )}
          </>
        )}
      </Drawer>
    </>
  );
}
