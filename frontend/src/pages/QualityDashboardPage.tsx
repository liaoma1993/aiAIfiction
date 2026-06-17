import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Alert, Button, Card, Col, Empty, message, Modal, Progress, Row, Space, Spin, Table, Tabs, Tag, Typography } from 'antd';
import { AuditOutlined, BarChartOutlined, BranchesOutlined, DatabaseOutlined, ExclamationCircleOutlined, LeftOutlined, ReloadOutlined, ToolOutlined } from '@ant-design/icons';
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
  opening_continuity: '开场承接',
  chapter_function: '章节功能',
  indispensability: '不可替代性',
  character_voice: '角色声音',
  information_reveal: '信息揭露节奏',
  state_memory: '状态记忆',
  opening: '开场质量',
  state_delta: '状态增量',
  state_delta_density: '状态增量密度',
  arc_continuity: '弧线连续性',
  faction_entry_slope: '组织入场坡度',
  protagonist_state_memory: '主角状态记忆',
  hook_strength: '钩子强度',
  info_reveal_control: '信息揭露控制',
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

const dimensionLabel = (name: string) => QUALITY_DIMENSION_LABELS[name] || name.replace(/_/g, ' ');

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

const issuePayloadText = (issue: any) => {
  if (!issue) return '';
  if (typeof issue === 'string') return issue;
  try {
    return JSON.stringify(issue);
  } catch {
    return issueText(issue);
  }
};

const chapterIssueCount = (dashboard: any, chapterId?: string) => {
  if (!dashboard || !chapterId) return 0;
  const chapter = (dashboard.chapters || []).find((item: any) => String(item.id) === String(chapterId));
  return Array.isArray(chapter?.quality_review?.issues) ? chapter.quality_review.issues.length : 0;
};

const severityWeight = (severity?: string) => {
  const value = String(severity || '').toLowerCase();
  if (value === 'critical' || value === '致命') return 4;
  if (value === 'high' || value === '严重') return 3;
  if (value === 'medium' || value === '中等') return 2;
  if (value === 'low' || value === '轻微') return 1;
  return 0;
};

const normalizeIssueRecord = (issue: any, chapter: any, issueIndex: number) => ({
  chapter_id: chapter.id,
  issue_index: issueIndex,
  chapter_number: chapter.chapter_number,
  chapter_title: chapter.title,
  issue: issueText(issue),
  severity: typeof issue === 'object' ? issue.severity : '',
  target_text: typeof issue === 'object' ? issue.target_text : '',
  fix_mode: typeof issue === 'object' ? issue.fix_mode : '',
  fix_suggestion: typeof issue === 'object' ? issue.fix_suggestion : '',
  raw_issue: issue,
});

const chapterIssueGroupsFromDashboard = (dashboard: any) => {
  const groups = new Map<string, any>();
  const ensure = (base: any) => {
    const key = String(base.chapter_id || '');
    if (!key) return null;
    if (!groups.has(key)) {
      groups.set(key, {
        chapter_id: base.chapter_id,
        chapter_number: base.chapter_number,
        chapter_title: base.chapter_title,
        quality_score: base.quality_score,
        issues: [],
      });
    }
    const group = groups.get(key);
    if (base.quality_score !== undefined) group.quality_score = base.quality_score;
    return group;
  };

  (dashboard?.chapters || []).forEach((chapter: any) => {
    const issues = chapter?.quality_review?.issues || [];
    if (!Array.isArray(issues) || issues.length === 0) return;
    const group = ensure({
      chapter_id: chapter.id,
      chapter_number: chapter.chapter_number,
      chapter_title: chapter.title,
      quality_score: chapter.quality_score,
    });
    issues.forEach((issue: any, issueIndex: number) => group?.issues.push(normalizeIssueRecord(issue, chapter, issueIndex)));
  });

  (dashboard?.issues || []).forEach((issue: any) => {
    const group = ensure(issue);
    if (!group) return;
    const duplicated = group.issues.some((item: any) => (
      Number(item.issue_index) === Number(issue.issue_index)
      && String(item.issue || '') === String(issue.issue || '')
    ));
    if (!duplicated) {
      group.issues.push({
        chapter_id: issue.chapter_id,
        issue_index: issue.issue_index,
        chapter_number: issue.chapter_number,
        chapter_title: issue.chapter_title,
        issue: issue.issue,
        severity: issue.severity,
        target_text: issue.target_text,
        fix_mode: issue.fix_mode,
        fix_suggestion: issue.fix_suggestion,
        raw_issue: issue.raw_issue || issue,
      });
    }
  });

  return Array.from(groups.values())
    .map((group) => ({
      ...group,
      issue_count: group.issues.length,
      max_severity: group.issues.reduce((max: string, item: any) => (
        severityWeight(item.severity) > severityWeight(max) ? item.severity : max
      ), ''),
      summary: group.issues.slice(0, 3).map((item: any) => item.issue).join('；'),
    }))
    .sort((a, b) => severityWeight(b.max_severity) - severityWeight(a.max_severity) || b.issue_count - a.issue_count || Number(a.chapter_number || 0) - Number(b.chapter_number || 0));
};

