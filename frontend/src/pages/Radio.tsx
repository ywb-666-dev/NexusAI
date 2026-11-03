import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Alert,
  App,
  Button,
  Collapse,
  Empty,
  Input,
  Modal,
  Progress,
  Select,
  Skeleton,
  Space,
  Tag,
  Typography,
} from "antd";
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  SoundOutlined,
  StepBackwardOutlined,
  StepForwardOutlined,
} from "@ant-design/icons";
import { Link, useSearchParams } from "react-router-dom";
import request from "../api/request";
import PageHeading from "../components/PageHeading";
import useRadioSpeech from "../components/useRadioSpeech";
import { useAuthStore } from "../store/auth";

export default function Radio() {
  const { message } = App.useApp();
  const user = useAuthStore((s) => s.user);
  const [params, setParams] = useSearchParams();
  const id = params.get("id") || "";
  const [episodes, setEpisodes] = useState<any[]>([]),
    [brief, setBrief] = useState<any>(null),
    [index, setIndex] = useState(0),
    [context, setContext] = useState<any>(null);
  const [question, setQuestion] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true),
    [refresh, setRefresh] = useState(0),
    [actionBusy, setActionBusy] = useState(false),
    [followOpen, setFollowOpen] = useState(false);
  const [resumeAt, setResumeAt] = useState<{
    event: number;
    part: number;
  } | null>(null);
  const key = `nexus-radio:${user?.id}`;
  const events = brief?.report?.events || [];
  const current = useRef({ id, index });
  current.current = { id, index };
  const texts = useMemo(
    () =>
      events.map(
        (e: any, i: number) =>
          `${i === 0 ? `欢迎收听我的信息电台。${brief.headline}。${brief.report.overview}。` : ""}第${i + 1}条。${e.title}。${e.summary}。关注建议：${e.attention}。`,
      ),
    [brief],
  );
  const checkpoint = useCallback(
    (event: number, part: number) => {
      try {
        localStorage.setItem(key, JSON.stringify({ id, event, part }));
      } catch {
        /* Storage can be disabled. */
      }
    },
    [id, key],
  );
  const speech = useRadioSpeech(texts, setIndex, checkpoint);
  useEffect(() => {
    let live = true;
    request
      .get("/python/briefings", { params: { size: 50 } })
      .then((r: any) => {
        if (!live) return;
        const ready = r.data.items.filter(
          (b: any) => b.status === "ready" && b.eventCount > 0,
        );
        setEpisodes(ready);
        if (!id && ready.length) {
          let saved: any = null;
          try {
            saved = JSON.parse(localStorage.getItem(key) || "null");
          } catch {
            /* Ignore invalid state. */
          }
          setParams(
            {
              id: ready.some((b: any) => b.id === saved?.id)
                ? saved.id
                : ready[0].id,
            },
            { replace: true },
          );
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
  }, [refresh]);
  useEffect(() => {
    speech.stop();
    setBrief(null);
    setContext(null);
    setIndex(0);
    setResumeAt(null);
    setQuestion("");
    if (!id) return;
    let live = true;
    setLoading(true);
    request
      .get("/python/briefings/" + id)
      .then((r: any) => {
        if (!live) return;
        setBrief(r.data);
        setError("");
        try {
          const saved = JSON.parse(localStorage.getItem(key) || "null");
          if (
            saved?.id === id &&
            Number.isInteger(saved.event) &&
            saved.event >= 0 &&
            saved.event < (r.data.report?.events?.length || 0) &&
            Number.isInteger(saved.part) &&
            saved.part >= 0 &&
            saved.part < 100
          ) {
            setResumeAt(saved);
            setIndex(saved.event);
          }
        } catch {
          /* Invalid checkpoint. */
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
  }, [id, refresh]);
  useEffect(() => {
    setContext(null);
    if (!id || !events.length) return;
    let live = true;
    request
      .get(`/python/radio/${id}/events/${index}`)
      .then((r: any) => {
        if (live) {
          setContext(r.data);
          setError("");
        }
      })
      .catch((e) => {
        if (live) setError(e.message);
      });
    return () => {
      live = false;
    };
  }, [id, index, brief]);
  const switchEvent = (next: number) => {
    speech.stop();
    setResumeAt(null);
    setIndex(next);
    checkpoint(next, 0);
    setQuestion("");
  };
  const ask = async (text: string) => {
    if (!text.trim() || busy) return;
    speech.pause();
    setBusy(true);
    const target = index,
      episode = id;
    try {
      const r: any = await request.post(
        `/python/radio/${episode}/events/${target}/ask`,
        { question: text.trim() },
        { timeout: 110000 },
      );
      if (current.current.id !== episode || current.current.index !== target)
        return;
      setContext((previous: any) =>
        previous
          ? { ...previous, turns: [...previous.turns, r.data].slice(-20) }
          : previous,
      );
      setQuestion("");
    } catch (e: any) {
      message.error(e.message);
    } finally {
      setBusy(false);
    }
  };
  const preference = async () => {
    const target = { id, index };
    speech.pause();
    setActionBusy(true);
    try {
      await request.put(`/python/radio/${id}/events/${index}/preference`, {
        dismissed: !context.dismissed,
      });
      if (
        current.current.id === target.id &&
        current.current.index === target.index
      )
        setContext((c: any) => (c ? { ...c, dismissed: !c.dismissed } : c));
      message.success("偏好已更新，将影响后续推荐与新简报；当前节目保留原样");
    } catch (e: any) {
      message.error(e.message);
    } finally {
      setActionBusy(false);
    }
  };
  const follow = async () => {
    const target = { id, index };
    setActionBusy(true);
    try {
      const r: any = await request.post(
        `/python/radio/${id}/events/${index}/follow`,
      );
      if (
        current.current.id === target.id &&
        current.current.index === target.index
      )
        setContext((c: any) => (c ? { ...c, followId: r.data.id } : c));
      setFollowOpen(false);
      message.success("追踪订阅已保存，请到我的订阅确认条件并启用");
    } catch (e: any) {
      message.error(e.message);
    } finally {
      setActionBusy(false);
    }
  };
  const event = events[index];
  const sources = Object.fromEntries(
    (context?.sources || []).map((s: any) => [s.id, s]),
  );
  return (
    <>
      <PageHeading
        label="RADIO / 我的信息电台"
        title="听见你关心的世界"
        subtitle="听一段，问一句。节目来自你的个人简报，重要信息始终可以回到原文。"
        extra={
          <Space>
            <Button
              disabled={busy || actionBusy}
              onClick={() => setRefresh((v) => v + 1)}
            >
              刷新节目
            </Button>
            <Link to="/briefings">
              <Button type="primary">生成或查看简报</Button>
            </Link>
          </Space>
        }
      />
      {error && (
        <Alert type="error" message={error} style={{ marginBottom: 16 }} />
      )}
      {loading ? (
        <Skeleton active />
      ) : !brief && !episodes.length ? (
        <div className="panel">
          <Empty description="还没有可播放的节目。先创建兴趣订阅、完成采集，再生成一份有内容的个人简报。" />
          <Link to="/briefings">
            <Button type="primary">前往个人简报</Button>
          </Link>
        </div>
      ) : (
        <>
          <div className="panel" style={{ marginBottom: 20 }}>
            <Space wrap>
              <SoundOutlined />
              <Select
                aria-label="选择节目"
                value={id || undefined}
                style={{ width: "min(440px, 65vw)" }}
                options={episodes.map((b) => ({
                  value: b.id,
                  label: b.headline,
                }))}
                onChange={(value) => {
                  speech.stop();
                  setParams({ id: value });
                }}
                disabled={busy || actionBusy}
              />
              <Tag>{events.length} 个事件</Tag>
              <Tag>
                约{" "}
                {Math.max(
                  1,
                  Math.ceil(texts.join("").length / 250 / speech.rate),
                )}{" "}
                分钟 · 估算
              </Tag>
            </Space>
          </div>
          {!events.length ? (
            <Empty description="这份简报还没有可播放的事件，请选择已完成且有内容的节目" />
          ) : (
            <div className="radio-layout">
              <div className="panel">
                <Typography.Text className="eyebrow">
                  ON YOUR FREQUENCY
                </Typography.Text>
                <Typography.Title level={2}>{brief.headline}</Typography.Title>
                <Typography.Paragraph type="secondary">
                  {brief.report.overview}
                </Typography.Paragraph>
                <div className="radio-orbit" aria-hidden="true">
                  <SoundOutlined />
                </div>
                <Progress
                  percent={Math.round(((index + 1) / events.length) * 100)}
                  format={() => `${index + 1} / ${events.length}`}
                />
                <Space wrap style={{ margin: "16px 0" }}>
                  <Button
                    aria-label="上一条"
                    icon={<StepBackwardOutlined />}
                    disabled={index === 0 || busy || actionBusy}
                    onClick={() => switchEvent(index - 1)}
                  />
                  <Button
                    type="primary"
                    icon={
                      speech.state === "playing" ? (
                        <PauseCircleOutlined />
                      ) : (
                        <PlayCircleOutlined />
                      )
                    }
                    disabled={
                      busy ||
                      actionBusy ||
                      !speech.supported ||
                      !speech.voices.length
                    }
                    onClick={() => {
                      if (speech.state === "playing") speech.pause();
                      else if (speech.state === "paused") speech.resume();
                      else {
                        speech.play(
                          index,
                          resumeAt?.event === index ? resumeAt.part : 0,
                        );
                        setResumeAt(null);
                      }
                    }}
                  >
                    {speech.state === "playing"
                      ? "暂停收听"
                      : speech.state === "paused"
                        ? "继续收听"
                        : resumeAt
                          ? "从上次位置收听"
                          : "开始收听"}
                  </Button>
                  <Button
                    aria-label="下一条"
                    icon={<StepForwardOutlined />}
                    disabled={index === events.length - 1 || busy || actionBusy}
                    onClick={() => switchEvent(index + 1)}
                  />
                  <Button
                    onClick={() => {
                      speech.stop();
                      setResumeAt(null);
                    }}
                  >
                    停止
                  </Button>
                </Space>
                <Space wrap>
                  <Select
                    aria-label="朗读速度"
                    value={speech.rate}
                    options={[0.8, 1, 1.2, 1.5].map((v) => ({
                      value: v,
                      label: `${v} 倍速`,
                    }))}
                    onChange={(value) => {
                      speech.stop();
                      speech.setRate(value);
                    }}
                  />
                  <Select
                    aria-label="朗读声音"
                    value={speech.voice || undefined}
                    placeholder="自动选择设备声音"
                    style={{ maxWidth: "100%", width: 220 }}
                    options={speech.voices.map((v) => ({
                      value: v.voiceURI,
                      label: `${v.name} · ${v.lang}`,
                    }))}
                    onChange={(value) => {
                      speech.stop();
                      speech.setVoice(value);
                    }}
                  />
                </Space>
                {(!speech.supported || !speech.voices.length) && (
                  <Alert
                    type="warning"
                    message="当前浏览器或设备尚无可用朗读声音，仍可阅读卡片和文字追问。可检查系统语音包或换用支持朗读的浏览器。"
                    style={{ marginTop: 16 }}
                  />
                )}
                {speech.error && (
                  <Alert
                    type="warning"
                    message={speech.error}
                    style={{ marginTop: 16 }}
                  />
                )}
                <Typography.Paragraph
                  type="secondary"
                  style={{ marginTop: 16 }}
                >
                  使用设备朗读声音，不自动播放。切换事件会停止朗读，文字追问会暂停；返回后可继续。进入后台自动暂停。语音服务是否联网由设备决定，不支持音频下载或锁屏续播。
                </Typography.Paragraph>
                {speech.spoken && (
                  <Alert message="正在播报的文字" description={speech.spoken} />
                )}
                <div style={{ marginTop: 20 }}>
                  {events.map((e: any, i: number) => (
                    <Button
                      key={i}
                      block
                      type={i === index ? "primary" : "text"}
                      disabled={busy || actionBusy}
                      style={{
                        textAlign: "left",
                        whiteSpace: "normal",
                        height: "auto",
                        padding: 12,
                      }}
                      onClick={() => switchEvent(i)}
                    >
                      {i + 1}. {e.title}
                    </Button>
                  ))}
                </div>
              </div>
              <div className="panel" style={{ minWidth: 0 }}>
                <Tag color="cyan">当前事件 {index + 1}</Tag>
                <Typography.Title level={3}>{event.title}</Typography.Title>
                <Typography.Paragraph>{event.summary}</Typography.Paragraph>
                <Typography.Paragraph>
                  <strong>关注建议：</strong>
                  {event.attention}
                </Typography.Paragraph>
                <Space wrap>
                  <Button
                    disabled={!context || busy}
                    loading={actionBusy}
                    onClick={preference}
                  >
                    {context?.dismissed ? "撤销少推这类" : "这类消息少一点"}
                  </Button>
                  {context?.followId ? (
                    <Link to="/subscriptions">查看追踪订阅</Link>
                  ) : (
                    <Button
                      disabled={!context || busy || actionBusy}
                      onClick={() => {
                        speech.pause();
                        setFollowOpen(true);
                      }}
                    >
                      追踪后续
                    </Button>
                  )}
                </Space>
                <Collapse
                  style={{ margin: "20px 0" }}
                  items={[
                    {
                      key: "sources",
                      label: `查看 ${context?.sources?.length || 0} 篇原文依据`,
                      children: context?.sources?.map((s: any) => (
                        <Typography.Paragraph key={s.id}>
                          <a
                            href={s.url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            {s.title}
                          </a>
                          <blockquote>
                            {
                              event.citations.find((c: any) => c.id === s.id)
                                ?.quote
                            }
                          </blockquote>
                        </Typography.Paragraph>
                      )),
                    },
                  ]}
                />
                <Typography.Title level={4}>
                  随时打断，问清楚再继续
                </Typography.Title>
                <Space wrap>
                  {[
                    "这件事讲简单一点",
                    "为什么值得关注",
                    "有没有不同的说法",
                  ].map((q) => (
                    <Button
                      key={q}
                      disabled={!context || busy || actionBusy}
                      onClick={() => ask(q)}
                    >
                      {q}
                    </Button>
                  ))}
                </Space>
                <Input.TextArea
                  aria-label="围绕当前事件追问"
                  placeholder="例如：这与刚才提到的变化有什么关系？"
                  value={question}
                  maxLength={500}
                  showCount
                  rows={3}
                  onChange={(e) => setQuestion(e.target.value)}
                  onFocus={speech.pause}
                  disabled={busy || actionBusy}
                  style={{ margin: "16px 0" }}
                />
                <Button
                  type="primary"
                  loading={busy}
                  disabled={!context || !question.trim() || actionBusy}
                  onClick={() => ask(question)}
                >
                  发送追问
                </Button>
                <Typography.Paragraph
                  type="secondary"
                  style={{ marginTop: 14 }}
                >
                  回答会调用已配置的模型，仅依据当前事件最多 6
                  篇原文片段及最近对话。不会实时搜索；原文引文校验不等于独立事实核查。
                </Typography.Paragraph>
                {context?.turns?.map((turn: any) => (
                  <div
                    key={turn.id}
                    style={{
                      borderTop: "1px solid #263448",
                      paddingTop: 16,
                      marginTop: 16,
                    }}
                  >
                    <Typography.Text strong>
                      你问：{turn.question}
                    </Typography.Text>
                    <Typography.Paragraph
                      style={{ whiteSpace: "pre-wrap", marginTop: 10 }}
                    >
                      {turn.answer.answer}
                    </Typography.Paragraph>
                    {turn.answer.insufficient && (
                      <Tag color="warning">资料不足</Tag>
                    )}
                    <Typography.Paragraph type="secondary">
                      {turn.answer.limitations}
                    </Typography.Paragraph>
                    {turn.answer.citations.map((c: any) => (
                      <div key={c.id}>
                        <a
                          href={sources[c.id]?.url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          {sources[c.id]?.title}
                        </a>
                        <blockquote>{c.quote}</blockquote>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
      <Modal
        title="创建后续追踪订阅"
        open={followOpen}
        confirmLoading={actionBusy}
        onCancel={() => setFollowOpen(false)}
        onOk={follow}
        okText="保存待确认订阅"
        cancelText="取消"
      >
        <p>
          将复用事件原订阅的来源，生成关注后续进展的语义订阅，默认暂停。请到“我的订阅”检查条件和来源后启用；启用后可能调用模型和已配置的推送渠道。
        </p>
      </Modal>
    </>
  );
}
