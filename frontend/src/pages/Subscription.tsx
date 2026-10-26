import { useEffect, useState } from "react";
import {
  Alert,
  App,
  Button,
  Checkbox,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from "antd";
import {
  PlusOutlined,
  DeleteOutlined,
  SearchOutlined,
  PlayCircleOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import request from "../api/request";
import PageHeading from "../components/PageHeading";
import TrialDrawer from "../components/TrialDrawer";
import AutomaticSources from "../components/AutomaticSources";
import SemanticFields, { semanticValues } from "../components/SemanticFields";
export default function SubscriptionPage() {
  const { message } = App.useApp(),
    navigate = useNavigate(),
    [form] = Form.useForm();
  const semanticMode = Form.useWatch("matchingMode", form) === "semantic";
  const autoMode = Form.useWatch("sourceMode", form) === "auto";
  const sourcePolicy = () =>
    form.getFieldValue("sourceMode") === "auto"
      ? {
          mode: "auto",
          topic: semanticValues(form).enabled
            ? semanticValues(form).intent.slice(0, 200)
            : (form.getFieldValue("focusTopic") || "").trim(),
          language: form.getFieldValue("sourceLanguage") || "zh_first",
          excluded_ids: form.getFieldValue("excludedSourceIds") || [],
        }
      : { mode: "manual" };
  const [data, setData] = useState<any[]>([]),
    [total, setTotal] = useState(0),
    [page, setPage] = useState(1),
    [loading, setLoading] = useState(false),
    [error, setError] = useState(""),
    [open, setOpen] = useState(false),
    [editing, setEditing] = useState<any>(null),
    [saving, setSaving] = useState(false),
    [topic, setTopic] = useState(""),
    [discovering, setDiscovering] = useState(false),
    [sources, setSources] = useState<any[]>([]),
    [selected, setSelected] = useState<string[]>([]),
    [preview, setPreview] = useState<any>(null),
    [triggering, setTriggering] = useState<number | null>(null);
  const [trialOpen, setTrialOpen] = useState(false),
    [trialing, setTrialing] = useState(false),
    [trialResult, setTrialResult] = useState<any>(null),
    [trialError, setTrialError] = useState("");
  const trialValues = () => ({
    rss_feeds: (form.getFieldValue("rssFeeds") || []).map((f: any) => ({
      url: (f.url || "").trim(),
      platform: f.platform || "rss",
    })),
    keywords: form.getFieldValue("keywords") || [],
    source_policy: sourcePolicy(),
    semantic_policy: semanticValues(form),
  });
  const trial = async () => {
    const values = trialValues();
    if (values.semantic_policy.enabled && !values.semantic_policy.intent) {
      message.warning("请描述订阅需求");
      return;
    }
    if (autoMode && !values.source_policy.topic) {
      message.warning("请先填写关注主题");
      return;
    }
    if (
      (!autoMode && !values.rss_feeds.length) ||
      values.rss_feeds.some((f: any) => !/^https?:\/\/\S+$/.test(f.url))
    ) {
      message.warning("请先填写有效的采集源地址");
      return;
    }
    setTrialOpen(true);
    setTrialing(true);
    setTrialError("");
    setTrialResult(null);
    try {
      const r: any = await request.post(
        "/python/subscriptions/trial",
        { ...values, rss_feeds: values.rss_feeds.slice(0, 5) },
        { timeout: semanticMode ? 330000 : 90000 },
      );
      if (JSON.stringify(values) !== JSON.stringify(trialValues())) {
        setTrialError("订阅配置已变化，请重新试采查看最新结果");
        return;
      }
      setTrialResult({ ...r.data, requested_sources: values.rss_feeds.length });
    } catch (e: any) {
      setTrialError(e.message);
    } finally {
      setTrialing(false);
    }
  };
  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const r: any = await request.get("/java/subscriptions", {
        params: { current: page, size: 10 },
      });
      setData(r.data.records);
      setTotal(r.data.total);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    load();
  }, [page]);
  const show = (row: any = null) => {
    setTrialResult(null);
    setTrialError("");
    setEditing(row);
    setSources([]);
    setSelected([]);
    setTopic("");
    let conditions: any = {};
    try {
      conditions = JSON.parse(row?.triggerConditions || "{}");
    } catch {}
    form.resetFields();
    form.setFieldsValue(
      row
        ? {
            ...row,
            matchingMode: conditions.semantic_filter?.enabled
              ? "semantic"
              : "keyword",
            semanticIntent: conditions.semantic_filter?.intent || "",
            semanticExclusions: conditions.semantic_filter?.exclusions || "",
            semanticThreshold: conditions.semantic_filter?.threshold || 75,
            semanticBudget: conditions.semantic_filter?.max_candidates || 20,
            rssFeeds:
              conditions.source_policy?.mode === "auto"
                ? (row.rssFeeds || []).filter((f: any) => f.origin !== "system")
                : row.rssFeeds,
            sourceMode: conditions.source_policy?.mode || "manual",
            focusTopic: conditions.source_policy?.topic || "",
            sourceLanguage: conditions.source_policy?.language || "zh_first",
            excludedSourceIds: conditions.source_policy?.excluded_ids || [],
            interval: conditions.interval_minutes || 60,
            enableAi: conditions.enable_ai || false,
          }
        : {
            keywords: [],
            rssFeeds: [],
            sourceMode: "auto",
            focusTopic: "",
            matchingMode: "semantic",
            semanticIntent: "",
            semanticExclusions: "",
            semanticThreshold: 75,
            semanticBudget: 20,
            sourceLanguage: "zh_first",
            excludedSourceIds: [],
            priority: 2,
            interval: 60,
          },
    );
    setOpen(true);
  };
  const save = async () => {
    if ((autoMode || semanticMode) && !form.getFieldValue("name"))
      form.setFieldValue(
        "name",
        (semanticMode
          ? semanticValues(form).intent
          : (form.getFieldValue("focusTopic") || "").trim()
        ).slice(0, 100),
      );
    const v = await form.validateFields();
    setSaving(true);
    try {
      const payload = {
        name: v.name,
        keywords: v.keywords || [],
        rssFeeds: v.rssFeeds.map((f: any) => ({ ...f, origin: "manual" })),
        sourcePlatforms: [...new Set(v.rssFeeds.map((f: any) => f.platform))],
        matchMode: 1,
        priority: v.priority,
        status: editing?.status ?? 1,
        triggerConditions: JSON.stringify({
          interval_minutes: v.interval,
          enable_ai: !!v.enableAi,
          source_policy: sourcePolicy(),
          semantic_filter: semanticValues(form),
        }),
      };
      if (editing)
        await request.put("/java/subscriptions/" + editing.id, payload, {
          timeout: 150000,
        });
      else
        await request.post("/java/subscriptions", payload, { timeout: 150000 });
      setOpen(false);
      message.success("订阅已保存");
      load();
    } catch (e: any) {
      message.error(e.message);
    } finally {
      setSaving(false);
    }
  };
  const discover = async () => {
    if (!topic.trim()) return;
    setDiscovering(true);
    try {
      const r: any = await request.post(
        "/python/subscriptions/discover-sources",
        { topic, keywords: [] },
      );
      setSources(r.data.sources || []);
      setSelected([]);
    } catch (e: any) {
      message.error(e.message);
    } finally {
      setDiscovering(false);
    }
  };
  const addSelected = () => {
    const next = sources
      .filter((s) => selected.includes(s.id))
      .map((s) => ({ url: s.url, name: s.name, platform: s.platform }));
    const existing = (form.getFieldValue("rssFeeds") || []).filter(
      (f: any) => f.url,
    );
    const seen = new Set(existing.map((f: any) => f.url));
    form.setFieldValue("rssFeeds", [
      ...existing,
      ...next.filter((f) => !seen.has(f.url)),
    ]);
    if (!form.getFieldValue("name")) form.setFieldValue("name", topic);
    message.success("已添加到订阅源列表");
  };
  const trigger = async (id: number) => {
    setTriggering(id);
    try {
      await request.post("/java/subscriptions/" + id + "/trigger", null, {
        timeout: 120000,
      });
      message.success("任务已创建");
      navigate("/tasks");
    } catch (e: any) {
      message.error(e.message);
    } finally {
      setTriggering(null);
    }
  };
  const pause = async (row: any) => {
    try {
      await request.put("/java/subscriptions/" + row.id, {
        ...row,
        status: row.status === 1 ? 0 : 1,
      });
      load();
    } catch (e: any) {
      message.error(e.message);
    }
  };
  return (
    <>
      <PageHeading
        label="SUBSCRIPTIONS / 订阅管理"
        title="建立你的信息雷达"
        subtitle="描述你关心的事情，理解文章语义后推荐相关内容。"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => show()}>
            新建订阅
          </Button>
        }
      />
      {error && (
        <Alert type="error" message={error} style={{ marginBottom: 20 }} />
      )}
      <div className="panel">
        <Table
          rowKey="id"
          dataSource={data}
          loading={loading}
          scroll={{ x: 850 }}
          pagination={{
            current: page,
            total,
            pageSize: 10,
            onChange: setPage,
            showSizeChanger: false,
          }}
          columns={[
            {
              title: "订阅名称",
              dataIndex: "name",
              render: (v: string) => (
                <Typography.Text strong>{v}</Typography.Text>
              ),
            },
            {
              title: "采集源",
              dataIndex: "rssFeeds",
              render: (v: any) => <Tag>{v?.length || 0} 个源</Tag>,
            },
            {
              title: "关注词",
              dataIndex: "keywords",
              render: (v: string[]) =>
                (v || [])
                  .filter((k) => !k.startsWith("http"))
                  .map((k) => <Tag key={k}>{k}</Tag>),
            },
            {
              title: "状态",
              dataIndex: "status",
              render: (v) => (
                <Tag color={v === 1 ? "success" : "default"}>
                  {v === 1 ? "已启用" : "已暂停"}
                </Tag>
              ),
            },
            {
              title: "最近运行",
              dataIndex: "lastRunAt",
              render: (v) =>
                v ? new Date(v + "Z").toLocaleString("zh-CN") : "尚未执行",
            },
            {
              title: "操作",
              render: (_, row) => (
                <Space>
                  <Button
                    type="link"
                    size="small"
                    icon={<PlayCircleOutlined />}
                    disabled={row.status !== 1}
                    loading={triggering === row.id}
                    onClick={() => trigger(row.id)}
                  >
                    采集
                  </Button>
                  <Button type="link" size="small" onClick={() => show(row)}>
                    编辑
                  </Button>
                  <Button type="link" size="small" onClick={() => pause(row)}>
                    {row.status === 1 ? "暂停" : "启用"}
                  </Button>
                  <Popconfirm
                    title="删除此订阅？已采集内容将保留在数据库中。"
                    onConfirm={async () => {
                      try {
                        await request.delete("/java/subscriptions/" + row.id);
                        load();
                      } catch (e: any) {
                        message.error(e.message);
                      }
                    }}
                  >
                    <Button
                      type="text"
                      danger
                      size="small"
                      icon={<DeleteOutlined />}
                    />
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </div>
      <Modal
        open={open}
        title={editing ? "编辑订阅" : "新建订阅"}
        onCancel={() => setOpen(false)}
        onOk={save}
        confirmLoading={saving}
        width={760}
        okText="保存订阅"
        cancelText="取消"
        forceRender
      >
        <Alert
          type="info"
          message="描述订阅需求，系统理解后选择来源并逐篇语义审核；也可添加自己的来源。"
          style={{ margin: "16px 0" }}
        />
        <Space wrap style={{ marginBottom: 16 }}>
          <Button onClick={trial} loading={trialing}>
            试采预览
          </Button>
          <Typography.Text type="secondary">
            保存前预览推荐与拒绝理由（最多前 5 个来源）
          </Typography.Text>
        </Space>
        {!autoMode && (
          <>
            <Space.Compact style={{ width: "100%", marginBottom: 12 }}>
              <Input
                placeholder="例如：人工智能、Python、安全、科技"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                onPressEnter={discover}
              />
              <Button
                icon={<SearchOutlined />}
                loading={discovering}
                onClick={discover}
              >
                推荐订阅源
              </Button>
            </Space.Compact>
            {sources.length > 0 && (
              <div
                style={{
                  maxHeight: 220,
                  overflow: "auto",
                  marginBottom: 16,
                  border: "1px solid #38c9db40",
                  padding: 12,
                  borderRadius: 8,
                }}
              >
                <Typography.Text type="secondary">
                  以下为内置目录推荐，可先预览确认。
                </Typography.Text>
                {sources.map((s) => (
                  <div
                    key={s.id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      margin: "10px 0",
                    }}
                  >
                    <Checkbox
                      checked={selected.includes(s.id)}
                      onChange={(e) =>
                        setSelected((p) =>
                          e.target.checked
                            ? [...p, s.id]
                            : p.filter((x) => x !== s.id),
                        )
                      }
                    />
                    <div style={{ flex: 1 }}>
                      {s.name}
                      <div
                        style={{
                          fontSize: 11,
                          opacity: 0.6,
                          wordBreak: "break-all",
                        }}
                      >
                        {s.url}
                      </div>
                    </div>
                    <Button
                      size="small"
                      onClick={async () => {
                        try {
                          const r: any = await request.get(
                            "/python/subscriptions/preview-feed",
                            { params: { url: s.url } },
                          );
                          setPreview(r.data);
                        } catch (e: any) {
                          message.error(e.message);
                        }
                      }}
                    >
                      预览
                    </Button>
                  </div>
                ))}
                <Button
                  size="small"
                  disabled={!selected.length}
                  onClick={addSelected}
                >
                  添加选中的源
                </Button>
              </div>
            )}
          </>
        )}
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            keywords: [],
            rssFeeds: [],
            sourceMode: "auto",
            sourceLanguage: "zh_first",
            excludedSourceIds: [],
            priority: 2,
            interval: 60,
          }}
        >
          <SemanticFields form={form} />
          <AutomaticSources form={form} />
          <Form.Item
            name="name"
            label="订阅名称"
            rules={[{ required: true, message: "请输入名称" }, { max: 100 }]}
          >
            <Input maxLength={100} />
          </Form.Item>
          <Form.List
            name="rssFeeds"
            rules={[
              {
                validator: async (_, value) => {
                  if (!value?.length && !autoMode)
                    throw Error("至少添加一个采集源");
                },
              },
            ]}
          >
            {(fields, { add, remove }, { errors }) => (
              <>
                <Typography.Text strong>
                  {autoMode ? "额外来源（可选）" : "采集源"}
                </Typography.Text>
                {fields.map((field) => (
                  <Space
                    key={field.key}
                    style={{ display: "flex", marginTop: 10 }}
                    align="start"
                  >
                    <Form.Item name={[field.name, "platform"]}>
                      <Select
                        style={{ width: 95 }}
                        options={[
                          { label: "RSS", value: "rss" },
                          { label: "网页", value: "web" },
                          { label: "JSON API", value: "api" },
                        ]}
                      />
                    </Form.Item>
                    <Form.Item
                      name={[field.name, "url"]}
                      rules={[
                        { required: true, message: "请输入源地址" },
                        { type: "url", message: "请输入有效 URL" },
                        {
                          pattern: /^https?:\/\//,
                          message: "仅支持 HTTP/HTTPS",
                        },
                      ]}
                    >
                      <Input
                        placeholder="https://example.com/feed.xml"
                        style={{ width: "min(460px, calc(100vw - 230px))" }}
                      />
                    </Form.Item>
                    <Button
                      icon={<DeleteOutlined />}
                      onClick={() => remove(field.name)}
                    />
                  </Space>
                ))}
                <Form.ErrorList errors={errors} />
                <Button
                  type="dashed"
                  onClick={() => add({ platform: "rss", url: "" })}
                  icon={<PlusOutlined />}
                  style={{ marginBottom: 20 }}
                >
                  {autoMode ? "添加自己的来源" : "添加采集源"}
                </Button>
              </>
            )}
          </Form.List>
          <Form.Item name="enableAi" valuePropName="checked">
            <Checkbox>额外生成 AI 翻译与简报（可选，与语义筛选独立）</Checkbox>
          </Form.Item>
          {!semanticMode && (
            <Form.Item name="keywords" label="关注关键词（兼容模式，可选）">
              <Select
                mode="tags"
                tokenSeparators={[",", "，"]}
                placeholder="输入关键词，回车添加"
              />
            </Form.Item>
          )}
          <Space size={24}>
            <Form.Item
              name="interval"
              label="采集间隔（分钟）"
              rules={[{ required: true }]}
            >
              <InputNumber min={15} max={10080} />
            </Form.Item>
            <Form.Item name="priority" label="优先级">
              <Select
                style={{ width: 120 }}
                options={[
                  { label: "高", value: 1 },
                  { label: "中", value: 2 },
                  { label: "低", value: 3 },
                ]}
              />
            </Form.Item>
          </Space>
        </Form>
      </Modal>
      <TrialDrawer
        open={trialOpen}
        onClose={() => setTrialOpen(false)}
        loading={trialing}
        data={trialResult}
        error={trialError}
        onRetry={trial}
      />
      <Modal
        open={!!preview}
        title="订阅源预览"
        footer={null}
        onCancel={() => setPreview(null)}
      >
        {preview?.entries?.length
          ? preview.entries.map((e: any) => (
              <div key={e.link} style={{ marginBottom: 16 }}>
                <Typography.Text strong>{e.title}</Typography.Text>
                <p>{e.summary}</p>
              </div>
            ))
          : "该订阅源暂时没有条目"}
      </Modal>
    </>
  );
}
