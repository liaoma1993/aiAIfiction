import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Alert, Button, Card, Descriptions, Drawer, Empty, Input, Select, Space, Statistic, Table, Tag, Typography, Row, Col, message } from 'antd';
import { ArrowLeftOutlined, CopyOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons';
import api from '@/services/api';

const { Title, Text, Paragraph } = Typography;

const statusMap: Record<string, { label: string; color: string }> = {
  success: { label: '成功', color: 'green' },
  failed: { label: '失败', color: 'red' },
};

const functionLabel: Record<string, string> = {
  generate_story_suggestions: '故事建议',
  chat_project_plan: '项目策划对话',
  generate_world_setting: '生成世界观',
  generate_characters: '生成角色',
  generate_factions: '生成势力',
  generate_outline_plan: '生成全书大纲',
  expand_volume_outline: '展开卷大纲',
  expand_volume_arcs: '展开卷弧线',
  revise_volume_arc: '调整弧线',
  expand_arc_chapters: '展开弧线章节',
  write_chapter: '写章节',
  audit_chapter: '审计章节',
  diagnose_chapter_before_write: '写前诊断',
  review_arc_structure: '弧线结构评审',
  review_chapter_blueprints: '章节蓝图评审',
  review_chapters: '评审章节',
  plan_review_repair: '评审修复计划',
  revise_chapter: '修订章节',
  extract_state_changes: '提取状态',
  generate_chapter_blueprint: '生成章节蓝图',
  adjust_outline: '调整大纲',
  chat_adjust_outline: '大纲调整对话',
  analyze_writing_style_skill: '分析写作风格',
  summarize_state: '总结状态',
  split_chapter: '拆分章节',
  split_chapter_metadata: '拆分章节元数据',
  test_provider: '测试模型',
  _ask_list: '结构列表生成',
  '_ask_list.json_repair': '结构列表生成 JSON 修复',
};

const fmt = (value: any) => {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString();
};

const projectLabel = (record: any) => {
  if (record?.project_name) return record.project_name;
  if (record?.project_id) return record.project_id;
  if (record?.function_name === 'chat_project_plan') return <Text type="secondary">项目创建前</Text>;
  return <Text type="secondary">未绑定</Text>;
};

const functionDisplay = (name?: string) => {
  if (!name) return '未知';
  if (functionLabel[name]) return functionLabel[name];
  if (name.endsWith('.json_repair')) {
    const base = name.replace(/\.json_repair$/, '');
    return `${functionLabel[base] || base} JSON 修复`;
  }
  return name.startsWith('_') ? `内部调用：${name}` : name;
};

const stringifyValue = (value: any) => (typeof value === 'string' ? value : JSON.stringify(value || {}, null, 2));

const copyToClipboard = async (value: any, title = '内容') => {
  const text = stringifyValue(value);
  try {
    await navigator.clipboard.writeText(text);
    message.success(`${title}已复制`);
  } catch {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.setAttribute('readonly', 'true');
    textarea.style.position = 'fixed';
    textarea.style.left = '-9999px';
    document.body.appendChild(textarea);
    textarea.select();
    const ok = document.execCommand('copy');
    document.body.removeChild(textarea);
    if (ok) {
      message.success(`${title}已复制`);
    } else {
      message.error('复制失败，请手动选择文本复制');
    }
  }
};

const JsonText = ({ title, value }: { title: string; value: any }) => {
  const text = stringifyValue(value);
  return (
  <Card
    size="small"
    title={title}
    extra={
      <Button
        size="small"
        icon={<CopyOutlined />}
        onClick={() => copyToClipboard(value, title)}
      >
        复制
      </Button>
    }
  >
    <pre style={{
      maxHeight: 360,
      overflow: 'auto',
      whiteSpace: 'pre-wrap',
      wordBreak: 'break-word',
      margin: 0,
      padding: 12,
      borderRadius: 6,
      background: '#0f172a',
      color: '#dbeafe',
      fontSize: 12,
      lineHeight: 1.6,
    }}>
      {text}
    </pre>
  </Card>
  );
};

export default function LLMCallLogsPage() {
  const navigate = useNavigate();
  const [logs, setLogs] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detail, setDetail] = useState<any>(null);
  const [total, setTotal] = useState(0);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 50 });
  const [filters, setFilters] = useState({ q: '', project_name: '', function_name: '', model_name: '', status: '' });

  const loadSummary = async () => {
    try {
      const res = await api.get('/llm-call-logs/summary');
      setSummary(res.data);
    } catch {
      setSummary(null);
    }
  };

  const loadLogs = async (page = pagination.current, pageSize = pagination.pageSize) => {
    setLoading(true);
    try {
      const params: any = {
        limit: pageSize,
        offset: (page - 1) * pageSize,
      };
      Object.entries(filters).forEach(([key, value]) => {
        if (value) params[key] = value;
      });
      const res = await api.get('/llm-call-logs', { params });
      setLogs(res.data.logs || []);
      setTotal(res.data.total || 0);
      setPagination({ current: page, pageSize });
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e.message || '加载调用记录失败');
    } finally {
      setLoading(false);
    }
  };

  const openDetail = async (id: string) => {
    setDetailOpen(true);
    setDetailLoading(true);
    try {
      const res = await api.get(`/llm-call-logs/${id}`);
      setDetail(res.data.log);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e.message || '加载详情失败');
    } finally {
      setDetailLoading(false);
    }
  };

  useEffect(() => {
    loadSummary();
    loadLogs(1, pagination.pageSize);
  }, []);

  const functionOptions = Object.entries(functionLabel).map(([value, label]) => ({ value, label }));
  const statusOptions = [
    { value: 'success', label: '成功' },
    { value: 'failed', label: '失败' },
  ];

  return (
    <div style={{ maxWidth: 1280, margin: '0 auto', padding: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16, marginBottom: 16 }}>
        <Space align="center">
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/dashboard')}>返回项目列表</Button>
          <div>
            <Title level={3} style={{ margin: 0 }}>模型调用记录</Title>
            <Text type="secondary">记录每次模型调用的项目、功能、提示词、返回内容、token 和耗时。</Text>
          </div>
        </Space>
        <Button icon={<ReloadOutlined />} loading={loading} onClick={() => { loadSummary(); loadLogs(); }}>刷新</Button>
      </div>

      <Row gutter={[12, 12]} style={{ marginBottom: 12 }}>
        {[
          ['总调用', summary?.total_calls ?? 0],
          ['成功率', `${summary?.success_rate ?? 100}%`],
          ['入 Token', summary?.input_tokens ?? 0],
          ['出 Token', summary?.output_tokens ?? 0],
          ['总 Token', summary?.total_tokens ?? 0],
        ].map(([title, value]) => (
          <Col xs={12} md={4} key={title}>
            <Card size="small"><Statistic title={title} value={value as any} /></Card>
          </Col>
        ))}
      </Row>

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 12 }}
        message="模型调用会自动绑定项目上下文；项目创建前的策划对话会显示为“项目创建前”。"
      />

      <Card style={{ marginBottom: 12 }}>
        <Space wrap>
          <Input
            allowClear
            prefix={<SearchOutlined />}
            placeholder="搜索提示词/返回/项目/功能"
            value={filters.q}
            onChange={(e) => setFilters((prev) => ({ ...prev, q: e.target.value }))}
            onPressEnter={() => loadLogs(1)}
            style={{ width: 260 }}
          />
          <Input
            allowClear
            placeholder="项目名"
            value={filters.project_name}
            onChange={(e) => setFilters((prev) => ({ ...prev, project_name: e.target.value }))}
            onPressEnter={() => loadLogs(1)}
            style={{ width: 180 }}
          />
          <Select
            allowClear
            showSearch
            placeholder="功能名称"
            value={filters.function_name || undefined}
            onChange={(v) => setFilters((prev) => ({ ...prev, function_name: v || '' }))}
            options={functionOptions}
            style={{ width: 190 }}
          />
          <Input
            allowClear
            placeholder="模型名"
            value={filters.model_name}
            onChange={(e) => setFilters((prev) => ({ ...prev, model_name: e.target.value }))}
            onPressEnter={() => loadLogs(1)}
            style={{ width: 170 }}
          />
          <Select
            allowClear
            placeholder="状态"
            value={filters.status || undefined}
            onChange={(v) => setFilters((prev) => ({ ...prev, status: v || '' }))}
            options={statusOptions}
            style={{ width: 120 }}
          />
          <Button type="primary" onClick={() => loadLogs(1)}>筛选</Button>
          <Button onClick={() => {
            setFilters({ q: '', project_name: '', function_name: '', model_name: '', status: '' });
            window.setTimeout(() => loadLogs(1), 0);
          }}>清空</Button>
        </Space>
      </Card>

      <Card>
        <Table
          rowKey="id"
          loading={loading}
          dataSource={logs}
          locale={{ emptyText: <Empty description="暂无模型调用记录" /> }}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total,
            showSizeChanger: true,
            pageSizeOptions: [20, 50, 100, 200],
            onChange: loadLogs,
          }}
          columns={[
            {
              title: '时间',
              dataIndex: 'created_at',
              width: 170,
              render: fmt,
            },
            {
              title: '项目',
              dataIndex: 'project_name',
              width: 180,
              ellipsis: true,
              render: (_v: string, record: any) => projectLabel(record),
            },
            {
              title: '功能',
              dataIndex: 'function_name',
              width: 170,
              render: (v: string) => <Tag>{functionDisplay(v)}</Tag>,
            },
            {
              title: '模型',
              dataIndex: 'model_name',
              width: 190,
              ellipsis: true,
              render: (v: string, record: any) => (
                <Space direction="vertical" size={0}>
                  <Text>{v || '未知'}</Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>{record.provider_name || record.provider_type || '-'}</Text>
                </Space>
              ),
            },
            {
              title: '状态',
              dataIndex: 'status',
              width: 90,
              render: (v: string) => {
                const item = statusMap[v] || { label: v || '未知', color: 'default' };
                return <Tag color={item.color}>{item.label}</Tag>;
              },
            },
            {
              title: 'Token',
              width: 150,
              render: (_: any, record: any) => (
                <Space direction="vertical" size={0}>
                  <Text>{record.total_tokens || 0}</Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>入 {record.input_tokens || 0} / 出 {record.output_tokens || 0}</Text>
                </Space>
              ),
            },
            {
              title: '耗时',
              dataIndex: 'duration_ms',
              width: 100,
              render: (v: number) => `${Math.round((v || 0) / 100) / 10}s`,
            },
            {
              title: '预览',
              dataIndex: 'prompt_preview',
              ellipsis: true,
              render: (v: string, record: any) => (
                <Paragraph ellipsis={{ rows: 2 }} style={{ margin: 0 }}>
                  {record.status === 'failed' ? record.error_message || v : v || record.response_preview || '-'}
                </Paragraph>
              ),
            },
            {
              title: '操作',
              width: 90,
              render: (_: any, record: any) => <Button size="small" onClick={() => openDetail(record.id)}>详情</Button>,
            },
          ]}
        />
      </Card>

      <Drawer
        title="调用详情"
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        width={860}
        loading={detailLoading}
      >
        {detail ? (
          <Space direction="vertical" size={12} style={{ width: '100%' }}>
            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="项目">{projectLabel(detail)}</Descriptions.Item>
              <Descriptions.Item label="功能">{functionDisplay(detail.function_name)}</Descriptions.Item>
              <Descriptions.Item label="模型">{detail.model_name || '-'}</Descriptions.Item>
              <Descriptions.Item label="供应商">{detail.provider_name || detail.provider_type || '-'}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={(statusMap[detail.status] || {}).color}>{(statusMap[detail.status] || {}).label || detail.status}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="时间">{fmt(detail.created_at)}</Descriptions.Item>
              <Descriptions.Item label="Token">入 {detail.input_tokens || 0} / 出 {detail.output_tokens || 0} / 总 {detail.total_tokens || 0}</Descriptions.Item>
              <Descriptions.Item label="耗时">{detail.duration_ms || 0} ms</Descriptions.Item>
              <Descriptions.Item label="temperature">{detail.temperature || '-'}</Descriptions.Item>
              <Descriptions.Item label="max_tokens">{detail.max_tokens || '-'}</Descriptions.Item>
            </Descriptions>
            {detail.error_message && <Alert type="error" showIcon message="调用失败" description={detail.error_message} />}
            <JsonText title="系统提示词" value={detail.system_prompt || '无'} />
            <JsonText title="发送提示词" value={detail.prompt || '无'} />
            <JsonText title="得到的内容" value={detail.response_content || '无'} />
            <JsonText title="响应元信息" value={detail.response_metadata || {}} />
          </Space>
        ) : (
          <Empty description="暂无详情" />
        )}
      </Drawer>
    </div>
  );
}
