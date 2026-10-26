import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Form,
  Input,
  Radio,
  Select,
  Space,
  Tag,
  Typography,
} from "antd";
import type { FormInstance } from "antd";
import request from "../api/request";

export default function AutomaticSources({ form }: { form: FormInstance }) {
  const mode = Form.useWatch("sourceMode", form),
    topic = Form.useWatch("focusTopic", form) || "",
    language = Form.useWatch("sourceLanguage", form) || "zh_first";
  const excluded = Form.useWatch("excludedSourceIds", form) || [],
    manual = Form.useWatch("rssFeeds", form) || [];
  const [data, setData] = useState<any>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const signature = JSON.stringify({
    topic,
    language,
    excluded,
    manual: manual.filter((f: any) => f.url).length,
  });
  useEffect(() => {
    setData(null);
    setError("");
    if (mode !== "auto" || !topic.trim() || topic.length > 200) {
      setBusy(false);
      return;
    }
    let active = true;
    const controller = new AbortController();
    setBusy(true);
    const timer = setTimeout(async () => {
      try {
        const r: any = await request.post(
          "/python/subscriptions/resolve-sources",
          {
            topic: topic.trim(),
            language,
            excluded_ids: excluded,
            limit: Math.max(
              0,
              Math.min(5, 20 - manual.filter((f: any) => f.url).length),
            ),
          },
          { signal: controller.signal, timeout: 40000 },
        );
        if (active) setData(r.data);
      } catch (e: any) {
        if (active) setError(e.message);
      } finally {
        if (active) setBusy(false);
      }
    }, 650);
    return () => {
      active = false;
      clearTimeout(timer);
      controller.abort();
    };
  }, [mode, signature]);
  return (
    <>
      <Form.Item name="sourceMode" label="来源方式">
        <Radio.Group
          onChange={(e) => {
            const feeds = (form.getFieldValue("rssFeeds") || []).filter(
              (f: any) => f.url,
            );
            form.setFieldValue(
              "rssFeeds",
              e.target.value === "manual" && !feeds.length
                ? [{ url: "", platform: "rss" }]
                : feeds,
            );
          }}
          options={[
            { label: "系统自动匹配（推荐）", value: "auto" },
            { label: "手动配置", value: "manual" },
          ]}
        />
      </Form.Item>
      <Form.Item name="excludedSourceIds" hidden>
        <Select mode="multiple" />
      </Form.Item>
      {mode === "auto" && (
        <>
          <Form.Item
            name="focusTopic"
            label="关注主题"
            rules={[
              {
                required: true,
                whitespace: true,
                message: "告诉系统你想关注什么",
              },
              { max: 200 },
            ]}
          >
            <Input
              placeholder="例如：人工智能、Python、网络安全"
              maxLength={200}
              onBlur={() => {
                if (!form.getFieldValue("name") && topic.trim())
                  form.setFieldValue("name", topic.trim().slice(0, 100));
              }}
            />
          </Form.Item>
          <Form.Item name="sourceLanguage" label="来源语言偏好">
            <Select
              options={[
                { value: "zh_first", label: "优先中文，兼顾英文" },
                { value: "all", label: "中英文均可" },
              ]}
            />
          </Form.Item>
          <div style={{ marginBottom: 20 }}>
            <Space wrap style={{ marginBottom: 10 }}>
              <Typography.Text strong>系统自动添加的来源</Typography.Text>
              {busy && <Tag color="processing">正在匹配与校验</Tag>}
              {excluded.length > 0 && (
                <Button
                  size="small"
                  onClick={() => form.setFieldValue("excludedSourceIds", [])}
                >
                  恢复已排除来源（{excluded.length}）
                </Button>
              )}
            </Space>
            {error && <Alert type="warning" message={error} />}
            {!busy && !topic.trim() && (
              <Typography.Paragraph type="secondary">
                填写主题即可自动选择来源，无需了解 RSS 地址。
              </Typography.Paragraph>
            )}
            {data?.feeds?.map((feed: any) => (
              <div
                key={feed.sourceId}
                style={{
                  border: "1px solid var(--line)",
                  borderRadius: 8,
                  padding: 12,
                  marginBottom: 8,
                }}
              >
                <Space wrap>
                  <Tag color="cyan">系统来源</Tag>
                  <Typography.Text strong>{feed.name}</Typography.Text>
                  <Button
                    size="small"
                    disabled={excluded.length >= 50}
                    onClick={() =>
                      form.setFieldValue("excludedSourceIds", [
                        ...excluded,
                        feed.sourceId,
                      ])
                    }
                  >
                    排除此来源
                  </Button>
                </Space>
                <div style={{ marginTop: 6 }}>
                  <Typography.Text type="secondary">
                    {feed.reason}
                  </Typography.Text>
                </div>
              </div>
            ))}
            {data && !busy && (
              <Alert
                type={data.feeds.length ? "success" : "warning"}
                message={data.notice}
              />
            )}
            <Typography.Paragraph type="secondary" style={{ marginTop: 10 }}>
              主题用于选择来源；下方关键词可进一步筛选文章。保存及后续采集会重新匹配系统来源，额外来源始终保留。系统最多自动选择
              5 个不同域名的来源。
            </Typography.Paragraph>
          </div>
        </>
      )}
    </>
  );
}
