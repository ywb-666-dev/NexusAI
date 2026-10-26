export const nodeNames: Record<string, string> = {
  scout: "资源采集",
  parser: "正文解析",
  connector: "去重入库",
  actor: "风险审核",
  curator: "简报与推送",
};
export const statusName = (s: string) =>
  ({
    queued: "排队中",
    fetching: "采集中",
    parsing: "解析中",
    storing: "入库中",
    deciding: "风险评估",
    curating: "生成简报",
    completed: "已完成",
    failed: "失败",
    rejected: "已拒绝",
    "interrupted: awaiting approval": "等待人工审批",
  })[s] ||
  (s?.startsWith("completed:")
    ? "完成，无匹配内容"
    : s?.startsWith("error")
      ? "执行失败"
      : s || "待执行");
export const activeTask = (s: string) =>
  ["queued", "fetching", "parsing", "storing", "deciding", "curating"].includes(
    s,
  );
