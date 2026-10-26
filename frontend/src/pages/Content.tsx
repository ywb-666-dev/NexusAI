import { useEffect, useState } from "react";
import {
  Alert,
  App,
  Button,
  Drawer,
  Empty,
  Input,
  Pagination,
  Segmented,
  Skeleton,
  Space,
  Tag,
  Typography,
} from "antd";
import { useSearchParams } from "react-router-dom";
import { SearchOutlined, ExportOutlined } from "@ant-design/icons";
import request from "../api/request";
import PageHeading from "../components/PageHeading";
import QualityBadge from "../components/QualityBadge";
import RelevanceView from "../components/RelevanceView";
const { Text } = Typography;
export default function ContentPage() {
  const [params, setParams] = useSearchParams(),
    [search, setSearch] = useState(params.get("search") || ""),
    [query, setQuery] = useState(search),
    [platform, setPlatform] = useState(""),
    [sort, setSort] = useState("relevance"),
    [page, setPage] = useState(1),
    [data, setData] = useState<any[]>([]),
    [total, setTotal] = useState(0),
    [loading, setLoading] = useState(true),
    [error, setError] = useState(""),
    [detail, setDetail] = useState<any>(null),
    [ai, setAi] = useState(""),
    [busy, setBusy] = useState(false);
  const { message } = App.useApp();
  useEffect(() => {
    const next = params.get("search") || "";
    setSearch(next);
    setQuery(next);
    setPage(1);
  }, [params]);
  useEffect(() => {
    let live = true;
    setLoading(true);
    setError("");
    request
      .get("/python/contents", {
        params: { page, size: 12, search: query, platform, sort },
      })
      .then((r: any) => {
        if (live) {
          setData(r.data.items);
          setTotal(r.data.total);
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
  }, [page, query, platform, sort]);
  const invoke = async (name: string) => {
    setBusy(true);
    setAi("");
    try {
      const r: any = await request.post("/python/skills/" + name + "/invoke", {
        text: detail.contentBody || detail.summary,
        style: "article_summary",
      });
      setAi(
        (r.data.data?.source !== "llm"
          ? "当前未使用大模型，以下保留原文或提供原文摘录。\n\n"
          : "") +
          (r.data.data?.summary || r.data.data?.translated || "未返回内容"),
      );
    } catch (e: any) {
      message.error(e.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <PageHeading
        label="CONTENT / 内容情报"
        title="你的内容中心"
        subtitle="所有订阅内容集中阅读，保留来源与原文，按需翻译和提炼。"
      />
      <div className="toolbar">
        <Input.Search
          prefix={<SearchOutlined />}
          placeholder="搜索标题或摘要，回车检索"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onSearch={(v) => {
            setQuery(v);
            setPage(1);
            setParams(v ? { search: v } : {});
          }}
          allowClear
          style={{ width: 360, maxWidth: "100%" }}
        />
        <Segmented
          options={[
            { label: "全部来源", value: "" },
            { label: "RSS", value: "rss" },
            { label: "网页", value: "web" },
            { label: "API", value: "api" },
          ]}
          value={platform}
          onChange={(v) => {
            setPlatform(String(v));
            setPage(1);
          }}
        />
        <Segmented
          value={sort}
          onChange={(v) => {
            setSort(String(v));
            setPage(1);
          }}
          options={[
            { value: "relevance", label: "推荐优先" },
            { value: "latest", label: "最新内容" },
          ]}
        />
        <Text type="secondary">共 {total} 条内容</Text>
      </div>
      {error && (
        <Alert
          type="error"
          message={error}
          showIcon
          style={{ marginTop: 20 }}
        />
      )}
      <div className="content-grid">
        {loading
          ? Array.from({ length: 6 }, (_, i) => (
              <div className="panel" key={i}>
                <Skeleton active />
              </div>
            ))
          : data.map((item) => (
              <button
                className="panel article-card"
                key={item.id}
                onClick={() => {
                  setDetail(item);
                  setAi("");
                }}
              >
                <Tag color={item.sourcePlatform === "rss" ? "cyan" : "purple"}>
                  {item.sourcePlatform.toUpperCase()}
                </Tag>
                <h3>{item.title || "无标题"}</h3>
                <QualityBadge quality={item.quality} />
                <RelevanceView value={item.relevance} compact />
                <p>
                  {item.translatedSummary || item.summary || "打开阅读完整正文"}
                </p>
                <div className="article-meta">
                  <span>{item.author || "来源未署名"}</span>
                  <span>
                    {item.fetchedAt
                      ? new Date(item.fetchedAt).toLocaleString("zh-CN")
                      : ""}
                  </span>
                </div>
              </button>
            ))}
      </div>
      {!loading && !error && data.length === 0 && (
        <Empty
          description={
            query
              ? "没有找到匹配的内容"
              : "还没有可读内容，创建订阅并触发首次采集吧"
          }
          style={{ padding: 60 }}
        />
      )}
      <Pagination
        current={page}
        total={total}
        pageSize={12}
        onChange={setPage}
        showSizeChanger={false}
        hideOnSinglePage
      />
      <Drawer
        open={!!detail}
        onClose={() => setDetail(null)}
        width={Math.min(760, window.innerWidth)}
        title="内容阅读"
        extra={
          detail && (
            <Button
              href={detail.sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
              icon={<ExportOutlined />}
            >
              查看来源
            </Button>
          )
        }
      >
        {detail && (
          <>
            <Tag color="cyan">{detail.sourcePlatform}</Tag>
            <Typography.Title level={3}>{detail.title}</Typography.Title>
            <RelevanceView value={detail.relevance} />
            <QualityBadge quality={detail.quality} />
            {!!detail.quality?.reasons?.length && (
              <Typography.Paragraph type="secondary" style={{ marginTop: 10 }}>
                {detail.quality.reasons.join("；")}
              </Typography.Paragraph>
            )}
            <Text type="secondary">
              {detail.author || "来源未署名"} ·{" "}
              {detail.publishedAt
                ? new Date(detail.publishedAt).toLocaleString("zh-CN")
                : "发布时间未知"}
            </Text>
            <Space style={{ margin: "22px 0" }}>
              <Button loading={busy} onClick={() => invoke("summarize")}>
                AI 提炼摘要
              </Button>
              <Button loading={busy} onClick={() => invoke("translate")}>
                翻译为中文
              </Button>
            </Space>
            {ai && (
              <Alert
                type="info"
                message="AI 辅助阅读"
                description={
                  <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.9 }}>
                    {ai}
                  </div>
                }
                style={{ marginBottom: 24 }}
              />
            )}
            {detail.translatedSummary && (
              <Alert
                message="中文摘要"
                description={detail.translatedSummary}
                style={{ marginBottom: 24 }}
              />
            )}
            <div className="reading-body">
              {detail.contentBody ||
                detail.summary ||
                "来源未提供正文，请打开原文阅读。"}
            </div>
          </>
        )}
      </Drawer>
    </>
  );
}