const renderStringList = (items: any[]) => (
  <ul style={{ margin: 0, paddingLeft: 18 }}>
    {(items || []).map((item, idx) => <li key={idx}>{String(item)}</li>)}
  </ul>
);

const SystemHealthPanel = ({ data, loading, onRefresh }: { data: any; loading: boolean; onRefresh: () => void }) => {
  if (!data && loading) return <div style={{ padding: 48, textAlign: 'center' }}><Spin /></div>;
  if (!data) return <Empty description="暂无系统诊断数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  const scores = data.scores || {};
  const scoreItems = [
    ['弧线连续', scores.arc_continuity],
    ['蓝图质量', scores.chapter_blueprint],
    ['钩子密度', scores.hook_density],
    ['事件密度', scores.event_density],
    ['伏笔追踪', scores.foreshadowing_tracking],
    ['世界规则', scores.world_rules],
  ];
  const worldAudit = data.world_rule_audit;
  return (
    <Spin spinning={loading}>
      <div style={{ display: 'grid', gap: 16 }}>
        <Card size="small">
          <Space align="center" size={18} style={{ width: '100%', justifyContent: 'space-between' }}>
            <Space align="center" size={18}>
              <Progress type="circle" percent={Number(data.overall_score || 0)} size={92} strokeColor={percentColor(data.overall_score)} />
              <div>
                <Title level={4} style={{ margin: 0 }}>系统健康度</Title>
                <Text type="secondary">Prompt {data.prompt_version || '-'}</Text>
              </div>
            </Space>
            <Button icon={<ReloadOutlined />} loading={loading} onClick={onRefresh}>刷新诊断</Button>
          </Space>
        </Card>

        <Row gutter={[8, 8]}>
          {scoreItems.map(([label, value]) => (
            <Col xs={24} sm={12} md={8} key={label}>
              <Card size="small">
                <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                  <Text type="secondary">{label}</Text>
                  <Text strong>{value ?? 0}</Text>
                </Space>
                <Progress percent={Number(value || 0)} size="small" strokeColor={percentColor(Number(value || 0))} />
              </Card>
            </Col>
          ))}
        </Row>

        {Array.isArray(data.fatigue_warnings) && data.fatigue_warnings.length > 0 && (
          <Alert type="warning" showIcon message="长篇疲劳警告" description={renderStringList(data.fatigue_warnings)} />
        )}

        {worldAudit && (
          <Card size="small" title="世界规则闸门">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                <Progress percent={Number(worldAudit.score || 0)} size="small" status={worldAudit.passed ? 'success' : 'exception'} style={{ flex: 1 }} />
                <Tag color={worldAudit.passed ? 'green' : 'orange'}>{worldAudit.passed ? '通过' : '需补强'}</Tag>
              </Space>
              {Array.isArray(worldAudit.risks) && worldAudit.risks.length > 0 && (
                <Space wrap>
                  {worldAudit.risks.slice(0, 8).map((risk: string, idx: number) => <Tag key={idx} color="orange">{risk}</Tag>)}
                </Space>
              )}
            </Space>
          </Card>
        )}

        <Row gutter={[12, 12]}>
          <Col xs={24} lg={12}>
            <Card size="small" title="弧线问题">
              {Array.isArray(data.arc_issues) && data.arc_issues.length > 0 ? (
                <div style={{ display: 'grid', gap: 8 }}>
                  {data.arc_issues.slice(0, 12).map((item: any, idx: number) => (
                    <div key={idx} style={{ padding: 10, border: '1px solid #eef2f7', borderRadius: 8, background: '#f8fafc' }}>
                      <Text strong>{item.volume || item.name || `弧线 ${idx + 1}`}</Text>
                      <div><Text type="secondary">{item.quality_gate?.related_issues?.[0]?.issue || (item.needs_repair ? '需要修复承接或台阶' : '连续性风险')}</Text></div>
                    </div>
                  ))}
                </div>
              ) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无弧线问题" />}
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card size="small" title="章节蓝图问题">
              {Array.isArray(data.blueprint_issues) && data.blueprint_issues.length > 0 ? (
                <div style={{ display: 'grid', gap: 8 }}>
                  {data.blueprint_issues.slice(0, 12).map((item: any) => (
                    <div key={item.chapter_number} style={{ padding: 10, border: '1px solid #eef2f7', borderRadius: 8, background: '#f8fafc' }}>
                      <Text strong>第{item.chapter_number}章 {item.title || ''}</Text>
                      <div><Text type="secondary">{(item.gate?.issues || []).join('；') || '蓝图质量未通过'}</Text></div>
                    </div>
                  ))}
                </div>
              ) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无蓝图问题" />}
            </Card>
          </Col>
        </Row>

        <Card size="small" title="伏笔状态">
          {Array.isArray(data.foreshadowing) && data.foreshadowing.length > 0 ? (
            <Space wrap>
              {data.foreshadowing.slice(0, 32).map((f: any, idx: number) => (
                <Tag key={`${f.name}-${idx}`} color={['已回收', '完成', 'done'].includes(f.status) ? 'green' : 'orange'}>
                  {f.name || '未命名'} · {f.status || '未定'}
                </Tag>
              ))}
            </Space>
          ) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无伏笔状态" />}
        </Card>
      </div>
    </Spin>
  );
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
  const [systemHealth, setSystemHealth] = useState<any>(null);
  const [systemHealthLoading, setSystemHealthLoading] = useState(false);
  const [chapterIssueDetail, setChapterIssueDetail] = useState<any>(null);

  // 修复并发控制：全局修复（world/outline/task）禁用所有按钮；章节级修复只禁用同一章节
  // key 形如：global-xxx / top-xxx（全局）、chapter-<id> / chapter-group-<id> / <prefix>-sentence 等
  const repairingScope = (() => {
    if (!repairingKey) return { any: false, isGlobal: false, chapterId: null as string | null };
    // 全局问题（world/outline/task 修复）会整表重构，必须禁用全部
    if (repairingKey.startsWith('global-') || repairingKey.startsWith('top-')) {
      return { any: true, isGlobal: true, chapterId: null };
    }
    // 章节级：从 key 提取 chapter_id（形如 chapter-<id>、chapter-group-<id>、modal-*-<id>）
    const m = repairingKey.match(/(?:^chapter-group-|^chapter-|^modal-[a-z]+-)([a-f0-9-]+)/i);
    return { any: true, isGlobal: false, chapterId: m ? m[1] : null };
  })();
  // 判断某章节的按钮是否应被禁用：全局修复时全禁；章节修复时只禁同章
  const isChapterDisabled = (chapterId: string) => {
    if (!repairingScope.any) return false;
    if (repairingScope.isGlobal) return true;
    // 章节修复：无法解析 chapterId 时保守禁用，能解析时只禁同章
    return !repairingScope.chapterId ? true : String(repairingScope.chapterId) === String(chapterId);
  };

  const loadDashboard = async (silent = false) => {
    if (!projectId) return null;
    if (!silent) setLoading(true);
    try {
      const dashboard = await storyApi.qualityDashboard(projectId);
      setData(dashboard);
      return dashboard;
    } finally {
      setLoading(false);
    }
  };

  const loadSystemHealth = (silent = false) => {
    if (!projectId) return;
    if (!silent) setSystemHealthLoading(true);
    api.get(`/projects/${projectId}/wizard/project-health`)
      .then((res) => setSystemHealth(res.data))
      .catch((e) => message.error(e?.response?.data?.detail || e.message || '加载系统诊断失败'))
      .finally(() => setSystemHealthLoading(false));
  };

  useEffect(() => {
    loadDashboard();
    loadSystemHealth();
  }, [projectId]);

  useEffect(() => {
    if (!projectId) return;
    const refreshIfSameProject = (payload: any) => {
      if (payload?.projectId === projectId) {
        loadDashboard(true);
        loadSystemHealth(true);
      }
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
        message.warning('当前问题没有可定位原文，请先重新审稿找问题，或直接做整章复审修复');
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
        controls: {
          readability_mode: 'easy',
          punctuation_style: 'standard',
          quality_resolved_issue: {
            issue_index: record.issue_index,
            issue: record.issue || issueText(issue),
            raw_issue: issue,
          },
        },
        apply: true,
        resolved_issue_index: typeof record.issue_index === 'number' ? record.issue_index : undefined,
        resolved_issue: issuePayloadText(issue),
      });
      message.loading({
        content: scope === 'sentence' ? 'AI 正在只修原句…' : scope === 'context' ? 'AI 正在深修此问题…' : 'AI 正在修这一段…',
        key: 'quality-repair',
        duration: 0,
      });
      const result = await pollTask(res.data.task_id);
      const issueCount = Array.isArray(result?.quality_review?.issues)
        ? result.quality_review.issues.length
        : chapterIssueCount(await loadDashboard(true), record.chapter_id);
      message.success({
        content: issueCount > 0 ? `修复完成，复审仍发现 ${issueCount} 个问题，已刷新问题清单` : '修复完成，复审通过，当前章节问题已清空',
        key: 'quality-repair',
      });
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
        controls: {
          readability_mode: 'easy',
          punctuation_style: 'standard',
          quality_resolved_issue: {
            issue_index: record.issue_index,
            issue: record.issue || issueText(issue),
            raw_issue: issue,
          },
        },
        apply: true,
        resolved_issue_index: typeof record.issue_index === 'number' ? record.issue_index : undefined,
        resolved_issue: issuePayloadText(issue),
      });
      message.loading({ content: 'AI 正在整章轻修…', key: 'quality-light-fix', duration: 0 });
      const result = await pollTask(res.data.task_id);
      const issueCount = Array.isArray(result?.quality_review?.issues)
        ? result.quality_review.issues.length
        : chapterIssueCount(await loadDashboard(true), record.chapter_id);
      message.success({
        content: issueCount > 0 ? `整章轻修完成，复审仍发现 ${issueCount} 个问题，已刷新问题清单` : '整章轻修完成，复审通过，当前章节问题已清空',
        key: 'quality-light-fix',
      });
      notifyQualityUpdated(projectId, record.chapter_id);
    } catch (e: any) {
      message.error({ content: e?.response?.data?.detail || e.message || '整章轻修失败', key: 'quality-light-fix' });
    } finally {
      setRepairingKey(null);
    }
  };

  const lightFixChapterIssueGroup = async (group: any, key: string) => {
    if (!projectId || !group?.chapter_id || !Array.isArray(group.issues) || group.issues.length === 0) return;
    setRepairingKey(key);
    try {
      const chapter = await chapterApi.get(projectId, group.chapter_id);
      const originalChars = String(chapter?.content || '').length || Number(chapter?.word_count || 0);
      const minChars = originalChars ? Math.floor(originalChars * 0.9) : 0;
      const issueList = group.issues.map((item: any, idx: number) => ({
        index: typeof item.issue_index === 'number' ? item.issue_index : idx,
        severity: item.severity || '',
        problem: item.issue || issueText(item.raw_issue),
        target_text: item.target_text || item.raw_issue?.target_text || '',
        fix_suggestion: item.fix_suggestion || item.raw_issue?.fix_suggestion || '',
      }));
      const res = await api.post(`/projects/${projectId}/wizard/revise-chapter/${group.chapter_id}`, {
        mode: 'quality_group_fix',
        instruction: [
          `根据质量仪表盘汇总的问题，对第${group.chapter_number || ''}章《${group.chapter_title || ''}》做一次整章连续性修复。`,
          '必须把这些问题当成同一章的同一组问题整体处理，不要只修第一条。',
          '优先修复开场承接、上一章钩子回应、人物已知信息、章末钩子与状态快照冲突。',
          '保留本章核心剧情、人物关系、关键线索和章末追读钩子；不得压缩成梗概，不得删除有效场景、对话、动作、阻力和余波。',
          originalChars ? `原文约 ${originalChars} 字，修复后正文不得少于 ${minChars} 字；如果需要修复连续性，应通过补足过渡、反应、物件承接和场景实写完成，不允许缩水。` : '',
          '输出必须是完整章节正文，不要只输出修改片段，不要输出修改说明代替正文。',
          `本章问题清单：${JSON.stringify(issueList)}`,
        ].filter(Boolean).join('\n'),
        selection: '',
        controls: {
          readability_mode: 'easy',
          punctuation_style: 'standard',
          min_output_chars: minChars,
          quality_resolved_issue_group: {
            chapter_id: group.chapter_id,
            issue_count: group.issues.length,
            issues: issueList,
          },
        },
        apply: true,
        resolved_issue: JSON.stringify(issueList),
      });
      message.loading({ content: `AI 正在整章处理 ${group.issues.length} 个问题…`, key: 'quality-group-fix', duration: 0 });
      const result = await pollTask(res.data.task_id);
      const issueCount = Array.isArray(result?.quality_review?.issues)
        ? result.quality_review.issues.length
        : chapterIssueCount(await loadDashboard(true), group.chapter_id);
      message.success({
        content: issueCount > 0 ? `本章整组修复完成，复审仍发现 ${issueCount} 个问题，已刷新问题清单` : '本章整组修复完成，复审通过，当前章节问题已清空',
        key: 'quality-group-fix',
      });
      notifyQualityUpdated(projectId, group.chapter_id);
    } catch (e: any) {
      message.error({ content: e?.response?.data?.detail || e.message || '本章整组修复失败', key: 'quality-group-fix' });
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
    const isLowScoreWithoutLocator = issue?.issue_type === 'low_score_without_locator' || String(issue?.description || record?.issue || '').includes('模型未返回具体问题');
    const disabledHere = isChapterDisabled(String(record.chapter_id));
    return (
      <Space size={4} wrap>
        {!isLowScoreWithoutLocator && (
          <>
            <Button
              size="small"
              icon={<ToolOutlined />}
              disabled={disabledHere || !hasNewLocator}
              loading={repairingKey === `${prefix}-sentence`}
              onClick={() => repairIssue(record, 'sentence', `${prefix}-sentence`)}
            >
              只修原句
            </Button>
            <Button
              size="small"
              disabled={disabledHere || !hasNewLocator}
              loading={repairingKey === `${prefix}-paragraph`}
              onClick={() => repairIssue(record, preferredScope === 'context' ? 'context' : 'paragraph', `${prefix}-paragraph`)}
            >
              {preferredScope === 'context' ? '修局部' : '修这一段'}
            </Button>
            <Button
              size="small"
              disabled={disabledHere || !hasNewLocator}
              loading={repairingKey === `${prefix}-context`}
              onClick={() => repairIssue(record, 'context', `${prefix}-context`)}
            >
              深修此问题
            </Button>
          </>
        )}
        {!hasNewLocator && (
          <Button
            size="small"
            type={isLowScoreWithoutLocator ? 'primary' : 'default'}
            disabled={disabledHere}
            loading={repairingKey === `${prefix}-audit`}
            onClick={() => reAuditChapter(record, `${prefix}-audit`)}
          >
            {isLowScoreWithoutLocator ? '重新审稿找问题' : '重新审计定位'}
          </Button>
        )}
        <Button
          size="small"
          type={isLowScoreWithoutLocator ? 'primary' : 'default'}
          ghost={isLowScoreWithoutLocator}
          disabled={disabledHere}
          loading={repairingKey === `${prefix}-light`}
          onClick={() => lightFixChapter(record, `${prefix}-light`)}
        >
          {isLowScoreWithoutLocator ? '整章复审修复' : '整章轻修'}
        </Button>
        <Button
          size="small"
          type="primary"
          ghost
          disabled={disabledHere}
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
  const chapterIssueGroups = chapterIssueGroupsFromDashboard(data);
  const scoreCards = [
    ['世界规则', aggregate.world],
    ['大纲结构', aggregate.outline],
    ['卷轴结构', aggregate.volume],
    ['弧线连续', aggregate.arc],
    ['章节质量', aggregate.chapter],
    ['任务运行', aggregate.task],
  ];
  const topIssues = globalIssues.slice(0, 6);

  // 紧凑统计指标：合并原"统计数字行"，横排到概览区
  const stats = [
    { label: '平均质量', value: summary.average_quality ? `${summary.average_quality}` : '--', suffix: summary.average_quality ? '/10' : '' },
    { label: '低分章节', value: summary.low_quality_count || 0 },
    { label: '已写章节', value: summary.written_chapter_count || 0 },
    { label: '总字数', value: summary.total_words || 0 },
    { label: '平均字数', value: summary.average_words || 0 },
    { label: '全局问题', value: summary.global_issue_count || summary.issue_count || 0 },
  ];

  return (
    <div style={{ padding: 24, maxWidth: 1440, margin: '0 auto' }}>
      <Space style={{ marginBottom: 12 }}>
        <Link to={`/projects/${projectId}`}><Button icon={<LeftOutlined />}>返回工作台</Button></Link>
        <AuditOutlined style={{ color: '#1677ff', fontSize: 20 }} />
        <Title level={3} style={{ margin: 0 }}>项目质量总控</Title>
      </Space>

      {/* 顶部紧凑概览：圆环 + 项目信息 + 关键计数 + 6 项子评分 + 统计数字，全部压进一块 */}
      <Card style={{ marginBottom: 12 }}>
        <Row gutter={[16, 12]} align="middle">
          <Col xs={24} md={6} lg={5}>
            <Space align="center" size={14}>
              <Progress type="circle" percent={Number(aggregate.overall || 0)} size={88} strokeColor={percentColor(aggregate.overall)} />
              <div>
                <Text strong style={{ fontSize: 15 }}>{data?.project?.title || '当前项目'}</Text>
                <div><Text type="secondary" style={{ fontSize: 12 }}>{data?.project?.genre || '未分类'}{data?.project?.core_theme ? ` · ${data.project.core_theme}` : ''}</Text></div>
              </div>
            </Space>
          </Col>
          <Col xs={24} md={18} lg={19}>
            <Row gutter={[8, 8]}>
              <Col xs={24}>
                <Space wrap size={6}>
                  <Tag color={summary.high_issue_count ? 'red' : 'green'}>高优先级 {summary.high_issue_count || 0}</Tag>
                  <Tag color={summary.global_issue_count ? 'orange' : 'green'}>全局问题 {summary.global_issue_count || 0}</Tag>
                  <Tag color={summary.failed_task_count ? 'red' : 'green'}>失败任务 {summary.failed_task_count || 0}</Tag>
                  {stats.map((s) => (
                    <Tag key={s.label} style={{ marginInlineEnd: 0 }}>{s.label} <Text strong>{s.value}{s.suffix || ''}</Text></Tag>
                  ))}
                </Space>
              </Col>
              {scoreCards.map(([label, value]) => (
                <Col xs={12} md={4} key={String(label)}>
                  <div>
                    <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>{label}</Text>
                      <Text strong style={{ fontSize: 12 }}>{value ?? 0}</Text>
                    </Space>
                    <Progress percent={Number(value || 0)} size="small" showInfo={false} strokeColor={percentColor(Number(value || 0))} />
                  </div>
                </Col>
              ))}
            </Row>
          </Col>
        </Row>
      </Card>

      {topIssues.length > 0 && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 12 }}
          message={<Text strong>优先处理 · {topIssues.length} 项</Text>}
          description={
            <div style={{ display: 'grid', gap: 6 }}>
              {topIssues.map((issue: any, idx: number) => (
                <div key={`${issue.scope}-${issue.scope_id}-${idx}`} style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                  <Space size={4}>{renderSeverity(issue.severity)}{renderScope(issue.scope)}</Space>
                  <Text strong style={{ fontSize: 13 }}>{issue.scope_name}</Text>
                  <Text style={{ fontSize: 12 }}>{issue.title}</Text>
                  {globalIssueActions(issue, `top-${idx}`)}
                </div>
              ))}
            </div>
          }
        />
      )}

      {/* 双栏主体：左章节明细 + 右 Tab 区（问题/评分/诊断/趋势/维度） */}
      <Row gutter={[12, 12]}>
        <Col xs={24} lg={15}>
          <Card title="章节明细" size="small" style={{ marginBottom: 12 }}>
            <Table
              rowKey="id"
              dataSource={data?.chapters || []}
              pagination={{ pageSize: 10 }}
              scroll={{ x: 1180 }}
              columns={[
                { title: '章', dataIndex: 'chapter_number', width: 64, render: (v) => `第${v}章` },
                { title: '标题', dataIndex: 'title', ellipsis: true },
                { title: '状态', dataIndex: 'status', width: 86, render: renderChapterStatus },
                { title: '字数', dataIndex: 'word_count', width: 80 },
                { title: '质量', dataIndex: 'quality_score', width: 92, render: (v) => v ? <Tag color={scoreColor(v)}>{v}/10</Tag> : <Tag>未审</Tag> },
                {
                  title: '主要问题',
                  dataIndex: 'quality_review',
                  ellipsis: true,
                  render: (v, record: any) => {
                    const issues = Array.isArray(v?.issues) ? v.issues : [];
                    const issue = issues[0];
                    if (!issue) return <Text type="secondary">暂无</Text>;
                    return (
                      <div>
                        <Space size={4} wrap style={{ marginBottom: 2 }}>
                          <Tag color={issues.length > 1 ? 'red' : 'orange'}>{issues.length} 条</Tag>
                          {typeof issue === 'object' && issue?.severity && renderSeverity(issue.severity)}
                        </Space>
                        <div><Text style={{ fontSize: 12 }}>{issueText(issue)}</Text></div>
                      </div>
                    );
                  },
                },
                {
                  title: '操作',
                  width: 320,
                  fixed: 'right',
                  render: (_v, record: any) => {
                    const issues = Array.isArray(record.quality_review?.issues) ? record.quality_review.issues : [];
                    const issue = issues[0];
                    if (!issue) return <Text type="secondary">暂无</Text>;
                    const group = chapterIssueGroups.find((item: any) => String(item.chapter_id) === String(record.id)) || {
                      chapter_id: record.id,
                      chapter_number: record.chapter_number,
                      chapter_title: record.title,
                      quality_score: record.quality_score,
                      issues: issues.map((item: any, idx: number) => normalizeIssueRecord(item, record, idx)),
                    };
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
                      <Space size={4} wrap>
                        <Button size="small" icon={<ExclamationCircleOutlined />} disabled={isChapterDisabled(String(record.id))} onClick={() => setChapterIssueDetail(group)}>查看</Button>
                        {group.issues.length > 1 && (
                          <Button size="small" type="primary" icon={<ToolOutlined />} disabled={isChapterDisabled(String(record.id))} loading={repairingKey === `chapter-group-${record.id}`} onClick={() => lightFixChapterIssueGroup(group, `chapter-group-${record.id}`)}>修复全部</Button>
                        )}
                        {repairActions(repairRecord, `chapter-${record.id}`)}
                      </Space>
                    );
                  },
                },
              ]}
            />
          </Card>
        </Col>

        <Col xs={24} lg={9}>
          <Card size="small" style={{ position: 'sticky', top: 12 }}>
            <Tabs
              defaultActiveKey="issues"
              size="small"
              items={[
                {
                  key: 'issues',
                  label: <span><ExclamationCircleOutlined /> 问题 ({globalIssues.length})</span>,
                  children: (
                    <Table
                      size="small"
                      rowKey={(r: any, idx) => `${r.scope}-${r.scope_id}-${idx}`}
                      dataSource={globalIssues}
                      pagination={{ pageSize: 6 }}
                      scroll={{ x: 560 }}
                      columns={[
                        { title: '层级', dataIndex: 'scope', width: 72, render: renderScope },
                        { title: '严重度', dataIndex: 'severity', width: 76, render: renderSeverity },
                        { title: '问题', dataIndex: 'title', render: (v, record: any) => (
                          <div style={{ whiteSpace: 'normal', overflowWrap: 'anywhere', lineHeight: 1.5 }}>
                            <Text strong style={{ fontSize: 12 }}>{record.scope_name}</Text>
                            <div><Text style={{ fontSize: 12 }}>{v}</Text></div>
                            <div style={{ marginTop: 4 }}>{globalIssueActions(record, `global-${record.scope_id}`)}</div>
                          </div>
                        ) },
                      ]}
                    />
                  ),
                },
                {
                  key: 'scores',
                  label: <span><BarChartOutlined /> 评分合并</span>,
                  children: (
                    <Table
                      size="small"
                      rowKey={(r: any, idx) => `${r.scope}-${r.scope_id}-${idx}`}
                      dataSource={data?.quality_scores || []}
                      pagination={{ pageSize: 6 }}
                      scroll={{ x: 480 }}
                      columns={[
                        { title: '对象', dataIndex: 'scope_name', width: 140, ellipsis: true, render: (v, r: any) => <span>{renderScope(r.scope)} {v}</span> },
                        { title: '分', dataIndex: 'score', width: 70, render: (v: number) => <Tag color={percentColor(v)}>{v}</Tag> },
                        { title: '维度', dataIndex: 'dimensions', render: (dims: any[]) => (
                          <Space wrap size={4}>{(dims || []).slice(0, 5).map((d: any) => <Tag key={d.key || d.label} style={{ marginInlineEnd: 0 }}>{d.label || d.key} {d.score}</Tag>)}</Space>
                        ) },
                      ]}
                    />
                  ),
                },
                {
                  key: 'dimensions',
                  label: '维度/趋势',
                  children: (
                    <div style={{ display: 'grid', gap: 10, maxHeight: 'calc(100vh - 220px)', overflowY: 'auto', paddingRight: 4 }}>
                      <div>
                        <Text type="secondary" style={{ fontSize: 12 }}>维度均分</Text>
                        {(data?.dimensions || []).length === 0 ? <Text type="secondary"> 暂无</Text> : (
                          // 两列网格，省一半高度
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 12px', marginTop: 6 }}>
                            {data.dimensions.slice(0, 16).map((d: any) => (
                              <div key={d.name}>
                                <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                                  <Text style={{ fontSize: 11 }} ellipsis>{dimensionLabel(d.name)}</Text>
                                  <Text strong style={{ fontSize: 11 }}>{d.score}</Text>
                                </Space>
                                <Progress percent={Math.round(d.score * 10)} size="small" strokeColor={scoreColor(d.score) === 'red' ? '#ff4d4f' : '#1677ff'} />
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                      <div>
                        <Text type="secondary" style={{ fontSize: 12 }}>章节质量趋势</Text>
                        <div style={{ display: 'flex', gap: 3, overflowX: 'auto', alignItems: 'end', minHeight: 90, maxHeight: 110, padding: '6px 0' }}>
                          {(data?.trends || []).map((t: any) => {
                            const h = Math.max(8, (t.quality_score || 0) * 9);
                            return (
                              <div key={t.chapter_number} style={{ width: 20, flexShrink: 0, textAlign: 'center' }}>
                                <div title={`第${t.chapter_number}章：${t.quality_score || '未审'}`} style={{ height: h, borderRadius: 2, background: t.quality_score ? '#1677ff' : '#d9d9d9' }} />
                                <Text type="secondary" style={{ fontSize: 9 }}>{t.chapter_number}</Text>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    </div>
                  ),
                },
                {
                  key: 'system',
                  label: <span><DatabaseOutlined /> 诊断</span>,
                  children: <SystemHealthPanel data={systemHealth} loading={systemHealthLoading} onRefresh={() => loadSystemHealth()} />,
                },
              ]}
            />
          </Card>
        </Col>
      </Row>

      <Modal
        title={chapterIssueDetail ? `第${chapterIssueDetail.chapter_number}章《${chapterIssueDetail.chapter_title || ''}》问题清单` : '章节问题清单'}
        open={!!chapterIssueDetail}
        onCancel={() => setChapterIssueDetail(null)}
        footer={null}
        width={860}
      >
        {chapterIssueDetail && (
          <div style={{ display: 'grid', gap: 12 }}>
            <Space wrap>
              <Tag color={scoreColor(chapterIssueDetail.quality_score)}>质量 {chapterIssueDetail.quality_score ?? '-'} / 10</Tag>
              <Tag color={chapterIssueDetail.issue_count > 1 ? 'red' : 'orange'}>{chapterIssueDetail.issue_count} 条问题</Tag>
              {chapterIssueDetail.max_severity && renderSeverity(chapterIssueDetail.max_severity)}
            </Space>
            <Alert
              type="info"
              showIcon
              message="这里展示的是本章当前审稿问题清单"
              description="连续性断裂、上一章钩子未承接、人物信息倒退、章末状态冲突这类问题建议点击“修复本章全部问题”，让模型一次性按整章处理。"
            />
            <div style={{ display: 'grid', gap: 10, maxHeight: '48vh', overflow: 'auto' }}>
              {(chapterIssueDetail.issues || []).map((item: any, idx: number) => (
                <div key={idx} style={{ padding: 12, border: '1px solid #e5ebf3', borderRadius: 8, background: '#fbfcfe' }}>
                  <Space size={4} wrap style={{ marginBottom: 6 }}>
                    <Tag>{idx + 1}</Tag>
                    {renderSeverity(item.severity)}
                    {typeof item.issue_index === 'number' && <Tag>问题 {item.issue_index + 1}</Tag>}
                  </Space>
                  <div style={{ whiteSpace: 'normal', overflowWrap: 'anywhere', lineHeight: 1.65 }}>
                    <Text>{item.issue}</Text>
                    {item.target_text && <div style={{ marginTop: 6 }}><Text type="secondary" style={{ fontSize: 12 }}>定位：{item.target_text}</Text></div>}
                    {item.fix_suggestion && <div style={{ marginTop: 6 }}><Text type="secondary" style={{ fontSize: 12 }}>建议：{item.fix_suggestion}</Text></div>}
                  </div>
                </div>
              ))}
            </div>
            <Space wrap style={{ justifyContent: 'flex-end' }}>
              <Button onClick={() => setChapterIssueDetail(null)}>关闭</Button>
              <Button
                disabled={isChapterDisabled(String(chapterIssueDetail.chapter_id))}
                loading={repairingKey === `modal-audit-${chapterIssueDetail.chapter_id}`}
                onClick={() => reAuditChapter(chapterIssueDetail, `modal-audit-${chapterIssueDetail.chapter_id}`)}
              >
                重新审稿
              </Button>
              <Button
                type="primary"
                icon={<ToolOutlined />}
                disabled={isChapterDisabled(String(chapterIssueDetail.chapter_id))}
                loading={repairingKey === `modal-group-${chapterIssueDetail.chapter_id}`}
                onClick={() => lightFixChapterIssueGroup(chapterIssueDetail, `modal-group-${chapterIssueDetail.chapter_id}`)}
              >
                修复本章全部问题
              </Button>
            </Space>
          </div>
        )}
      </Modal>
    </div>
  );
}
