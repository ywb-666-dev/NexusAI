import { useEffect, useState } from "react";
import {
  Alert,
  App,
  Button,
  Card,
  Collapse,
  Empty,
  Pagination,
  Popconfirm,
  Segmented,
  Skeleton,
  Space,
  Switch,
  Tag,
  Typography,
} from "antd";
import {
  FileTextOutlined,
  ReloadOutlined,
  SendOutlined,
  DownloadOutlined,
} from "@ant-design/icons";
import { useSearchParams } from "react-router-dom";
import request from "../api/request";
import PageHeading from "../components/PageHeading";

const labels: Record<string, string> = {
  queued: "排队中",
  generating: "正在整理",
  ready: "已完成",
  failed: "生成失败",
};
const time = (v: string) =>
  new Date(v).toLocaleString("zh-CN", {
    timeZone: "Asia/Shanghai",
    hour12: false,
  });
export default function Briefings() {
  const { message } = App.useApp();
  const [params, setParams] = useSearchParams();
  const selected = params.get("id");
  const [hours, setHours] = useState(24),
    [items, setItems] = useState<any[]>([]),
    [total, setTotal] = useState(0),
    [page, setPage] = useState(1);
  const [detail, setDetail] = useState<any>(null),
    [prefs, setPrefs] = useState({ enabled: false, pushEnabled: false });
  const [busy, setBusy] = useState(false),
    [saving, setSaving] = useState(false),
    [loading, setLoading] = useState(true),
    [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0),
    [detailLoading, setDetailLoading] = useState(false);
  useEffect(() => {
    let live = true;
    setLoading(true);
    Promise.all([
      request.get("/python/briefings", { params: { page, size: 8 } }),
      request.get("/python/briefings/preferences"),
    ])
      .then(([list, pref]: any[]) => {
        if (live) {
          setItems(list.data.items);
          setTotal(list.data.total);
          setPrefs(pref.data);
          setError("");
        }
      })
      .catch((e) => {
        if (live) setError(e.message);
      })
      .finally(() => {
        if (live) setLoading(false);
      });
    return () => {
      live = false;
    };
  }, [page, refresh]);
  useEffect(() => {
    if (!selected) {
      setDetail(null);
      return;
    }
    let live = true;
    setDetailLoading(true);
    setDetail(null);
    request
      .get("/python/briefings/" + selected)
      .then((r: any) => {
        if (live) {
          setDetail(r.data);
          setError("");
        }
      })
      .catch((e) => {
        if (live) setError(e.message);
      })
      .finally(() => {
        if (live) setDetailLoading(false);
      });
    return () => {
      live = false;
    };
  }, [selected, refresh]);
  const running =
    items.some((r) => ["queued", "generating"].includes(r.status)) ||
    (detail && ["queued", "generating"].includes(detail.status));
  useEffect(() => {
    if (!running) return;
    const timer = setInterval(() => setRefresh((v) => v + 1), 4000);
    return () => clearInterval(timer);
  }, [running]);
  const generate = async () => {
    setBusy(true);
    try {
      const r: any = await request.post("/python/briefings", { hours });
      setPage(1);
      setParams({ id: r.data.id });
      setRefresh((v) => v + 1);
      message.success("已开始整理，可稍后回来阅读");
    } catch (e: any) {
      message.error(e.message);
    } finally {
      setBusy(false);
    }
  };
  const save = async (next: typeof prefs) => {
    setSaving(true);
    try {
      await request.put("/python/briefings/preferences", next);
      setPrefs(next);
      message.success("简报设置已保存");
    } catch (e: any) {
      message.error(e.message);
    } finally {
      setSaving(false);
    }
  };
  const push = async () => {
    setBusy(true);
    try {
      const r: any = await request.post(`/python/briefings/${detail.id}/push`);
      message.success(r.message);
    } catch (e: any) {
      message.error(e.message);
    } finally {
      setBusy(false);
    }
  };
  const report = detail?.report;
  const sources = Object.fromEntries(
    (report?.sources || []).map((s: any) => [s.id, s]),
  );
  const download = () => {
    const lines = [
      `# ${detail.headline}`,
      "",
      `采集范围（北京时间）：${time(detail.periodStart)} — ${time(detail.periodEnd)}`,
      "",
      report.overview,
      "",
      "以下关注建议由模型生成，请结合原文核实。",
    ];
    for (const event of report.events || []) {
      lines.push(
        "",
        `## ${event.title}`,
        "",
        event.summary,
        "",
        `关注建议：${event.attention}`,
      );
      for (const c of event.citations) {
        const s: any = sources[c.id];
        lines.push("", `> ${c.quote}`, "", `${s.title}\n${s.url}`);
      }
    }
    const url = URL.createObjectURL(
      new Blob([lines.join("\n")], { type: "text/markdown;charset=utf-8" }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = `NexusAI-简报-${detail.id.slice(0, 8)}.md`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  return (
    <>
      <PageHeading
        label="BRIEFING / 个人情报"
        title="把信息整理成值得关注的重点"
        subtitle="跨订阅汇总语义推荐，合并事件、追溯原文，让每次阅读都有方向。"
        extra={
          <Space wrap>
            <Segmented
              value={hours}
              options={[
                { label: "近 24 小时", value: 24 },
                { label: "近 7 天", value: 168 },
              ]}
              onChange={(v) => setHours(Number(v))}
            />
            <Button
              type="primary"
              icon={<FileTextOutlined />}
              loading={busy}
              disabled={!!running}
              onClick={generate}
            >
              生成个人简报
            </Button>
          </Space>
        }
      />
      {error && (
        <Alert
          type="error"
          message={error}
          action={
            <Button onClick={() => setRefresh((v) => v + 1)}>重试</Button>
          }
          style={{ marginBottom: 16 }}
        />
      )}
      <div className="panel" style={{ marginBottom: 20 }}>
        <Space wrap size="large">
          <Space>
            <Switch
              checked={prefs.enabled}
              loading={saving}
              onChange={(enabled) => save({ ...prefs, enabled })}
              aria-label="每日自动简报"
            />
            <span>每日 08:00 自动整理（北京时间）</span>
          </Space>
          <Space>
            <Switch
              checked={prefs.pushEnabled}
              loading={saving}
              disabled={!prefs.enabled}
              onChange={(pushEnabled) => save({ ...prefs, pushEnabled })}
              aria-label="自动推送简报"
            />
            <span>同时推送到已启用的机器人</span>
          </Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => setRefresh((v) => v + 1)}
          >
            刷新
          </Button>
        </Space>
        <Typography.Paragraph
          type="secondary"
          style={{ marginBottom: 0, marginTop: 12 }}
        >
          仅汇总所选采集时间范围内已发布且通过语义筛选的内容，最多选取 40
          篇；关键词模式内容不纳入。开启自动整理后，从下一个 08:00 起生成近 24
          小时简报；没有内容时不调用模型、不向机器人推送。
        </Typography.Paragraph>
      </div>
      <div className="briefing-layout">
        <div>
          <Typography.Title level={4}>历史简报</Typography.Title>
          {loading && !items.length ? (
            <Skeleton active />
          ) : !items.length ? (
            <Empty description="还没有简报，先运行语义订阅，再生成第一份简报" />
          ) : (
            <Space direction="vertical" style={{ width: "100%" }}>
              {items.map((r) => (
                <Card
                  key={r.id}
                  size="small"
                  hoverable
                  onClick={() => setParams({ id: r.id })}
                  style={{
                    borderColor: selected === r.id ? "#24c6c8" : undefined,
                  }}
                >
                  <Button
                    type="link"
                    style={{
                      padding: 0,
                      height: "auto",
                      whiteSpace: "normal",
                      textAlign: "left",
                    }}
                    onClick={() => setParams({ id: r.id })}
                  >
                    {r.headline}
                  </Button>
                  <div style={{ marginTop: 10 }}>
                    <Tag
                      color={
                        r.status === "ready"
                          ? "success"
                          : r.status === "failed"
                            ? "error"
                            : "processing"
                      }
                    >
                      {labels[r.status]}
                    </Tag>
                    <Typography.Text type="secondary">
                      {r.hours === 24 ? "24 小时" : "7 天"} · {r.eventCount}{" "}
                      个重点
                    </Typography.Text>
                  </div>
                  <Typography.Text type="secondary">
                    {time(r.createdAt)}
                  </Typography.Text>
                </Card>
              ))}
            </Space>
          )}
          <Pagination
            size="small"
            current={page}
            pageSize={8}
            total={total}
            onChange={setPage}
            style={{ marginTop: 16 }}
          />
        </div>
        <div style={{ minWidth: 0 }}>
          {detailLoading ? (
            <Skeleton active paragraph={{ rows: 8 }} />
          ) : !detail ? (
            <div className="panel">
              <Empty description="选择一份简报，查看重点与原文依据" />
            </div>
          ) : detail.status === "failed" ? (
            <Alert
              type="error"
              message="本次简报未完成"
              description={detail.error}
              action={
                <Button onClick={generate} loading={busy}>
                  重新生成
                </Button>
              }
            />
          ) : detail.status !== "ready" ? (
            <div className="panel">
              <Alert
                type="info"
                showIcon
                message="正在整理你的个人情报"
                description="页面会自动更新，也可以离开后从历史简报返回查看。"
              />
              <Skeleton active style={{ marginTop: 24 }} />
            </div>
          ) : (
            <div className="panel">
              <Space
                wrap
                style={{ width: "100%", justifyContent: "space-between" }}
              >
                <Tag color="cyan">
                  {report.method === "llm" ? "AI 情报简报" : "本期暂无内容"}
                </Tag>
                <Space>
                  <Button icon={<DownloadOutlined />} onClick={download}>
                    导出 Markdown
                  </Button>
                  <Popconfirm
                    title="推送这份简报？"
                    description="发送到你已启用的飞书或钉钉机器人，已投递过的渠道会跳过。"
                    onConfirm={push}
                    okText="发送"
                    cancelText="取消"
                  >
                    <Button
                      icon={<SendOutlined />}
                      disabled={!report.events?.length}
                      loading={busy}
                    >
                      推送简报
                    </Button>
                  </Popconfirm>
                </Space>
              </Space>
              <Typography.Title level={2} style={{ overflowWrap: "anywhere" }}>
                {detail.headline}
              </Typography.Title>
              <Typography.Paragraph type="secondary">
                {time(detail.periodStart)} — {time(detail.periodEnd)}
                （北京时间，按采集时间）
              </Typography.Paragraph>
              <Typography.Paragraph>{report.overview}</Typography.Paragraph>
              <Space wrap>
                <Tag>{report.sources.length} 篇资料</Tag>
                <Tag>{report.events.length} 个重点</Tag>
                <Tag>重复或无效资料 {report.deduplicatedCount} 篇</Tag>
                {report.unselectedCount > 0 && (
                  <Tag color="warning">
                    另有 {report.unselectedCount} 篇未纳入本期预算
                  </Tag>
                )}
              </Space>
              {!!report.events.length && (
                <Alert
                  type="info"
                  showIcon
                  message="摘要和关注建议由模型整理，请结合原文核实；引文校验不代表事实已获独立验证。"
                  style={{ margin: "20px 0" }}
                />
              )}
              {report.events.map((event: any, i: number) => (
                <section
                  key={i}
                  style={{
                    padding: "20px 0",
                    borderTop: "1px solid var(--border, #263448)",
                  }}
                >
                  <Typography.Title level={4}>
                    {i + 1}. {event.title}
                  </Typography.Title>
                  <Typography.Paragraph>{event.summary}</Typography.Paragraph>
                  <Typography.Paragraph>
                    <Typography.Text strong>关注建议：</Typography.Text>
                    {event.attention}
                  </Typography.Paragraph>
                  <Collapse
                    ghost
                    items={[
                      {
                        key: "sources",
                        label: `查看 ${event.citations.length} 篇原文与依据`,
                        children: (
                          <Space direction="vertical" style={{ width: "100%" }}>
                            {event.citations.map((c: any) => {
                              const s: any = sources[c.id];
                              return (
                                <Card size="small" key={c.id}>
                                  <a
                                    href={s.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                  >
                                    {s.title}
                                  </a>
                                  <div>
                                    <Tag>{s.subscription}</Tag>
                                    <Tag>相关度 {s.score}</Tag>
                                  </div>
                                  <Typography.Paragraph
                                    style={{ marginTop: 10 }}
                                  >
                                    <blockquote
                                      style={{
                                        margin: 0,
                                        paddingLeft: 12,
                                        borderLeft: "2px solid #24c6c8",
                                      }}
                                    >
                                      {c.quote}
                                    </blockquote>
                                  </Typography.Paragraph>
                                  <Typography.Text type="secondary">
                                    推荐理由：{s.reason}
                                  </Typography.Text>
                                </Card>
                              );
                            })}
                          </Space>
                        ),
                      },
                    ]}
                  />
                </section>
              ))}
              {!!report.omitted.length && (
                <Collapse
                  ghost
                  items={[
                    {
                      key: "omitted",
                      label: `${report.omitted.length} 篇未列为重点的资料`,
                      children: report.omitted.map((o: any) => (
                        <Typography.Paragraph key={o.id}>
                          <a
                            href={sources[o.id]?.url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            {sources[o.id]?.title}
                          </a>
                          ：{o.reason}
                        </Typography.Paragraph>
                      )),
                    },
                  ]}
                />
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
