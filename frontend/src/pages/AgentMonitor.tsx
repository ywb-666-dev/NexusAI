import { useEffect, useState, useCallback, useMemo } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { Card, Select, Tag, Descriptions, Empty, Button, Space, Typography, Steps } from 'antd'
import {
  ReloadOutlined,
  ApiOutlined,
  LinkOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  PauseCircleOutlined,
  MinusCircleOutlined,
} from '@ant-design/icons'
import request from '../api/request'

const { Title, Text } = Typography

interface NodeStatus {
  status: 'idle' | 'running' | 'success' | 'failed' | 'interrupted'
  timestamp: string | null
}

interface TaskStatus {
  task_id: string
  status: string
  nodes: Record<string, NodeStatus>
  updated_at: string | null
}

const NODE_COLORS: Record<string, string> = {
  idle: '#e2e8f0',
  running: '#6366f1',
  success: '#10b981',
  failed: '#ef4444',
  interrupted: '#f59e0b',
}

const NODE_LABELS: Record<string, string> = {
  idle: '空闲',
  running: '运行中',
  success: '成功',
  failed: '失败',
  interrupted: '中断',
}

const NODE_ICONS: Record<string, React.ReactNode> = {
  idle: <MinusCircleOutlined />,
  running: <LoadingOutlined spin />,
  success: <CheckCircleOutlined />,
  failed: <CloseCircleOutlined />,
  interrupted: <PauseCircleOutlined />,
}

const AGENT_DEFS = [
  { id: 'scout', label: 'Scout\n侦察采集', description: '从 RSS/Web/API 采集原始内容', index: 0 },
  { id: 'parser', label: 'Parser\n解析清洗', description: '解析内容、格式清洗', index: 1 },
  { id: 'connector', label: 'Connector\n关联去重', description: '语义去重与内容关联', index: 2 },
  { id: 'actor', label: 'Actor\n决策行动', description: '审批决策与动作执行', index: 3 },
  { id: 'curator', label: 'Curator\n日报生成', description: '生成内容日报摘要', index: 4 },
]

const EDGE_DEFS: Edge[] = [
  { id: 'e-scout-parser', source: 'scout', target: 'parser', animated: false, style: { stroke: '#cbd5e1' } },
  { id: 'e-parser-connector', source: 'parser', target: 'connector', animated: false, style: { stroke: '#cbd5e1' } },
  { id: 'e-connector-actor', source: 'connector', target: 'actor', animated: false, style: { stroke: '#cbd5e1' } },
  { id: 'e-actor-curator', source: 'actor', target: 'curator', animated: false, style: { stroke: '#cbd5e1' } },
]

const STATUS_ORDER = ['idle', 'running', 'interrupted', 'success', 'failed']

const NODE_X_START = 80
const NODE_X_GAP = 240
const NODE_Y = 180

function buildNodes(nodeStates: Record<string, NodeStatus>): Node[] {
  return AGENT_DEFS.map((def) => {
    const ns = nodeStates[def.id] || { status: 'idle', timestamp: null }
    const isRunning = ns.status === 'running'
    const isSuccess = ns.status === 'success'
    const isFailed = ns.status === 'failed'

    return {
      id: def.id,
      type: 'default',
      position: { x: NODE_X_START + def.index * NODE_X_GAP, y: NODE_Y },
      data: { label: def.label },
      style: {
        background: isRunning
          ? 'linear-gradient(135deg, #6366f1, #818cf8)'
          : isSuccess
            ? 'linear-gradient(135deg, #10b981, #34d399)'
            : isFailed
              ? 'linear-gradient(135deg, #ef4444, #f87171)'
              : NODE_COLORS[ns.status],
        color: ns.status === 'idle' ? '#64748b' : '#fff',
        border: isRunning ? '2px solid #4338ca' : '2px solid transparent',
        borderRadius: 14,
        padding: '22px 28px',
        fontSize: 13.5,
        fontWeight: 600,
        width: 160,
        textAlign: 'center' as const,
        whiteSpace: 'pre-line' as const,
        transition: 'all 0.3s ease',
        boxShadow: isRunning
          ? '0 0 24px rgba(99,102,241,0.5), 0 4px 12px rgba(99,102,241,0.3)'
          : isSuccess
            ? '0 4px 16px rgba(16,185,129,0.15)'
            : isFailed
              ? '0 4px 16px rgba(239,68,68,0.15)'
              : '0 2px 8px rgba(0,0,0,0.06)',
      },
    } as Node
  })
}

function buildEdges(nodeStates: Record<string, NodeStatus>): Edge[] {
  return EDGE_DEFS.map((e) => {
    const srcStatus = nodeStates[e.source]?.status || 'idle'
    const tgtStatus = nodeStates[e.target]?.status || 'idle'
    const srcIdx = STATUS_ORDER.indexOf(srcStatus)
    const tgtIdx = STATUS_ORDER.indexOf(tgtStatus)
    const active = srcIdx >= STATUS_ORDER.indexOf('success') && tgtIdx >= STATUS_ORDER.indexOf('idle')
    const running = tgtStatus === 'running'
    return {
      ...e,
      animated: running,
      style: {
        stroke: active ? '#10b981' : running ? '#818cf8' : '#cbd5e1',
        strokeWidth: active ? 2.5 : running ? 2 : 1.5,
        transition: 'all 0.3s ease',
      },
    }
  })
}

