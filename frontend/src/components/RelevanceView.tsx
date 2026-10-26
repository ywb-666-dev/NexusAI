import { Alert, Tag, Typography } from "antd";

export default function RelevanceView({
  value,
  compact = false,
}: {
  value: any;
  compact?: boolean;
}) {
  if (!value || value.method !== "llm")
    return compact ? null : (
      <Typography.Paragraph type="secondary">
        这条内容未经过语义筛选。
      </Typography.Paragraph>
    );
  if (compact) return <Tag color="blue">语义相关度 {value.score}</Tag>;
  return (
    <Alert
      type="info"
      style={{ margin: "14px 0" }}
      message={`推荐理由 · 语义相关度 ${value.score}/100`}
      description={
        <>
          <Typography.Paragraph>{value.reason}</Typography.Paragraph>
          <Typography.Paragraph type="secondary">
            订阅需求：{value.intent}
            {value.exclusions ? `；排除：${value.exclusions}` : ""}
          </Typography.Paragraph>
          {value.evidence?.map((text: string) => (
            <blockquote
              key={text}
              style={{
                borderLeft: "2px solid #20b8ca",
                paddingLeft: 12,
                marginLeft: 0,
              }}
            >
              {text}
            </blockquote>
          ))}
          <Typography.Text type="secondary">
            依据为模型看到的文章片段；相关度不表示事实准确性。
          </Typography.Text>
        </>
      }
    />
  );
}
