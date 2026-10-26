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

export function semanticValues(form: FormInstance) {
  return {
    enabled: form.getFieldValue("matchingMode") === "semantic",
    intent: (form.getFieldValue("semanticIntent") || "").trim(),
    exclusions: (form.getFieldValue("semanticExclusions") || "").trim(),
    threshold: form.getFieldValue("semanticThreshold") || 75,
    max_candidates: form.getFieldValue("semanticBudget") || 20,
  };
}
export function IntentView({ plan }: { plan: any }) {
  return plan ? (
    <Alert
      type="info"
      message="系统理解的订阅需求"
      description={
        <>
          <Typography.Paragraph>{plan.summary}</Typography.Paragraph>
          <Space wrap>
            {plan.include.map((item: string) => (
              <Tag key={item} color="cyan">
                关注：{item}
              </Tag>
            ))}
            {plan.exclude.map((item: string) => (
              <Tag key={item} color="orange">
                排除：{item}
              </Tag>
            ))}
          </Space>
          <Typography.Paragraph
            type="secondary"
            style={{ marginTop: 8, marginBottom: 0 }}
          >
            文章仍会结合正文逐条审核，选中来源不等于推荐该来源的全部文章。
          </Typography.Paragraph>
        </>
      }
    />
  ) : null;
}

export default function SemanticFields({ form }: { form: FormInstance }) {
  const mode = Form.useWatch("matchingMode", form),
    sourceMode = Form.useWatch("sourceMode", form);
  const intent = Form.useWatch("semanticIntent", form),
    exclusions = Form.useWatch("semanticExclusions", form);
  const [configured, setConfigured] = useState<boolean | null>(null),
    [plan, setPlan] = useState<any>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  useEffect(() => {
    let live = true;
    request
      .get("/python/subscriptions/semantic-capabilities")
      .then((r: any) => {
        if (live) setConfigured(r.data.configured);
      })
      .catch(() => {});
    return () => {
      live = false;
    };
  }, []);
  useEffect(() => {
    setPlan(null);
    setError("");
  }, [intent, exclusions]);
  const understand = async () => {
    if (!intent?.trim()) {
      setError("请先描述想关注的内容");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const values = semanticValues(form);
      const r: any = await request.post(
        "/python/subscriptions/interpret",
        values,
        { timeout: 100000 },
      );
      if (JSON.stringify(values) === JSON.stringify(semanticValues(form)))
        setPlan(r.data.plan);
      else setError("需求已改变，请重新理解当前订阅需求");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <Form.Item name="matchingMode" label="文章筛选方式">
        <Radio.Group
          options={[
            { value: "semantic", label: "语义订阅（推荐）" },
            { value: "keyword", label: "关键词筛选（兼容）" },
          ]}
        />
      </Form.Item>
      {mode === "semantic" && (
        <>
          <Alert
            type={configured === false ? "warning" : "info"}
            style={{ marginBottom: 16 }}
            message={
              configured === false
                ? "模型尚未配置，语义订阅无法执行；请配置模型服务后重试，或明确切换兼容模式。"
                : "语义订阅会调用模型理解需求并逐篇判断相关性，不依赖文章是否出现相同词语。试采也会调用模型。"
            }
          />
          <Form.Item
            name="semanticIntent"
            label="订阅需求"
            rules={[
              {
                required: true,
                whitespace: true,
                message: "请用自然语言描述想关注的内容",
              },
              { max: 1000 },
            ]}
          >
            <Input.TextArea
              rows={3}
              maxLength={1000}
              showCount
              placeholder="例如：关注能在普通电脑本地运行的开源大模型，尤其是实际部署教程和性能测试。"
              onBlur={() => {
                if (!form.getFieldValue("name") && intent?.trim())
                  form.setFieldValue("name", intent.trim().slice(0, 100));
              }}
            />
          </Form.Item>
          <Form.Item
            name="semanticExclusions"
            label="不想看到的内容（可选）"
            rules={[{ max: 500 }]}
          >
            <Input.TextArea
              rows={2}
              maxLength={500}
              placeholder="例如：排除融资新闻、纯广告、只能调用云端接口的产品。"
            />
          </Form.Item>
          <Space wrap size={20}>
            <Form.Item name="semanticThreshold" label="推荐严格程度">
              <Select
                style={{ width: 170 }}
                options={[
                  { value: 60, label: "宽松 · 60 分" },
                  { value: 75, label: "标准 · 75 分" },
                  { value: 85, label: "严格 · 85 分" },
                ]}
              />
            </Form.Item>
            <Form.Item name="semanticBudget" label="每次最多评估">
              <Select
                style={{ width: 150 }}
                options={[
                  { value: 10, label: "10 条候选" },
                  { value: 20, label: "20 条候选" },
                  { value: 40, label: "40 条候选" },
                ]}
              />
            </Form.Item>
          </Space>
          <Typography.Paragraph type="secondary">
            评分表示与需求的相关程度，不代表真实性。排除条件优先；信息不足或模型失败时不推荐，不会悄悄改用词语匹配。翻译与简报可单独选择。
          </Typography.Paragraph>
          {sourceMode === "manual" && (
            <div style={{ marginBottom: 18 }}>
              <Button loading={busy} onClick={understand}>
                理解订阅需求
              </Button>
              {error && (
                <Alert type="error" message={error} style={{ marginTop: 12 }} />
              )}
              <IntentView plan={plan} />
            </div>
          )}
        </>
      )}
    </>
  );
}
