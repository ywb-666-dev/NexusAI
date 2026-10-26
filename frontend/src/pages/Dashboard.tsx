import { useEffect, useState } from "react";
import { Alert, Button, Empty, Skeleton, Space, Table, Tag } from "antd";
import { useNavigate } from "react-router-dom";
import Chart from "../components/Chart";
import request from "../api/request";
import PageHeading from "../components/PageHeading";
import { useThemeStore } from "../store/theme";
import { statusName } from "../utils/task";
export default function Dashboard() {
  const [metrics, setMetrics] = useState<any>({}),
    [charts, setCharts] = useState<any>({}),
    [tasks, setTasks] = useState<any[]>([]),
    [loading, setLoading] = useState(true),
    [error, setError] = useState("");
  const dark = useThemeStore((s) => s.dark),
    navigate = useNavigate();
  const load = async () => {
    setError("");
    try {
      const [m, c, t]: any[] = await Promise.all([
        request.get("/java/system/metrics"),
        request.get("/java/system/charts"),
        request.get("/python/agent/tasks?size=5"),
      ]);
      setMetrics(m.data);
      setCharts(c.data);
      setTasks(t.data.items);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    load();
    const timer = setInterval(load, 15000);
    return () => clearInterval(timer);
  }, []);
  const hours = Array.from({ length: 24 }, (_, i) => {
    const d = new Date();
    d.setHours(d.getHours() - 23 + i, 0, 0, 0);
    return d;
  });
  const trend = hours.map((d) => {
    const label = d.toISOString().slice(0, 13).replace("T", " ") + ":00";
    return (
      (charts.hourlyTrend || []).find((v: any) => v.hour === label)?.count || 0
    );
  });
  const color = dark ? "#8a9bb7" : "#6b7b94";
  return (
    <>
      <PageHeading
        label="OVERVIEW / 实时概览"
        title="让信息汇聚，让洞察发生"
        subtitle="从订阅源到可读内容，掌握每一次采集与推送。"
        extra={
          <Space>
            <Button onClick={load}>刷新数据</Button>
            <Button type="primary" onClick={() => navigate("/subscriptions")}>
              创建订阅
            </Button>
          </Space>
        }
      />
      {error && (
        <Alert
          type="error"
          showIcon
          message={error}
          action={<Button onClick={load}>重试</Button>}
          style={{ marginBottom: 20 }}
        />
      )}
      <div className="stat-grid">
        {[
          [
            "订阅规则",
            metrics.totalSubscriptions,
            "按你的关注持续追踪",
            "#38c9db",
          ],
          [
            "可读内容",
            metrics.totalContents,
            "已通过审核的采集内容",
            "#8b87fa",
          ],
          [
            "待审工单",
            metrics.pendingApprovals,
            "需要人工确认的内容",
            "#fbbf24",
          ],
          ["最近任务", tasks.length, "最近五次任务执行记录", "#34d399"],
        ].map(([label, value, caption, accent]) => (
          <div
            className="stat-panel"
            style={{ "--accent": accent } as any}
            key={String(label)}
          >
            <div className="stat-label">{label}</div>
            {loading ? (
              <Skeleton.Input active />
            ) : (
              <div className="stat-number">{value ?? 0}</div>
            )}
            <div className="stat-caption">{caption}</div>
          </div>
        ))}
      </div>
      <div className="charts-grid">
        <div className="panel">
          <div className="panel-title">
            24 小时采集趋势<span className="eyebrow">COLLECTION ACTIVITY</span>
          </div>
          <Chart
            option={{
              tooltip: { trigger: "axis" },
              grid: { left: 35, right: 16, bottom: 30, top: 20 },
              xAxis: {
                type: "category",
                data: hours.map(
                  (d) => String(d.getHours()).padStart(2, "0") + ":00",
                ),
                axisLabel: { color },
                axisLine: { lineStyle: { color: "#314057" } },
              },
              yAxis: {
                type: "value",
                minInterval: 1,
                axisLabel: { color },
                splitLine: {
                  lineStyle: { color: dark ? "#25324a" : "#e5edf5" },
                },
              },
              series: [
                {
                  type: "line",
                  smooth: true,
                  data: trend,
                  lineStyle: { color: "#38c9db", width: 3 },
                  itemStyle: { color: "#38c9db" },
                  areaStyle: { color: "#38c9db18" },
                },
              ],
            }}
            style={{ height: 260 }}
          />
        </div>
        <div className="panel">
          <div className="panel-title">
            内容来源<span className="eyebrow">SOURCE MIX</span>
          </div>
          {(charts.platformDistribution || []).length ? (
            <Chart
              option={{
                tooltip: { trigger: "item" },
                legend: { bottom: 0, textStyle: { color } },
                color: ["#38c9db", "#8b87fa", "#34d399"],
                series: [
                  {
                    type: "pie",
                    radius: ["52%", "75%"],
                    label: { show: false },
                    data: charts.platformDistribution.map((p: any) => ({
                      name: p.platform,
                      value: p.count,
                    })),
                  },
                ],
              }}
              style={{ height: 260 }}
            />
          ) : (
            <Empty
              description="完成首次采集后显示来源分布"
              style={{ paddingTop: 65 }}
            />
          )}
        </div>
      </div>
      <div className="panel">
        <div className="panel-title">
          最近任务
          <Button type="link" onClick={() => navigate("/tasks")}>
            查看全部 →
          </Button>
        </div>
        <Table
          size="small"
          rowKey="task_id"
          dataSource={tasks}
          loading={loading}
          pagination={false}
          scroll={{ x: 600 }}
          columns={[
            {
              title: "任务",
              dataIndex: "task_id",
              render: (v) => <code>{v.slice(0, 12)}</code>,
            },
            { title: "订阅", dataIndex: "subscription_id" },
            {
              title: "状态",
              dataIndex: "status",
              render: (v) => (
                <Tag
                  color={
                    v === "completed"
                      ? "success"
                      : v === "failed"
                        ? "error"
                        : "processing"
                  }
                >
                  {statusName(v)}
                </Tag>
              ),
            },
            { title: "新增", render: (_, r) => r.counts?.stored_count ?? "—" },
            {
              title: "详情",
              render: () => (
                <Button type="link" onClick={() => navigate("/tasks")}>
                  查看执行链路
                </Button>
              ),
            },
          ]}
        />
      </div>
    </>
  );
}
