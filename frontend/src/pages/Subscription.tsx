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
export default function SubscriptionPage() {
  const { message } = App.useApp(),
    navigate = useNavigate(),
    [form] = Form.useForm();
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
  });
  const trial = async () => {
    const values = trialValues();
    if (
      !values.rss_feeds.length ||
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
        { timeout: 60000 },
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
            interval: conditions.interval_minutes || 60,
            enableAi: conditions.enable_ai || false,
          }
        : {
            keywords: [],
            rssFeeds: [{ url: "", platform: "rss" }],
            priority: 2,
            interval: 60,
          },
    );
    setOpen(true);
  };
  const save = async () => {
    const v = await form.validateFields();
    setSaving(true);
    try {
      const payload = {
        name: v.name,
        keywords: v.keywords || [],
        rssFeeds: v.rssFeeds,
        sourcePlatforms: [...new Set(v.rssFeeds.map((f: any) => f.platform))],
        matchMode: 1,
        priority: v.priority,
        status: editing?.status ?? 1,
        triggerConditions: JSON.stringify({
          interval_minutes: v.interval,
          enable_ai: !!v.enableAi,
        }),
      };
      if (editing)
        await request.put("/java/subscriptions/" + editing.id, payload);
      else await request.post("/java/subscriptions", payload);
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
      await request.post("/java/subscriptions/" + id + "/trigger");
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
        subtitle="将采集源与关注关键词分别配置，按设定频率持续获取内容。"
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
          message="先添加 RSS 或网页地址。关注关键词留空时采集全部内容，填写后只保留匹配条目。"
          style={{ margin: "16px 0" }}
        />
        <Space wrap style={{ marginBottom: 16 }}>
          <Button onClick={trial} loading={trialing}>
            试采预览
          </Button>
          <Typography.Text type="secondary">
            保存前看看会收到什么（最多前 5 个来源）
          </Typography.Text>
        </Space>
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
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            keywords: [],
            rssFeeds: [{ url: "", platform: "rss" }],
            priority: 2,
            interval: 60,
          }}
        >
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
                  if (!value?.length) throw Error("至少添加一个采集源");
                },
              },
            ]}
          >
            {(fields, { add, remove }, { errors }) => (
              <>
                <Typography.Text strong>采集源</Typography.Text>
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
                        style={{ width: window.innerWidth < 600 ? 190 : 460 }}
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
                  添加采集源
                </Button>
              </>
            )}
          </Form.List>
          <Form.Item name="enableAi" valuePropName="checked">
            <Checkbox>自动生成 AI 翻译与简报（需配置模型）</Checkbox>
          </Form.Item>
          <Form.Item name="keywords" label="关注关键词（可选）">
            <Select
              mode="tags"
              tokenSeparators={[",", "，"]}
              placeholder="输入关键词，回车添加"
            />
          </Form.Item>
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
