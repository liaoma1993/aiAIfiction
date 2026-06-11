import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Alert, Button, Card, Col, message, Progress, Row, Space, Spin, Statistic, Table, Tabs, Tag, Typography } from 'antd';
import { AuditOutlined, BarChartOutlined, BranchesOutlined, DatabaseOutlined, ExclamationCircleOutlined, LeftOutlined, ToolOutlined } from '@ant-design/icons';
import { chapterApi, storyApi } from '@/services/projectApi';
import api from '@/services/api';

const { Title, Text } = Typography;

const QUALITY_DIMENSION_LABELS: Record<string, string> = {
  ai_flavor: 'AI味控制',
  character_consistency: '角色一致性',
  dialogue: '对白自然度',
  hook: '章节钩子',
  punctuation: '标点规范',
  readability: '阅读易懂度',
  scene_clarity: '场景清晰度',
  plot_logic: '情节逻辑',
  continuity: '连续性',
  pacing: '节奏控制',
  emotion: '情绪感染力',
  prose: '文笔质感',
};

const CHAPTER_STATUS_LABELS: Record<string, { label: string; color: string }> = {
  planned: { label: '已规划', color: 'default' },
  writing: { label: '写作中', color: 'blue' },
  written: { label: '已写完', color: 'green' },
  completed: { label: '已完成', color: 'green' },
  reviewed: { label: '已审稿', color: 'purple' },
  failed: { label: '失败', color: 'red' },
};

const SEVERITY_LABELS: Record<string, { label: string; color: string }> = {
  critical: { label: '致命', color: 'red' },
  high: { label: '严重', color: 'red' },
  medium: { label: '中等', color: 'orange' },
  low: { label: '轻微', color: 'blue' },
  致命: { label: '致命', color: 'red' },
  严重: { label: '严重', color: 'red' },
  中等: { label: '中等', color: 'orange' },
  轻微: { label: '轻微', color: 'blue' },
};

const SCOPE_LABELS: Record<string, { label: string; color: string }> = {
  project: { label: '项目', color: 'purple' },
  world: { label: '世界观', color: 'cyan' },
  outline: { label: '大纲', color: 'geekblue' },
  volume: { label: '卷轴', color: 'blue' },
  arc: { label: '弧线', color: 'gold' },
  chapter: { label: '章节', color: 'green' },
  task: { label: '任务', color: 'red' },
  model: { label: '模型', color: 'volcano' },
};

const scoreColor = (score?: number | null) => {
  if (!score) return 'default';
  if (score >= 8) return 'green';
  if (score >= 7) return 'blue';
  if (score >= 6) return 'orange';
  return 'red';
};

const percentColor = (score?: number | null) => {
  if (score === null || score === undefined) return '#d9d9d9';
  if (score >= 85) return '#52c41a';
  if (score >= 75) return '#1677ff';
  if (score >= 60) return '#faad14';
  return '#ff4d4f';
};

const dimensionLabel = (name: string) => QUALITY_DIMENSION_LABELS[name] || name;

const renderChapterStatus = (status: string) => {
  const info = CHAPTER_STATUS_LABELS[status] || { label: status || '未知', color: 'default' };
  return <Tag color={info.color}>{info.label}</Tag>;
};

const renderSeverity = (severity: string) => {
  if (!severity) return '-';
  const info = SEVERITY_LABELS[severity] || { label: severity, color: 'default' };
  return <Tag color={info.color}>{info.label}</Tag>;
};

const renderScope = (scope: string) => {
  const info = SCOPE_LABELS[scope] || { label: scope || '未知', color: 'default' };
  return <Tag color={info.color}>{info.label}</Tag>;
};

const issueText = (issue: any) => {
  if (!issue) return '-';
  if (typeof issue === 'string') return issue;
  return issue.description || issue.issue || issue.fix_suggestion || JSON.stringify(issue);
};

const LOCAL_FIX_MODES: Record<string, string> = {
  sentence: 'target_sentence_fix',
  paragraph: 'target_paragraph_fix',
  context: 'target_context_fix',
};
const QUALITY_REFRESH_EVENT = 'aifiction:quality-updated';
const QUALITY_REFRESH_KEY = 'aifiction:quality-updated';