function AgentMonitor() {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
  const [tasks, setTasks] = useState<TaskStatus[]>([])
  const [selectedTaskId, setSelectedTaskId] = useState<string | undefined>()
  const [currentTask, setCurrentTask] = useState<TaskStatus | null>(null)
  const [wsConnected, setWsConnected] = useState(false)

  const fetchTasks = useCallback(async () => {
    try {
      const res: any = await request.get('/python/agent/tasks?size=50')
      const items = res.data?.items || []
      setTasks(items)
      if (items.length > 0 && !selectedTaskId) {
        setSelectedTaskId(items[0].task_id)
      }
    } catch { /* ignore */ }
  }, [selectedTaskId])

  useEffect(() => { fetchTasks() }, [])

  // WebSocket with auto-reconnect
  useEffect(() => {
    if (!selectedTaskId) return
    let ws: WebSocket | null = null
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null
    let attempt = 0
    const maxBackoff = 30000

    function connect() {
      if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return
      const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
      const wsUrl = `${protocol}://${window.location.host}/api/python/ws/agent/${selectedTaskId}`
      ws = new WebSocket(wsUrl)
      ws.onopen = () => { setWsConnected(true); attempt = 0 }
      ws.onclose = () => {
        setWsConnected(false); ws = null
        const delay = Math.min(1000 * Math.pow(2, attempt), maxBackoff)
        attempt++; reconnectTimer = setTimeout(connect, delay)
      }
      ws.onerror = () => { setWsConnected(false); ws?.close() }
      ws.onmessage = (evt) => {
        try {
          const data: TaskStatus = JSON.parse(evt.data)
          setCurrentTask(data)
          setTasks((prev) => prev.map((t) => (t.task_id === data.task_id ? { ...t, ...data } : t)))
        } catch { /* ignore */ }
      }
    }
    connect()
    return () => {
      if (reconnectTimer) clearTimeout(reconnectTimer)
      if (ws) { ws.onclose = null; ws.close(); ws = null }
    }
  }, [selectedTaskId])

  const nodeStates = useMemo(() => {
    if (!currentTask) {
      const empty: Record<string, NodeStatus> = {}
      AGENT_DEFS.forEach((d) => { empty[d.id] = { status: 'idle' as const, timestamp: null } })
      return empty
    }
    return currentTask.nodes || {}
  }, [currentTask])

  useEffect(() => {
    setNodes(buildNodes(nodeStates))
    setEdges(buildEdges(nodeStates))
  }, [nodeStates, setNodes, setEdges])

  const taskOptions = tasks.map((t) => ({
    value: t.task_id,
    label: `${t.task_id.slice(0, 8)}... — ${t.status}`,
  }))

  const defaultEdgeOptions = useMemo(() => ({ type: 'smoothstep' as const }), [])

  const getStatusColor = (status: string) =>
    status.includes('completed') ? 'success' : status.includes('error') ? 'error' : 'processing'

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <Title level={4} style={{ margin: 0, fontWeight: 700 }}>
          <ApiOutlined style={{ marginRight: 8 }} />
          Agent 监控
        </Title>
        <Text type="secondary" style={{ marginTop: 4, display: 'block' }}>
          LangGraph 五节点状态机实时可视化
        </Text>
      </div>

      {/* Control bar */}
      <Card
        style={{
          marginBottom: 20,
          borderRadius: 14,
          border: 'none',
          boxShadow: '0 2px 12px rgba(0,0,0,0.04)',
        }}
        bodyStyle={{ padding: '18px 24px' }}
      >
        <div style={{ display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Tag
              color={wsConnected ? 'success' : 'error'}
              icon={wsConnected ? <LinkOutlined /> : <CloseCircleOutlined />}
              style={{ borderRadius: 6 }}
            >
              {wsConnected ? 'WebSocket 已连接' : 'WebSocket 断开'}
            </Tag>
          </div>
          <span style={{ fontWeight: 600, color: '#475569' }}>选择任务：</span>
          <Select
            style={{ width: 360 }}
            value={selectedTaskId}
            onChange={(v) => {
              setSelectedTaskId(v)
              const task = tasks.find((t) => t.task_id === v)
              if (task) setCurrentTask(task)
            }}
            options={taskOptions}
            placeholder="选择一个 Agent 任务"
            notFoundContent={<Empty description="暂无任务记录，请先触发采集" />}
          />
          {currentTask && (
            <Tag color={getStatusColor(currentTask.status)} style={{ borderRadius: 6 }}>
              {currentTask.status}
            </Tag>
          )}
          <Button
            icon={<ReloadOutlined />}
            onClick={fetchTasks}
            style={{ borderRadius: 8, marginLeft: 'auto' }}
          >
            刷新任务列表
          </Button>
        </div>
      </Card>

      {/* Flow + Node status side by side */}
      <div style={{ display: 'flex', gap: 20, marginBottom: 20 }}>
        <Card
          title={
            <Space>
              <ApiOutlined style={{ color: '#6366f1' }} />
              <span style={{ fontWeight: 600 }}>LangGraph 状态机</span>
            </Space>
          }
          style={{
            flex: 1,
            borderRadius: 14,
            border: 'none',
            boxShadow: '0 2px 12px rgba(0,0,0,0.04)',
          }}
          bodyStyle={{ padding: 0 }}
        >
          <div style={{ height: 400 }}>
            {currentTask ? (
              <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                defaultEdgeOptions={defaultEdgeOptions}
                fitView
                nodesDraggable={false}
                nodesConnectable={false}
                elementsSelectable={false}
              >
                <Background color="#f1f5f9" gap={20} />
                <Controls showInteractive={false} style={{ borderRadius: 8, overflow: 'hidden' }} />
                <MiniMap
                  nodeColor={(n) => (n.style?.background as string) || '#d9d9d9'}
                  maskColor="rgba(0,0,0,0.06)"
                  style={{ borderRadius: 8 }}
                />
              </ReactFlow>
            ) : (
              <Empty
                description="请先触发一个采集任务，然后选择任务查看状态机"
                style={{ marginTop: 140 }}
              />
            )}
          </div>
        </Card>

        <Card
          title={
            <Space>
              <CheckCircleOutlined style={{ color: '#10b981' }} />
              <span style={{ fontWeight: 600 }}>节点状态</span>
            </Space>
          }
          style={{
            width: 300,
            borderRadius: 14,
            border: 'none',
            boxShadow: '0 2px 12px rgba(0,0,0,0.04)',
          }}
        >
          {currentTask ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {AGENT_DEFS.map((def, i) => {
                const ns = nodeStates[def.id]
                const status = ns?.status || 'idle'
                return (
                  <div
                    key={def.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 12,
                      padding: '10px 14px',
                      borderRadius: 10,
                      background: status === 'running' ? '#f0f0ff' : '#fafafa',
                      border: status === 'running' ? '1px solid #d4d4f8' : '1px solid transparent',
                      transition: 'all 0.3s ease',
                    }}
                  >
                    <div
                      style={{
                        width: 36,
                        height: 36,
                        borderRadius: 10,
                        background: NODE_COLORS[status],
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: status === 'idle' ? '#64748b' : '#fff',
                        fontSize: 14,
                        flexShrink: 0,
                      }}
                    >
                      {NODE_ICONS[status]}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 600, fontSize: 13, color: '#334155' }}>
                        {def.label.replace('\n', ' ')}
                      </div>
                      <Text style={{ fontSize: 12, color: '#94a3b8' }}>
                        {def.description}
                      </Text>
                      {ns?.timestamp && (
                        <div style={{ fontSize: 11, color: '#cbd5e1', marginTop: 2 }}>
                          {new Date(ns.timestamp).toLocaleTimeString()}
                        </div>
                      )}
                    </div>
                    <Tag
                      color={NODE_COLORS[status] === '#e2e8f0' ? 'default' : undefined}
                      style={{
                        borderRadius: 6,
                        fontSize: 11,
                        background: status === 'idle' ? '#e2e8f0' : undefined,
                        border: 'none',
                        color: status === 'idle' ? '#94a3b8' : '#fff',
                        ...(status !== 'idle' && { background: NODE_COLORS[status] }),
                      }}
                    >
                      {NODE_LABELS[status]}
                    </Tag>
                  </div>
                )
              })}
            </div>
          ) : (
            <Empty description="无任务" />
          )}
        </Card>
      </div>

      {/* Detail card */}
      <Card
        title={
          <Space>
            <span style={{ fontWeight: 600 }}>任务详情</span>
          </Space>
        }
        style={{
          borderRadius: 14,
          border: 'none',
          boxShadow: '0 2px 12px rgba(0,0,0,0.04)',
        }}
      >
        {currentTask ? (
          <Descriptions column={4} size="small" bordered>
            <Descriptions.Item label="任务ID">
              <Text code>{currentTask.task_id}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={getStatusColor(currentTask.status)} style={{ borderRadius: 6 }}>
                {currentTask.status}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="更新时间">
              {currentTask.updated_at ? new Date(currentTask.updated_at).toLocaleString() : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="实时连接">
              <Tag
                icon={wsConnected ? <LinkOutlined /> : <CloseCircleOutlined />}
                color={wsConnected ? 'success' : 'error'}
                style={{ borderRadius: 6 }}
              >
                {wsConnected ? 'WebSocket 实时推送中' : 'WebSocket 已断开'}
              </Tag>
            </Descriptions.Item>
          </Descriptions>
        ) : (
          <Empty description="无任务数据" />
        )}
      </Card>
    </div>
  )
}

export default AgentMonitor
