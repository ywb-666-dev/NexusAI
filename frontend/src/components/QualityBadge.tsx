import { Space, Tag, Tooltip, Typography } from "antd";

export type ContentQuality = {
  kind: string;
  label: string;
  score: number;
  characters: number;
  eligible: boolean;
  reasons: string[];
  extraction?: string;
};
export default function QualityBadge({
  quality,
}: {
  quality?: ContentQuality | null;
}) {
  if (!quality) return <Tag>尚未评估</Tag>;
  return (
    <Tooltip
      title={
        quality.reasons?.join("；") ||
        "规则评估正文提取质量，不代表内容真实性或全文完整性"
      }
    >
      <Space size={4} wrap>
        <Tag
          color={
            quality.kind === "body"
              ? "cyan"
              : quality.eligible
                ? "gold"
                : "error"
          }
        >
          {quality.label}
        </Tag>
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          提取质量 {quality.score}/100
        </Typography.Text>
      </Space>
    </Tooltip>
  );
}
