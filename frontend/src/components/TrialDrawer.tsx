import {
  Alert,
  Button,
  Drawer,
  Empty,
  Skeleton,
  Space,
  Tag,
  Typography,
} from "antd";
import QualityBadge from "./QualityBadge";
import RelevanceView from "./RelevanceView";
import { IntentView } from "./SemanticFields";

export default function TrialDrawer({
  open,
  onClose,
  loading,
  data,
  error,
  onRetry,
}: {
  open: boolean;
  onClose: () => void;
  loading: boolean;
  data: any;
  error: string;
  onRetry: () => void;
}) {
  return (
    <Drawer
      title="订阅试采预览"
      open={open}
      onClose={onClose}
      width={760}
      extra={
        <Button loading={loading} onClick={onRetry}>
          重新试采
        </Button>
      }
    >
      <Alert
        type="info"
        message="试采不保存文章、不发布通知。语义订阅会调用模型理解需求和评估相关性；兼容模式不调用模型。"
        style={{ marginBottom: 20 }}
      />
      {loading ? (
        <>
          <Skeleton active />
          <Typography.Text type="secondary">
            正在读取来源、检测正文并按订阅方式筛选；语义模式还需等待模型判断……
          </Typography.Text>
        </>
      ) : error ? (
        <Alert type="error" message={error} />
      ) : data ? (
        <>
          <Space wrap style={{ marginBottom: 16 }}>
            {[
              ["取得", data.collected_count],
              [data.semantic ? "采集候选" : "匹配关键词", data.matched_count],
              ["评估样本", data.examined_count],
              ["可读样本", data.readable_count],
              ["拦截样本", data.rejected_count],
            ].map(([name, value]) => (
              <Tag key={name}>
                {name}：{value}
              </Tag>
            ))}
          </Space>
          {data.semantic && (
            <>
              <IntentView plan={data.semantic.plan} />
              <Typography.Paragraph>
                语义评估 {data.semantic.evaluated_count} 条，推荐{" "}
                {data.semantic.accepted_count} 条，拒绝{" "}
                {data.semantic.rejected_count} 条；
                {data.semantic.unevaluated_count} 条超出本次评估范围。
              </Typography.Paragraph>
            </>
          )}
          <Typography.Paragraph type="secondary">
            {data.notice}{" "}
            {data.requested_sources > 5
              ? `此次使用已配置的前 5 / ${data.requested_sources} 个来源。`
              : ""}
          </Typography.Paragraph>
          <Typography.Title level={5}>来源读取结果</Typography.Title>
          {data.sources.map((source: any) => (
            <div
              key={source.url}
              style={{ marginBottom: 12, wordBreak: "break-all" }}
            >
              <Tag color={source.error ? "error" : "success"}>
                {source.error ? "读取失败" : `读取 ${source.count} 条`}
              </Tag>
              <Typography.Text type="secondary">{source.url}</Typography.Text>
              {source.error && (
                <div style={{ marginTop: 6 }}>{source.error}</div>
              )}
            </div>
          ))}
          <Typography.Title level={5}>匹配的候选内容</Typography.Title>
          {!data.items.length && (
            <Empty
              description={
                data.semantic
                  ? "本次样本没有通过语义筛选的推荐内容，请查看拒绝理由"
                  : data.matched_count
                    ? "本次样本未通过正文检测，请查看拦截原因"
                    : "本次没有匹配内容，可调整关键词或来源后重试"
              }
            />
          )}
          {data.items.map((item: any) => (
            <div className="panel" key={item.url} style={{ marginBottom: 16 }}>
              <Typography.Title level={5} style={{ marginTop: 0 }}>
                <Typography.Link
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {item.title || "无标题"}
                </Typography.Link>
              </Typography.Title>
              <QualityBadge quality={item.quality} />
              <RelevanceView value={item.relevance} />
              <Typography.Paragraph
                style={{ whiteSpace: "pre-wrap", marginTop: 12 }}
                ellipsis={{ rows: 6, expandable: true, symbol: "展开正文预览" }}
              >
                {item.body_preview || item.summary}
              </Typography.Paragraph>
              {item.quality.reasons?.length > 0 && (
                <Typography.Paragraph type="secondary">
                  {item.quality.reasons.join("；")}
                </Typography.Paragraph>
              )}
            </div>
          ))}
          {!!data.semantic?.rejected?.length && (
            <Alert
              type="info"
              message="未推荐的内容及语义判断理由"
              description={data.semantic.rejected.map((item: any) => (
                <div key={item.url} style={{ marginBottom: 12 }}>
                  <Typography.Text strong>{item.title}</Typography.Text> ·{" "}
                  {item.relevance.score} 分
                  {item.relevance.excluded ? " · 命中排除条件" : ""}
                  <div>{item.relevance.reason}</div>
                </div>
              ))}
            />
          )}
          {!!data.rejected?.length && (
            <Alert
              type="warning"
              message={`已拦截 ${data.rejected_count} 条异常样本，正式采集使用相同规则`}
              description={data.rejected.map((item: any) => (
                <div key={item.url}>
                  {item.title || item.url}：{item.quality.reasons.join("；")}
                </div>
              ))}
            />
          )}
        </>
      ) : null}
    </Drawer>
  );
}