const notifyQualityUpdated = (projectId?: string, chapterId?: string) => {
  if (!projectId) return;
  const payload = { projectId, chapterId, ts: Date.now() };
  window.dispatchEvent(new CustomEvent(QUALITY_REFRESH_EVENT, { detail: payload }));
  try {
    localStorage.setItem(QUALITY_REFRESH_KEY, JSON.stringify(payload));
  } catch {
    // Same-tab event is enough when storage is unavailable.
  }
};

const extractIssueTarget = (issue: any, source: string) => {
  const direct = String(issue?.target_text || '').trim();
  if (direct && source.includes(direct)) return direct;
  const haystack = `${issue?.description || issue?.issue || ''}\n${issue?.fix_suggestion || ''}`;
  const matches = [
    ...haystack.matchAll(/“([^”]{2,80})”/g),
    ...haystack.matchAll(/"([^"]{2,80})"/g),
    ...haystack.matchAll(/'([^']{2,80})'/g),
  ];
  return matches.map((m) => m[1]?.trim()).find((text) => text && source.includes(text)) || direct;
};

const paragraphByTarget = (source: string, target: string) => {
  const index = source.indexOf(target);
  if (index < 0) return '';
  const before = source.lastIndexOf('\n', index);
  const after = source.indexOf('\n', index + target.length);
  return source.slice(before + 1, after === -1 ? source.length : after).trim();
};

const contextBlockByTarget = (source: string, target: string) => {
  const index = source.indexOf(target);
  if (index < 0) return '';
  const paragraphs = source.split(/\n+/);
  let cursor = 0;
  let targetIndex = -1;
  for (let i = 0; i < paragraphs.length; i += 1) {
    const paragraph = paragraphs[i];
    const start = cursor;
    const end = start + paragraph.length;
    if (index >= start && index <= end) {
      targetIndex = i;
      break;
    }
    cursor = end + 1;
  }
  if (targetIndex < 0) return paragraphByTarget(source, target);
  return paragraphs.slice(Math.max(0, targetIndex - 2), Math.min(paragraphs.length, targetIndex + 2)).join('\n').trim();
};

