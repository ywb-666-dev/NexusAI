import { useEffect, useState } from "react";
import {
  Alert,
  App,
  Button,
  Form,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
} from "antd";
import request from "../api/request";
import PageHeading from "../components/PageHeading";

export default function PushSettings() {
  const [channels, setChannels] = useState<any[]>([]),
    [deliveries, setDeliveries] = useState<any[]>([]),
    [open, setOpen] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [form] = Form.useForm();
  const { message } = App.useApp();
  const load = async () => {
    try {
      const [c, d]: any[] = await Promise.all([
        request.get("/python/push/channels"),
        request.get("/python/push/deliveries"),
      ]);
      setChannels(c.data);
      setDeliveries(d.data);
      setError("");
    } catch (e: any) {
      setError(e.message);
    }
  };
  useEffect(() => {
    load();
  }, []);
  const save = async () => {
    const values = await form.validateFields();
    setBusy(true);
    try {
      await request.post("/python/push/channels", values);
      message.success("推送渠道已保存");
      setOpen(false);
      form.resetFields();
      load();
    } catch (e: any) {
      message.error(e.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <PageHeading
        label="DELIVERY / 推送设置"
        title="让重要内容主动抵达"
        subtitle="配置飞书或钉钉机器人，接收采集结果及你手动发送或启用自动推送的个人情报简报。"
        extra={
          <Button type="primary" onClick={() => setOpen(true)}>
            添加推送渠道
          </Button>
        }
      />
      {error && (
        <Alert type="error" message={error} style={{ marginBottom: 20 }} />
      )}
      <Alert
        type="info"
        showIcon
        message="配置方式"
        description="在群聊中添加自定义机器人，将 Webhook 与签名密钥填入。保存后可手动发送测试消息，确认机器人配置有效。"
        style={{ marginBottom: 22 }}
      />
      <div className="panel" style={{ marginBottom: 22 }}>
        <div className="panel-title">推送渠道</div>
        <Table
          rowKey="id"
          dataSource={channels}
          pagination={false}
          columns={[
            { title: "渠道名称", dataIndex: "name" },
            {
              title: "平台",
              dataIndex: "provider",
              render: (v) => (
                <Tag color="cyan">{v === "feishu" ? "飞书" : "钉钉"}</Tag>
              ),
            },
            {
              title: "操作",
              render: (_, r) => (
                <Space>
                  <Popconfirm
                    title="向此机器人发送一条测试消息？"
                    onConfirm={async () => {
                      try {
                        await request.post(
                          "/python/push/channels/" + r.id + "/test",
                        );
                        message.success("测试消息已发送");
                      } catch (e: any) {
                        message.error(e.message);
                      }
                    }}
                  >
                    <Button type="link">测试连接</Button>
                  </Popconfirm>
                  <Popconfirm
                    title="删除此推送渠道？"
                    onConfirm={async () => {
                      try {
                        await request.delete("/python/push/channels/" + r.id);
                        load();
                      } catch (e: any) {
                        message.error(e.message);
                      }
                    }}
                  >
                    <Button type="link" danger>
                      删除
                    </Button>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </div>
      <div className="panel">
        <div className="panel-title">
          最近投递记录
          <Button type="link" onClick={load}>
            刷新
          </Button>
        </div>
        <Table
          rowKey="id"
          dataSource={deliveries}
          pagination={{ pageSize: 10 }}
          scroll={{ x: 600 }}
          columns={[
            {
              title: "来源",
              dataIndex: "task_id",
              render: (v) =>
                v.startsWith("briefing:") ? (
                  <a href={"/briefings?id=" + encodeURIComponent(v.slice(9))}>
                    个人情报简报
                  </a>
                ) : (
                  <code>{v.slice(0, 12)}</code>
                ),
            },
            {
              title: "渠道",
              dataIndex: "channel_id",
              render: (v) =>
                channels.find((c) => c.id === v)?.name || "已删除渠道",
            },
            {
              title: "状态",
              dataIndex: "status",
              render: (v) => (
                <Tag
                  color={
                    v === "sent"
                      ? "success"
                      : v === "failed"
                        ? "error"
                        : "processing"
                  }
                >
                  {{ sent: "已送达", failed: "失败", pending: "等待投递" }[
                    v as string
                  ] || v}
                </Tag>
              ),
            },
            { title: "尝试次数", dataIndex: "attempts" },
            { title: "说明", dataIndex: "error", render: (v) => v || "—" },
            {
              title: "操作",
              render: (_, r) =>
                r.status === "failed" ? (
                  <Button
                    type="link"
                    onClick={async () => {
                      try {
                        const result: any = await request.post(
                          "/python/push/deliveries/" + r.id + "/retry",
                        );
                        if (result.data.status === "sent")
                          message.success("投递成功");
                        else message.error(result.data.error);
                        load();
                      } catch (e: any) {
                        message.error(e.message);
                      }
                    }}
                  >
                    重试投递
                  </Button>
                ) : null,
            },
          ]}
        />
      </div>
      <Modal
        title="添加机器人"
        open={open}
        onCancel={() => setOpen(false)}
        onOk={save}
        confirmLoading={busy}
        okText="保存渠道"
        cancelText="取消"
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{ provider: "feishu", secret: "" }}
        >
          <Form.Item name="name" label="渠道名称" rules={[{ required: true }]}>
            <Input placeholder="例如：团队技术情报群" maxLength={100} />
          </Form.Item>
          <Form.Item name="provider" label="平台">
            <Select
              options={[
                { label: "飞书", value: "feishu" },
                { label: "钉钉", value: "dingtalk" },
              ]}
            />
          </Form.Item>
          <Form.Item
            name="webhook"
            label="机器人 Webhook"
            rules={[{ required: true }, { type: "url" }]}
          >
            <Input.Password autoComplete="off" placeholder="https://..." />
          </Form.Item>
          <Form.Item name="secret" label="签名密钥（机器人开启签名时填写）">
            <Input.Password autoComplete="new-password" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
