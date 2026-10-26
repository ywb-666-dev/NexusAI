import { useEffect, useState } from "react";
import {
  Alert,
  App,
  Button,
  Drawer,
  Empty,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from "antd";
import {
  CheckCircleOutlined,
  DownloadOutlined,
  PlusOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import request from "../api/request";
import PageHeading from "../components/PageHeading";

type Source = {
  id: string;
  name: string;
  url: string;
  homepage: string;
  language: string;
  category: string;
  description: string;
  platform: string;
  health: {
    status: string;
    checked_at: string | null;
    last_success_at: string | null;
    latency_ms: number | null;
    entry_count: number;
    error: string | null;
    samples: { title: string; url: string; summary: string }[];
  };
};
const states: Record<string, { label: string; color: string }> = {
  available: { label: "可用", color: "success" },
  empty: { label: "有效但暂无条目", color: "warning" },
  unchecked: { label: "待检测", color: "default" },
  failed: { label: "检测失败", color: "error" },
};

export default function Sources() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const [items, setItems] = useState<Source[]>([]),
    [total, setTotal] = useState(0),
    [page, setPage] = useState(1);
  const [q, setQ] = useState(""),
    [category, setCategory] = useState(""),
    [language, setLanguage] = useState(""),
    [status, setStatus] = useState("");
  const [categories, setCategories] = useState<Record<string, string>>({}),
    [stats, setStats] = useState<Record<string, number>>({});
  const [selected, setSelected] = useState<Source[]>([]),
    [loading, setLoading] = useState(false),
    [error, setError] = useState("");
  const [checking, setChecking] = useState(false),
    [checked, setChecked] = useState(0),
    [preview, setPreview] = useState<Source | null>(null);
  const [open, setOpen] = useState(false),
    [saving, setSaving] = useState(false),
    [subscriptions, setSubscriptions] = useState<any[]>([]);
  const [form] = Form.useForm();
  const filters = { q, category, language, status };
  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const r: any = await request.get("/python/sources", {
        params: { ...filters, page, size: 24 },
      });
      setItems(r.data.items);
      setTotal(r.data.total);
      setCategories(r.data.categories);
      setStats(r.data.stats);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    load();
  }, [q, category, language, status, page]);
  const check = async (sources: Source[], showPreview = false) => {
    setChecking(true);
    setChecked(0);
    try {
      for (let i = 0; i < sources.length; i += 4) {
        const r: any = await request.post(
          "/python/sources/check",
          { ids: sources.slice(i, i + 4).map((s) => s.id) },
          { timeout: 120000 },
        );
        if (showPreview) setPreview({ ...sources[0], health: r.data.items[0] });
        setChecked(Math.min(i + 4, sources.length));
      }
      await load();
      message.success("检测完成，结果已保存（5 分钟内复用最近结果）");
    } catch (e: any) {
      message.error(e.message);
    } finally {
      setChecking(false);
    }
  };
  const choose = async () => {
    if (!selected.length) return;
    if (selected.length > 20) {
      message.warning("每个订阅最多 20 个来源，请减少选择");
      return;
    }
    try {
      const r: any = await request.get("/java/subscriptions", {
        params: { current: 1, size: 100 },
      });
      setSubscriptions(r.data.records);
      form.resetFields();
      form.setFieldsValue({
        target: "new",
        name: "我的信息订阅",
        interval: 60,
      });
      setOpen(true);
    } catch (e: any) {
      message.error(e.message);
    }
  };
  const save = async () => {
    const v = await form.validateFields();
    setSaving(true);
    try {
      const existing = subscriptions.find((s) => s.id === v.target);
      const feeds = [...(existing?.rssFeeds || [])];
      const seen = new Set(feeds.map((s: any) => s.url));
      for (const source of selected) {
        if (!seen.has(source.url)) {
          feeds.push({
            url: source.url,
            name: source.name,
            platform: source.platform,
          });
          seen.add(source.url);
        }
      }
      if (feeds.length > 20) {
        message.warning("合并后超过 20 个来源，请分成多个订阅");
        return;
      }
      const payload = {
        ...(existing || {}),
        name: existing?.name || v.name,
        rssFeeds: feeds,
        sourcePlatforms: [...new Set(feeds.map((s: any) => s.platform))],
        keywords: existing?.keywords || [],
        matchMode: existing?.matchMode || 1,
        priority: existing?.priority || 2,
        status: existing?.status ?? 1,
        triggerConditions:
          existing?.triggerConditions ||
          JSON.stringify({ interval_minutes: 60, enable_ai: false }),
      };
      if (existing)
        await request.put("/java/subscriptions/" + existing.id, payload);
      else await request.post("/java/subscriptions", payload);
      message.success("已加入订阅，可在我的订阅中手动采集或等待调度");
      setOpen(false);
      setSelected([]);
    } catch (e: any) {
      message.error(e.message);
    } finally {
      setSaving(false);
    }
  };
  const exportFeeds = async () => {
    try {
      const blob: any = await request.get("/python/sources/export.opml", {
        params: filters,
        responseType: "blob",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "nexusai-sources.opml";
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e: any) {
      message.error(e.message);
    }
  };
  return (
    <>
      <PageHeading
        label="SOURCES / 数据源中心"
        title="构建你的信息版图"
        subtitle="从公开 RSS 与 Atom 频道选择来源，检测可用性，再组成自己的订阅。"
        extra={
          <Button onClick={() => navigate("/subscriptions")}>
            管理我的订阅
          </Button>
        }
      />
      <div className="stat-grid" style={{ marginBottom: 20 }}>
        {[
          ["订阅频道", stats.total],
          ["来源域名", stats.hosts],
          ["中文频道", stats.chinese],
          ["最近检测可用", stats.available || 0],
        ].map(([label, value]) => (
          <div className="stat-panel" key={label}>
            <Typography.Text type="secondary">{label}</Typography.Text>
            <div style={{ fontSize: 32, fontWeight: 700, marginTop: 8 }}>
              {value ?? "—"}
            </div>
          </div>
        ))}
      </div>
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="可用性以当前服务器最近检测为准；有效的空订阅不代表失效。部分来源仅提供摘要，付费正文和 PDF 不保证可提取。选择来源不会立即采集。"
      />
      {error && (
        <Alert
          type="error"
          message={error}
          action={<Button onClick={load}>重试</Button>}
          style={{ marginBottom: 16 }}
        />
      )}
      <div className="panel">
        <Space wrap style={{ marginBottom: 16 }}>
          <Input.Search
            aria-label="搜索数据源"
            placeholder="名称、主题或域名"
            allowClear
            onSearch={(v) => {
              setQ(v);
              setPage(1);
            }}
            style={{ width: 240 }}
          />
          <Select
            aria-label="来源分类"
            value={category}
            style={{ width: 155 }}
            onChange={(v) => {
              setCategory(v);
              setPage(1);
            }}
            options={[
              { value: "", label: "全部分类" },
              ...Object.entries(categories).map(([value, label]) => ({
                value,
                label,
              })),
            ]}
          />
          <Select
            aria-label="来源语言"
            value={language}
            style={{ width: 110 }}
            onChange={(v) => {
              setLanguage(v);
              setPage(1);
            }}
            options={[
              { value: "", label: "全部语言" },
              { value: "zh", label: "中文" },
              { value: "en", label: "英文" },
            ]}
          />
          <Select
            aria-label="来源状态"
            value={status}
            style={{ width: 155 }}
            onChange={(v) => {
              setStatus(v);
              setPage(1);
            }}
            options={[
              { value: "", label: "全部状态" },
              ...Object.entries(states).map(([value, s]) => ({
                value,
                label: s.label,
              })),
            ]}
          />
          <Button icon={<ReloadOutlined />} onClick={load}>
            刷新
          </Button>
          <Button icon={<DownloadOutlined />} onClick={exportFeeds}>
            导出 OPML
          </Button>
        </Space>
        <Space wrap style={{ marginBottom: 16 }}>
          <Typography.Text>已选 {selected.length} / 20</Typography.Text>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            disabled={!selected.length || checking || selected.length > 20}
            onClick={choose}
          >
            加入订阅
          </Button>
          <Button
            icon={<CheckCircleOutlined />}
            disabled={!selected.length || selected.length > 20}
            loading={checking}
            onClick={() => check(selected)}
          >
            检测所选{checking ? `（已完成 ${checked}）` : ""}
          </Button>
          <Button disabled={!selected.length} onClick={() => setSelected([])}>
            清空选择
          </Button>
        </Space>
        <Table<Source>
          rowKey="id"
          loading={loading}
          dataSource={items}
          scroll={{ x: 1000 }}
          pagination={{
            current: page,
            pageSize: 24,
            total,
            showSizeChanger: false,
            onChange: setPage,
            showTotal: (n) => `共 ${n} 个频道`,
          }}
          rowSelection={{
            selectedRowKeys: selected.map((s) => s.id),
            preserveSelectedRowKeys: true,
            onChange: (_, rows) => setSelected(rows.filter(Boolean)),
            getCheckboxProps: (record) => ({
              disabled:
                checking ||
                (!selected.some((s) => s.id === record.id) &&
                  selected.length >= 20),
            }),
          }}
          columns={[
            {
              title: "来源",
              width: 340,
              render: (_, s) => (
                <>
                  <Typography.Text strong>{s.name}</Typography.Text>
                  <div>
                    <Typography.Text
                      type="secondary"
                      style={{ fontSize: 12, wordBreak: "break-all" }}
                    >
                      {s.url}
                    </Typography.Text>
                  </div>
                </>
              ),
            },
            {
              title: "分类",
              width: 160,
              render: (_, s) => (
                <Space size={0}>
                  <Tag>{categories[s.category]}</Tag>
                  <Tag>{s.language === "zh" ? "中文" : "英文"}</Tag>
                </Space>
              ),
            },
            {
              title: "最近检测",
              width: 220,
              render: (_, s) => (
                <>
                  <Tag color={states[s.health.status]?.color}>
                    {states[s.health.status]?.label}
                  </Tag>
                  <div>
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                      {s.health.checked_at
                        ? new Date(s.health.checked_at).toLocaleString()
                        : "尚未检测"}
                    </Typography.Text>
                  </div>
                </>
              ),
            },
            {
              title: "条目",
              width: 70,
              render: (_, s) => s.health.entry_count ?? "—",
            },
            {
              title: "操作",
              width: 100,
              render: (_, s) => (
                <Button type="link" onClick={() => setPreview(s)}>
                  预览与检测
                </Button>
              ),
            },
          ]}
        />
      </div>
      <Drawer
        title={preview?.name}
        width={560}
        open={!!preview}
        onClose={() => setPreview(null)}
      >
        {preview && (
          <>
            <Typography.Paragraph>{preview.description}</Typography.Paragraph>
            <Typography.Paragraph copyable>{preview.url}</Typography.Paragraph>
            <Space>
              <Tag color={states[preview.health.status]?.color}>
                {states[preview.health.status]?.label}
              </Tag>
              <Button loading={checking} onClick={() => check([preview], true)}>
                检测此来源
              </Button>
            </Space>
            <Typography.Paragraph type="secondary" style={{ marginTop: 16 }}>
              最近检测：
              {preview.health.checked_at
                ? new Date(preview.health.checked_at).toLocaleString()
                : "尚未检测"}
              ；耗时：{preview.health.latency_ms ?? "—"} ms
            </Typography.Paragraph>
            {preview.health.error && (
              <Alert
                type="warning"
                message="本次检测失败，不一定代表永久失效"
                description={preview.health.error}
              />
            )}
            {preview.health.samples?.length ? (
              preview.health.samples.map((s) => (
                <div key={s.url} style={{ marginTop: 20 }}>
                  <Typography.Link
                    href={s.url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {s.title}
                  </Typography.Link>
                  <Typography.Paragraph type="secondary">
                    {s.summary}
                  </Typography.Paragraph>
                </div>
              ))
            ) : (
              <Empty description="暂无预览条目，请先检测来源" />
            )}
          </>
        )}
      </Drawer>
      <Modal
        title={`将 ${selected.length} 个来源加入订阅`}
        open={open}
        onCancel={() => setOpen(false)}
        onOk={save}
        confirmLoading={saving}
        okText="保存订阅"
        cancelText="取消"
        forceRender
      >
        <Form form={form} layout="vertical">
          <Form.Item name="target" label="目标订阅">
            <Select
              options={[
                { value: "new", label: "新建订阅" },
                ...subscriptions.map((s) => ({
                  value: s.id,
                  label: s.name + (s.status === 0 ? "（已暂停）" : ""),
                })),
              ]}
            />
          </Form.Item>
          <Form.Item noStyle shouldUpdate={(a, b) => a.target !== b.target}>
            {({ getFieldValue }) =>
              getFieldValue("target") === "new" ? (
                <Form.Item
                  name="name"
                  label="订阅名称"
                  rules={[{ required: true, whitespace: true, max: 100 }]}
                >
                  <Input placeholder="例如：AI 与科技动态" />
                </Form.Item>
              ) : null
            }
          </Form.Item>
          <Alert
            type="info"
            message="新订阅每 60 分钟采集，AI 默认关闭；已有订阅保留原有设置。可在我的订阅中修改。"
          />
        </Form>
      </Modal>
    </>
  );
}