export default function QualityDashboardPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [repairingKey, setRepairingKey] = useState<string | null>(null);

  const loadDashboard = (silent = false) => {
    if (!projectId) return;
    if (!silent) setLoading(true);
    storyApi.qualityDashboard(projectId).then(setData).finally(() => setLoading(false));
  };

  useEffect(() => {
    loadDashboard();
  }, [projectId]);

  useEffect(() => {
    if (!projectId) return;
    const refreshIfSameProject = (payload: any) => {
      if (payload?.projectId === projectId) loadDashboard(true);
    };
    const onQualityUpdated = (event: Event) => {
      refreshIfSameProject((event as CustomEvent).detail);
    };
    const onStorage = (event: StorageEvent) => {
      if (event.key !== QUALITY_REFRESH_KEY || !event.newValue) return;
      try {
        refreshIfSameProject(JSON.parse(event.newValue));
      } catch {
        // Ignore malformed cross-tab payloads.
      }
    };
    window.addEventListener(QUALITY_REFRESH_EVENT, onQualityUpdated);
    window.addEventListener('storage', onStorage);
    return () => {
      window.removeEventListener(QUALITY_REFRESH_EVENT, onQualityUpdated);
      window.removeEventListener('storage', onStorage);
    };
  }, [projectId]);

  const pollTask = async (taskId: string, maxRetries = 120) => {
    if (!projectId) return null;
    for (let i = 0; i < maxRetries; i++) {
      await new Promise((resolve) => setTimeout(resolve, 1000));
      const res = await api.get(`/projects/${projectId}/wizard/task/${taskId}`);
      if (res.data.status === 'completed') return res.data.result;
      if (res.data.status === 'failed') throw new Error(res.data.error || '修复失败');
    }
    throw new Error('修复超时');
  };

  const repairIssue = async (record: any, scope: 'sentence' | 'paragraph' | 'context', key: string) => {
    if (!projectId || !record?.chapter_id) return;
    setRepairingKey(key);
    try {
      const chapter = await chapterApi.get(projectId, record.chapter_id);
      const content = chapter?.content || '';
      const issue = typeof record.raw_issue === 'object' ? record.raw_issue : {
        description: record.issue,
        severity: record.severity,
        target_text: record.target_text,
        fix_mode: record.fix_mode,
        fix_suggestion: record.fix_suggestion,
      };
      const target = extractIssueTarget(issue, content);
      if (!target || !content.includes(target)) {
        message.warning('老审计没有可定位原文，先点「重新审计定位」；急着处理可用「整章轻修」');
        return;
      }
      const selection = scope === 'sentence'
        ? target
        : scope === 'context'
          ? contextBlockByTarget(content, target)
          : paragraphByTarget(content, target);
      if (!selection || !content.includes(selection)) {
        message.warning('没有定位到可替换段落，请进入工作台手动处理');
        return;
      }
      const res = await api.post(`/projects/${projectId}/wizard/revise-chapter/${record.chapter_id}`, {
        mode: LOCAL_FIX_MODES[scope],
        instruction: `从质量仪表盘修复这条问题，只能改选择范围内文字。问题：${JSON.stringify(issue)}`,
        selection,
        controls: { readability_mode: 'easy', punctuation_style: 'standard' },
        apply: true,
      });
      message.loading({
        content: scope === 'sentence' ? 'AI 正在只修原句…' : scope === 'context' ? 'AI 正在深修此问题…' : 'AI 正在修这一段…',
        key: 'quality-repair',
        duration: 0,
      });
      await pollTask(res.data.task_id);
      message.success({ content: '修复完成，已重新评分并刷新质量仪表盘', key: 'quality-repair' });
      notifyQualityUpdated(projectId, record.chapter_id);
    } catch (e: any) {
      message.error({ content: e?.response?.data?.detail || e.message || '修复失败', key: 'quality-repair' });
    } finally {
      setRepairingKey(null);
    }
  };

  const reAuditChapter = async (record: any, key: string) => {
    if (!projectId || !record?.chapter_id) return;
    setRepairingKey(key);
    try {
      const res = await api.post(`/projects/${projectId}/wizard/audit-chapter/${record.chapter_id}`);
      message.loading({ content: 'AI 正在重新审计并补定位…', key: 'quality-audit', duration: 0 });
      await pollTask(res.data.task_id, 60);
      message.success({ content: '重新审计完成，已刷新定位信息', key: 'quality-audit' });
      notifyQualityUpdated(projectId, record.chapter_id);
    } catch (e: any) {
      message.error({ content: e?.response?.data?.detail || e.message || '重新审计失败', key: 'quality-audit' });
    } finally {
      setRepairingKey(null);
    }
  };

  const lightFixChapter = async (record: any, key: string) => {
    if (!projectId || !record?.chapter_id) return;
    setRepairingKey(key);
    try {
      const issue = typeof record.raw_issue === 'object' ? record.raw_issue : {
        description: record.issue,
        severity: record.severity,
        fix_suggestion: record.fix_suggestion,
      };
      const res = await api.post(`/projects/${projectId}/wizard/revise-chapter/${record.chapter_id}`, {
        mode: 'quality_light_fix',
        instruction: `根据质量仪表盘这条问题做轻量修复。优先修复该问题，保留剧情、人物关系、关键线索和章末钩子。问题：${JSON.stringify(issue)}`,
        selection: '',
        controls: { readability_mode: 'easy', punctuation_style: 'standard' },
        apply: true,
      });
      message.loading({ content: 'AI 正在整章轻修…', key: 'quality-light-fix', duration: 0 });
      await pollTask(res.data.task_id);
      message.success({ content: '整章轻修完成，已重新评分并刷新', key: 'quality-light-fix' });
      notifyQualityUpdated(projectId, record.chapter_id);
    } catch (e: any) {
      message.error({ content: e?.response?.data?.detail || e.message || '整章轻修失败', key: 'quality-light-fix' });
    } finally {
      setRepairingKey(null);
    }
  };

  const completeIssue = async (record: any, key: string) => {
    if (!projectId || !record?.chapter_id) return;
    setRepairingKey(key);
    try {
      await api.post(`/projects/${projectId}/story/quality-dashboard/complete-issue`, {
        chapter_id: record.chapter_id,
        issue_index: typeof record.issue_index === 'number' ? record.issue_index : undefined,
        issue: record.issue || '',
      });
      message.success('已标记为修复完成');
      notifyQualityUpdated(projectId, record.chapter_id);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e.message || '标记失败');
    } finally {
      setRepairingKey(null);
    }
  };

  const repairActions = (record: any, prefix: string) => {
    const issue = typeof record.raw_issue === 'object' ? record.raw_issue : record;
    const target = String(issue?.target_text || record?.target_text || '').trim();
    const preferredScope = issue?.fix_mode === 'paragraph' || issue?.fix_mode === 'context' ? issue.fix_mode : 'sentence';
    const hasNewLocator = !!target;
    return (
      <Space size={4} wrap>
        <Button
          size="small"
          icon={<ToolOutlined />}
          disabled={!!repairingKey}
          loading={repairingKey === `${prefix}-sentence`}
          onClick={() => repairIssue(record, 'sentence', `${prefix}-sentence`)}
        >
          只修原句
        </Button>
        <Button
          size="small"
          disabled={!!repairingKey}
          loading={repairingKey === `${prefix}-paragraph`}
          onClick={() => repairIssue(record, preferredScope === 'context' ? 'context' : 'paragraph', `${prefix}-paragraph`)}
        >
          {preferredScope === 'context' ? '修局部' : '修这一段'}
        </Button>
        <Button
          size="small"
          disabled={!!repairingKey}
          loading={repairingKey === `${prefix}-context`}
          onClick={() => repairIssue(record, 'context', `${prefix}-context`)}
        >
          深修此问题
        </Button>
        {!hasNewLocator && (
          <Button
            size="small"
            disabled={!!repairingKey}
            loading={repairingKey === `${prefix}-audit`}
            onClick={() => reAuditChapter(record, `${prefix}-audit`)}
          >
            重新审计定位
          </Button>
        )}
        <Button
          size="small"
          disabled={!!repairingKey}
          loading={repairingKey === `${prefix}-light`}
          onClick={() => lightFixChapter(record, `${prefix}-light`)}
        >
          整章轻修
        </Button>
        <Button
          size="small"
          type="primary"
          ghost
          disabled={!!repairingKey}
          loading={repairingKey === `${prefix}-complete`}
          onClick={() => completeIssue(record, `${prefix}-complete`)}
        >
          修复完成
        </Button>
        <Link to={`/projects/${projectId}`}>
          <Button size="small">去章节</Button>
        </Link>
      </Space>
    );
  };

  const globalIssueActions = (record: any, prefix: string) => {
    if (record.scope === 'chapter') {
      const repairRecord = {
        chapter_id: record.target?.chapter_id || record.scope_id,
        issue_index: record.target?.issue_index,
        chapter_number: record.scope_name,
        chapter_title: record.scope_name,
        issue: record.title,
        severity: record.severity,
        fix_suggestion: record.description,
        raw_issue: {
          description: record.title,
          severity: record.severity,
          fix_suggestion: record.description,
        },
      };
      return repairActions(repairRecord, prefix);
    }
    const route = record.scope === 'world'
      ? `/projects/${projectId}/world-setting`
      : record.scope === 'outline'
        ? `/projects/${projectId}/outline`
        : record.scope === 'task'
          ? `/projects/${projectId}`
          : `/projects/${projectId}`;
    return (
      <Space size={4} wrap>
        <Link to={route}><Button size="small">打开处理</Button></Link>
        {record.scope === 'volume' && <Link to={`/projects/${projectId}`}><Button size="small" icon={<BranchesOutlined />}>去卷轴</Button></Link>}
        {record.scope === 'arc' && <Link to={`/projects/${projectId}`}><Button size="small" icon={<BranchesOutlined />}>去弧线</Button></Link>}
        {record.scope === 'task' && <Button size="small" onClick={() => loadDashboard()}>刷新任务</Button>}
      </Space>
    );
  };

  if (!projectId) return null;
  if (loading) return <div style={{ padding: 80, textAlign: 'center' }}><Spin size="large" /></div>;

  const summary = data?.summary || {};
  const aggregate = data?.aggregate_scores || {};
  const globalIssues = data?.quality_issues || [];
  const scoreCards = [
    ['综合质量', aggregate.overall, '项目当前总控质量分'],
    ['世界规则', aggregate.world, '世界观硬规则、代价和主题绑定'],
    ['大纲结构', aggregate.outline, '全书长线和分卷结构'],
    ['卷轴结构', aggregate.volume, '卷目标、压力升级和章节承载'],
    ['弧线连续', aggregate.arc, '上承下启和变化台阶'],
    ['章节质量', aggregate.chapter, '正文审计平均质量'],
    ['任务运行', aggregate.task, '失败任务和运行状态'],
  ];
  const topIssues = globalIssues.slice(0, 6);

  return (
    <div style={{ padding: 24, maxWidth: 1280, margin: '0 auto' }}>
      <Space style={{ marginBottom: 16 }}>
        <Link to={`/projects/${projectId}`}><Button icon={<LeftOutlined />}>返回工作台</Button></Link>
        <AuditOutlined style={{ color: '#1677ff', fontSize: 20 }} />
        <Title level={3} style={{ margin: 0 }}>项目质量总控</Title>
      </Space>

      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={8}>
          <Card>
            <Space align="center" size={18}>
              <Progress type="circle" percent={Number(aggregate.overall || 0)} size={112} strokeColor={percentColor(aggregate.overall)} />
              <div>
                <Title level={4} style={{ margin: 0 }}>{data?.project?.title || '当前项目'}</Title>
                <Text type="secondary">{data?.project?.genre || '未分类'} · {data?.project?.core_theme ? `核心主题：${data.project.core_theme}` : '未设置核心主题'}</Text>
                <div style={{ marginTop: 10 }}>
                  <Space wrap>
                    <Tag color={summary.high_issue_count ? 'red' : 'green'}>高优先级 {summary.high_issue_count || 0}</Tag>
                    <Tag color={summary.global_issue_count ? 'orange' : 'green'}>问题 {summary.global_issue_count || 0}</Tag>
                    <Tag color={summary.failed_task_count ? 'red' : 'green'}>失败任务 {summary.failed_task_count || 0}</Tag>
                  </Space>
                </div>
              </div>
            </Space>
          </Card>
        </Col>
        <Col xs={24} lg={16}>
          <Row gutter={[8, 8]}>
            {scoreCards.slice(1).map(([label, value, help]) => (
              <Col xs={12} md={8} key={String(label)}>
                <Card size="small">
                  <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                    <Text type="secondary">{label}</Text>
                    <Text strong>{value ?? 0}</Text>
                  </Space>
                  <Progress percent={Number(value || 0)} size="small" showInfo={false} strokeColor={percentColor(Number(value || 0))} />
                  <Text type="secondary" style={{ fontSize: 11 }}>{help}</Text>
                </Card>
              </Col>
            ))}
          </Row>
        </Col>
      </Row>

      {topIssues.length > 0 && (
        <Card title={<span><ExclamationCircleOutlined /> 优先处理</span>} style={{ marginBottom: 16 }}>
          <div style={{ display: 'grid', gap: 10 }}>
            {topIssues.map((issue: any, idx: number) => (
              <div key={`${issue.scope}-${issue.scope_id}-${idx}`} style={{ display: 'grid', gridTemplateColumns: 'auto 1fr auto', gap: 10, alignItems: 'center', padding: '10px 12px', border: '1px solid #e5ebf3', borderRadius: 8, background: '#fbfcfe' }}>
                <Space size={4} wrap>{renderSeverity(issue.severity)}{renderScope(issue.scope)}</Space>
                <div>
                  <Text strong>{issue.scope_name}</Text>
                  <div style={{ marginTop: 2 }}><Text>{issue.title}</Text></div>
                  {issue.description && <div><Text type="secondary" style={{ fontSize: 12 }}>{issue.description}</Text></div>}
                </div>
                {globalIssueActions(issue, `top-${idx}`)}
              </div>
            ))}
          </div>
        </Card>
      )}

      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={12} md={4}><Card><Statistic title="平均质量" value={summary.average_quality ?? '--'} suffix={summary.average_quality ? '/10' : ''} /></Card></Col>
        <Col xs={12} md={4}><Card><Statistic title="低分章节" value={summary.low_quality_count || 0} /></Card></Col>
        <Col xs={12} md={4}><Card><Statistic title="已写章节" value={summary.written_chapter_count || 0} /></Card></Col>
        <Col xs={12} md={4}><Card><Statistic title="总字数" value={summary.total_words || 0} /></Card></Col>
        <Col xs={12} md={4}><Card><Statistic title="平均字数" value={summary.average_words || 0} /></Card></Col>
        <Col xs={12} md={4}><Card><Statistic title="全局问题" value={summary.global_issue_count || summary.issue_count || 0} /></Card></Col>
      </Row>

      <Card style={{ marginBottom: 16 }}>
        <Tabs
          items={[
            {
              key: 'issues',
              label: <span><ExclamationCircleOutlined /> 问题队列</span>,
              children: (
                <Table
                  rowKey={(r: any, idx) => `${r.scope}-${r.scope_id}-${idx}`}
                  dataSource={globalIssues}
                  pagination={{ pageSize: 10 }}
                  scroll={{ x: 1180 }}
                  columns={[
                    { title: '层级', dataIndex: 'scope', width: 96, filters: Object.entries(SCOPE_LABELS).map(([value, info]) => ({ text: info.label, value })), onFilter: (value, record: any) => record.scope === value, render: renderScope },
                    { title: '严重度', dataIndex: 'severity', width: 100, render: renderSeverity },
                    { title: '对象', dataIndex: 'scope_name', width: 190, ellipsis: true },
                    {
                      title: '问题',
                      dataIndex: 'title',
                      render: (v, record: any) => (
                        <div style={{ whiteSpace: 'normal', overflowWrap: 'anywhere', lineHeight: 1.65 }}>
                          <Text strong>{v}</Text>
                          {record.description && <div><Text type="secondary" style={{ fontSize: 12 }}>{record.description}</Text></div>}
                        </div>
                      ),
                    },
                    { title: '操作', width: 310, fixed: 'right', render: (_v, record: any, idx) => globalIssueActions(record, `global-${idx}`) },
                  ]}
                />
              ),
            },
            {
              key: 'scores',
              label: <span><BarChartOutlined /> 评分合并</span>,
              children: (
                <Table
                  rowKey={(r: any, idx) => `${r.scope}-${r.scope_id}-${idx}`}
                  dataSource={data?.quality_scores || []}
                  pagination={{ pageSize: 10 }}
                  scroll={{ x: 980 }}
                  columns={[
                    { title: '层级', dataIndex: 'scope', width: 96, render: renderScope },
                    { title: '对象', dataIndex: 'scope_name', width: 220, ellipsis: true },
                    { title: '评分类型', dataIndex: 'score_type', width: 140 },
                    { title: '分数', dataIndex: 'score', width: 160, render: (v: number, record: any) => <Space><Tag color={percentColor(v)}>{v}</Tag><Progress percent={Number(v || 0)} size="small" showInfo={false} style={{ width: 90 }} strokeColor={percentColor(v)} /></Space> },
                    { title: '状态', dataIndex: 'status', width: 100, render: (v: string) => <Tag color={v === 'pass' ? 'green' : v === 'warning' ? 'orange' : 'red'}>{v === 'pass' ? '通过' : v === 'warning' ? '提醒' : '需修'}</Tag> },
                    {
                      title: '维度',
                      dataIndex: 'dimensions',
                      render: (dims: any[]) => (
                        <Space wrap>{(dims || []).slice(0, 8).map((d: any) => <Tag key={d.key || d.label}>{d.label || d.key} {d.score}</Tag>)}</Space>
                      ),
                    },
                  ]}
                />
              ),
            },
          ]}
        />
      </Card>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={8}>
          <Card title="维度均分">
            {(data?.dimensions || []).length === 0 ? <Text type="secondary">暂无审稿维度数据</Text> : (
              <div style={{ display: 'grid', gap: 12 }}>
                {data.dimensions.map((d: any) => (
                  <div key={d.name}>
                    <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                      <Text>{dimensionLabel(d.name)}</Text>
                      <Text strong>{d.score}/10</Text>
                    </Space>
                    <Progress percent={Math.round(d.score * 10)} size="small" strokeColor={scoreColor(d.score) === 'red' ? '#ff4d4f' : '#1677ff'} />
                  </div>
                ))}
              </div>
            )}
          </Card>
        </Col>
        <Col xs={24} lg={16}>
          <Card title="章节质量趋势">
            <div style={{ display: 'flex', gap: 8, overflowX: 'auto', alignItems: 'end', minHeight: 160, padding: '8px 0' }}>
              {(data?.trends || []).map((t: any) => {
                const h = Math.max(12, (t.quality_score || 0) * 12);
                return (
                  <div key={t.chapter_number} style={{ width: 34, flexShrink: 0, textAlign: 'center' }}>
                    <div title={`第${t.chapter_number}章：${t.quality_score || '未审'}`} style={{ height: h, borderRadius: 4, background: t.quality_score ? '#1677ff' : '#d9d9d9' }} />
                    <Text type="secondary" style={{ fontSize: 11 }}>{t.chapter_number}</Text>
                  </div>
                );
              })}
            </div>
          </Card>
        </Col>
      </Row>

      <Card title="章节明细" style={{ marginBottom: 16 }}>
        <Table
          rowKey="id"
          dataSource={data?.chapters || []}
          pagination={{ pageSize: 12 }}
          scroll={{ x: 1180 }}
          columns={[
            { title: '章', dataIndex: 'chapter_number', width: 70, render: (v) => `第${v}章` },
            { title: '标题', dataIndex: 'title', ellipsis: true },
            { title: '弧线', dataIndex: 'arc_name', width: 140, render: (v) => v ? <Tag>{v}</Tag> : '-' },
            { title: '状态', dataIndex: 'status', width: 100, render: renderChapterStatus },
            { title: '字数', dataIndex: 'word_count', width: 100 },
            { title: '质量', dataIndex: 'quality_score', width: 110, render: (v) => v ? <Tag color={scoreColor(v)}>{v}/10</Tag> : <Tag>未审</Tag> },
            {
              title: '主要问题',
              dataIndex: 'quality_review',
              ellipsis: true,
              render: (v, record: any) => {
                const issue = (v?.issues || [])[0];
                const repairRecord = {
                  chapter_id: record.id,
                  issue_index: 0,
                  chapter_number: record.chapter_number,
                  chapter_title: record.title,
                  issue: issueText(issue),
                  severity: typeof issue === 'object' ? issue.severity : '',
                  target_text: typeof issue === 'object' ? issue.target_text : '',
                  fix_mode: typeof issue === 'object' ? issue.fix_mode : '',
                  fix_suggestion: typeof issue === 'object' ? issue.fix_suggestion : '',
                  raw_issue: issue,
                };
                return (
                  <div>
                    <Text style={{ fontSize: 12 }}>{issueText(issue)}</Text>
                    {typeof issue === 'object' && issue?.target_text && (
                      <div><Text type="secondary" style={{ fontSize: 11 }}>定位：{issue.target_text}</Text></div>
                    )}
                  </div>
                );
              },
            },
            {
              title: '修复',
              width: 360,
              fixed: 'right',
              render: (_v, record: any) => {
                const issue = (record.quality_review?.issues || [])[0];
                if (!issue) return <Text type="secondary">暂无问题</Text>;
                const repairRecord = {
                  chapter_id: record.id,
                  issue_index: 0,
                  chapter_number: record.chapter_number,
                  chapter_title: record.title,
                  issue: issueText(issue),
                  severity: typeof issue === 'object' ? issue.severity : '',
                  target_text: typeof issue === 'object' ? issue.target_text : '',
                  fix_mode: typeof issue === 'object' ? issue.fix_mode : '',
                  fix_suggestion: typeof issue === 'object' ? issue.fix_suggestion : '',
                  raw_issue: issue,
                };
                return repairActions(repairRecord, `chapter-${record.id}`);
              },
            },
          ]}
        />
      </Card>

      <Card title="问题清单">
        <Table
          rowKey={(r: any) => `${r.chapter_id}-${r.issue_index}-${r.issue}`}
          dataSource={data?.issues || []}
          pagination={{ pageSize: 10 }}
          scroll={{ x: 1180 }}
          columns={[
            { title: '章节', dataIndex: 'chapter_number', width: 90, render: (v) => `第${v}章` },
            { title: '标题', dataIndex: 'chapter_title', width: 180, ellipsis: true },
            { title: '严重度', dataIndex: 'severity', width: 100, render: renderSeverity },
            {
              title: '问题',
              dataIndex: 'issue',
              width: 520,
              render: (v, record: any) => (
                <div style={{ whiteSpace: 'normal', overflowWrap: 'anywhere', lineHeight: 1.65 }}>
                  <Text style={{ fontSize: 12 }}>{v}</Text>
                  {record.target_text && (
                    <div style={{ marginTop: 4 }}><Text type="secondary" style={{ fontSize: 11 }}>定位：{record.target_text}</Text></div>
                  )}
                  {record.fix_suggestion && (
                    <div style={{ marginTop: 4 }}><Text type="secondary" style={{ fontSize: 11 }}>建议：{record.fix_suggestion}</Text></div>
                  )}
                </div>
              ),
            },
            { title: '修复', width: 290, render: (_v, record: any) => repairActions(record, `issue-${record.chapter_id}-${record.issue}`) },
          ]}
        />
      </Card>
    </div>
  );
}
