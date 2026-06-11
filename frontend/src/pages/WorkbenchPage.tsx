import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Layout, Card, Typography, Tag, Spin, Button, Empty, Popconfirm, message, Modal, Radio,
  Tabs, Badge, Select, Space, Drawer, Input, Descriptions, Table, Progress, Alert, Row, Col, Collapse,
} from 'antd';
import {
  ThunderboltOutlined, LeftOutlined, TeamOutlined, ApartmentOutlined,
  EnvironmentOutlined, BookOutlined, FullscreenOutlined, FullscreenExitOutlined,
  DeleteOutlined, AuditOutlined, CloseOutlined, EditOutlined,
  BranchesOutlined, HistoryOutlined, StopOutlined, EyeOutlined, PlayCircleOutlined, ScissorOutlined, DownloadOutlined, ReloadOutlined,
  DatabaseOutlined, NodeIndexOutlined, BarChartOutlined, SendOutlined, FileSearchOutlined, WarningOutlined,
} from '@ant-design/icons';
import { volumeApi, chapterApi, projectApi, auditApi } from '@/services/projectApi';
import api from '@/services/api';
import './WorkbenchPage.css';

const { Title, Text, Paragraph } = Typography;
const { Content, Sider } = Layout;

const translateRole = (t: string) => {
  if (!t) return '';
  return t.split('/').map(part => LEGACY_ROLE_LABELS[part.trim()] || part.trim()).join('/');
};
const LEGACY_ROLE_LABELS: Record<string, string> = {
  protagonist: '主角', antagonist: '反派', supporting: '配角', mentor: '导师',
  love_interest: '恋人', other: '其他', hero: '英雄', villain: '恶人',
};
const LEGACY_FACTION_LABELS: Record<string, string> = {
  sect: '宗门', family: '家族', empire: '帝国', guild: '商会', merchant_guild: '商会',
  dark_org: '暗组织', race: '种族', tribe: '部落', alliance: '联盟', temple: '神殿',
  academy: '学院', court: '朝廷',
};
const translateFactionType = (t: string) => LEGACY_FACTION_LABELS[t] || t;
const factionTypeColor = (t: string) => {
  if (['dark_org', '暗组织', '反派组织', '黑帮'].includes(t)) return 'red';
  if (['sect', '门派', '宗门'].includes(t)) return 'blue';
  return 'default';
};
const TASK_LABELS: Record<string, string> = {
  suggest_stories: '构思故事方案', generate_world: '生成世界观', generate_characters: '生成角色势力',
  generate_outline: '生成全书大纲', expand_vol: '展开卷', expand_volume_arcs: '展开卷弧线',
  expand_arc_chapters: '展开弧线章节', write_chapter: '写作章节', audit_chapter: '审计章节',
  review_arc: '评审弧线', batch_write_arc: '批量写作', extract_state: '提取记忆',
  revise_chapter: '修订章节', generate_world_draft: '世界观草稿', generate_characters_draft: '角色草稿',
  repair_from_review: '按评审修复', split_chapter: '智能拆分章节', adjust_outline: 'AI调整大纲',
  adjust_outline_chat: '卷轴调整对话', revise_volume_arc: '调整弧线',
};
const READABILITY_OPTIONS = [
  { value: 'easy', label: '通俗易懂' },
  { value: 'simple', label: '简单直白' },
  { value: 'normal', label: '正常' },
  { value: 'dense', label: '烧脑细腻' },
];
const DEFAULT_WRITING_CONTROLS = {
  readability_mode: 'easy',
  pace_mode: 'standard',
  dialogue_density: 'medium',
  description_density: 'standard',
  humor_level: 'light',
  information_density: 'medium',
  punctuation_style: 'standard',
  chapter_template: 'standard',
  early_grip_mode: 'auto',
  auto_quality_check: true,
  auto_light_fix: true,
};
const DEFAULT_ARC_EXPAND_CFG = {
  arc_strategy: '长篇连载型',
  arc_density: '丰富弧线',
  style_focus: '轻松有梗，主线不散',
  length_control: '按150万字长篇规划，当前卷要有阶段目标、铺垫、误判和余波',
};
const ARC_STRATEGY_OPTIONS = [
  { value: '长篇连载型', label: '长篇连载型' },
  { value: '短篇紧凑型', label: '短篇紧凑型' },
  { value: '轻松单元剧型', label: '轻松单元剧型' },
  { value: '主线强推进型', label: '主线强推进型' },
  { value: '群像展开型', label: '群像展开型' },
];
const ARC_DENSITY_OPTIONS = [
  { value: '少量弧线', label: '少量弧线' },
  { value: '标准弧线', label: '标准弧线' },
  { value: '丰富弧线', label: '丰富弧线' },
  { value: '超细拆分', label: '超细拆分' },
];
const ARC_STYLE_OPTIONS = [
  { value: '轻松有梗，主线不散', label: '轻松有梗' },
  { value: '主线清晰，爽点密集', label: '爽点密集' },
  { value: '角色戏更多，关系变化更明显', label: '角色戏多' },
  { value: '伏笔更强，前后承接更严密', label: '伏笔更强' },
  { value: '日常单元剧感更强，但每段都服务主线', label: '日常单元' },
];
const OPTIMIZE_ACTIONS = [
  { mode: 'make_easy', label: '改易懂' },
  { mode: 'dialogue_natural', label: '对白' },
  { mode: 'punctuation_fix', label: '标点' },
  { mode: 'de_ai', label: '去AI味' },
  { mode: 'add_scene_texture', label: '画面感' },
  { mode: 'strengthen_hook', label: '强钩子' },
  { mode: 'strengthen_readthrough', label: '强追读' },
];

const REVIEW_ISSUE_GROUPS = [
  { key: 'critical_issues', title: '致命问题', color: 'red' },
  { key: 'high_issues', title: '严重问题', color: 'orange' },
  { key: 'low_issues', title: '轻微问题', color: 'blue' },
];

const issueDescription = (issue: any) => {
  if (!issue) return '';
  if (typeof issue === 'string') return issue;
  return issue.description || issue.issue_summary || issue.issue || JSON.stringify(issue);
};

const renderStringList = (items: any[], emptyText = '暂无') => {
  if (!Array.isArray(items) || items.length === 0) return <Text type="secondary">{emptyText}</Text>;
  return (
    <div className="task-detail-list">
      {items.map((item: any, idx: number) => (
        <div key={idx} className="task-detail-list-item">
          {typeof item === 'string' ? item : item?.description || item?.summary || JSON.stringify(item)}
        </div>
      ))}
    </div>
  );
};

const arcValueText = (value: any) => {
  if (value === null || value === undefined || value === '') return '';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  return value.description || value.summary || value.detail || value.name || JSON.stringify(value, null, 2);
};

const renderArcValue = (value: any, emptyText = '未填写') => {
  if (value === null || value === undefined || value === '' || (Array.isArray(value) && value.length === 0)) {
    return <Text type="secondary">{emptyText}</Text>;
  }
  if (Array.isArray(value)) {
    return (
      <div className="arc-detail-list">
        {value.map((item: any, idx: number) => (
          <div key={idx} className="arc-detail-list-item">{arcValueText(item)}</div>
        ))}
      </div>
    );
  }
  return <Paragraph className="arc-detail-text">{arcValueText(value)}</Paragraph>;
};

const RawJsonBlock = ({ title, data }: { title: string; data: any }) => (
  <Collapse
    size="small"
    className="task-raw-collapse"
    items={[{
      key: title,
      label: title,
      children: (
        <pre className="task-json-block">
          {JSON.stringify(data, null, 2)}
        </pre>
      ),
    }]}
  />
);

const ReviewTaskResult = ({ result }: { result: any }) => {
  const score = Number(result?.overall_score || 0);
  const issueCount = REVIEW_ISSUE_GROUPS.reduce((sum, group) => sum + ((result?.[group.key] || []).length), 0);
  return (
    <div className="task-report">
      <div className="task-report-hero">
        <div>
          <div className="task-report-score">{score || '-'}/10</div>
          <Text type="secondary">综合评分</Text>
        </div>
        <div className="task-report-summary">
          <Text strong>评审结论</Text>
          <Paragraph>{result?.summary || '本次评审没有返回总结。'}</Paragraph>
        </div>
        <div className="task-report-stat">
          <span>问题数</span>
          <strong>{issueCount}</strong>
        </div>
      </div>

      {Array.isArray(result?.dimensions) && result.dimensions.length > 0 && (
        <Card size="small" title="维度评分" className="task-report-card">
          <div className="task-dimension-grid">
            {result.dimensions.map((d: any, idx: number) => (
              <div key={idx} className="task-dimension-item">
                <div>
                  <Text strong>{d.name || d.dimension || `维度 ${idx + 1}`}</Text>
                  {d.comment && <Paragraph>{d.comment}</Paragraph>}
                </div>
                <Tag color={(d.score || 0) >= 7 ? 'green' : (d.score || 0) >= 5 ? 'orange' : 'red'}>{d.score ?? '-'}/10</Tag>
              </div>
            ))}
          </div>
        </Card>
      )}

      {REVIEW_ISSUE_GROUPS.map((group) => {
        const issues = result?.[group.key] || [];
        if (!Array.isArray(issues) || issues.length === 0) return null;
        return (
          <Card key={group.key} size="small" title={group.title} className="task-report-card">
            <div className="task-issue-list">
              {issues.map((issue: any, idx: number) => (
                <div key={idx} className={`task-issue-card ${group.color}`}>
                  <div className="task-issue-head">
                    <Text strong>{issue.chapter ? `第${issue.chapter}章` : issue.chapter_number ? `第${issue.chapter_number}章` : '全局'}</Text>
                    {issue.dimension && <Tag>{issue.dimension}</Tag>}
                    {issue.severity && <Tag color={group.color}>{issue.severity}</Tag>}
                  </div>
                  <Paragraph>{issueDescription(issue)}</Paragraph>
                  {issue.evidence && <Paragraph className="task-issue-evidence"><Text strong>证据：</Text>{issue.evidence}</Paragraph>}
                  {issue.fix_suggestion && <Paragraph className="task-issue-fix"><Text strong>建议：</Text>{issue.fix_suggestion}</Paragraph>}
                </div>
              ))}
            </div>
          </Card>
        );
      })}

      {Array.isArray(result?.strengths) && result.strengths.length > 0 && (
        <Card size="small" title="优点" className="task-report-card">{renderStringList(result.strengths)}</Card>
      )}
      {Array.isArray(result?.writing_tips) && result.writing_tips.length > 0 && (
        <Card size="small" title="写作建议" className="task-report-card">{renderStringList(result.writing_tips)}</Card>
      )}
      <RawJsonBlock title="原始评审数据" data={result} />
    </div>
  );
};

const RepairTaskResult = ({ result }: { result: any }) => {
  const plan = result?.repair_plan || {};
  return (
    <div className="task-report">
      <div className="task-report-hero compact">
        <div className="task-report-summary">
          <Text strong>修复诊断</Text>
          <Paragraph>{plan.diagnosis || '本次修复没有返回诊断。'}</Paragraph>
        </div>
        <div className="task-report-stat">
          <span>已修复章节</span>
          <strong>{Array.isArray(result?.repaired_chapters) ? result.repaired_chapters.length : 0}</strong>
        </div>
      </div>
      {Array.isArray(result?.repaired_chapters) && result.repaired_chapters.length > 0 && (
        <Card size="small" title="已修复章节" className="task-report-card">
          <Space wrap>{result.repaired_chapters.map((n: any) => <Tag color="green" key={n}>第{n}章</Tag>)}</Space>
        </Card>
      )}
      {Array.isArray(plan.global_constraints) && plan.global_constraints.length > 0 && (
        <Card size="small" title="后续硬约束" className="task-report-card">{renderStringList(plan.global_constraints)}</Card>
      )}
      {Array.isArray(plan.tasks) && plan.tasks.length > 0 && (
        <Card size="small" title="修复任务" className="task-report-card">
          <div className="task-issue-list">
            {plan.tasks.map((task: any, idx: number) => (
              <div key={idx} className="task-issue-card">
                <div className="task-issue-head">
                  <Text strong>{task.chapter ? `第${task.chapter}章` : '全局'}</Text>
                  {task.priority && <Tag color={task.priority === 'critical' ? 'red' : task.priority === 'high' ? 'orange' : 'blue'}>{task.priority}</Tag>}
                  {task.issue_type && <Tag>{task.issue_type}</Tag>}
                </div>
                <Paragraph>{task.issue_summary || '未返回问题摘要'}</Paragraph>
                {Array.isArray(task.changes_required) && task.changes_required.length > 0 && (
                  <div>{renderStringList(task.changes_required, '无具体改动')}</div>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}
      <RawJsonBlock title="原始修复数据" data={result} />
    </div>
  );
};

const AuditTaskResult = ({ result }: { result: any }) => (
  <div className="task-report">
    <div className="task-report-hero compact">
      <div>
        <div className="task-report-score">{result?.overall_score ?? '-'}/10</div>
        <Text type="secondary">{result?.passed ? '审计通过' : '审计未通过'}</Text>
      </div>
      <div className="task-report-summary">
        <Text strong>读者可能卡住的点</Text>
        {renderStringList(result?.reader_confusions || [], '暂无明显卡点')}
      </div>
    </div>
    {Array.isArray(result?.issues) && result.issues.length > 0 && (
      <Card size="small" title="主要问题" className="task-report-card">
        <div className="task-issue-list">
          {result.issues.map((issue: any, idx: number) => (
            <div key={idx} className="task-issue-card">
              <div className="task-issue-head">
                {issue.dimension && <Tag>{issue.dimension}</Tag>}
                {issue.severity && <Tag color={issue.severity === 'critical' ? 'red' : issue.severity === 'high' ? 'orange' : 'blue'}>{issue.severity}</Tag>}
                {issue.target_text && <Tag color="purple">定位：{issue.target_text}</Tag>}
              </div>
              <Paragraph>{issueDescription(issue)}</Paragraph>
              {issue.fix_suggestion && <Paragraph className="task-issue-fix"><Text strong>建议：</Text>{issue.fix_suggestion}</Paragraph>}
            </div>
          ))}
        </div>
      </Card>
    )}
    <RawJsonBlock title="原始审计数据" data={result} />
  </div>
);

const GenericTaskResult = ({ result }: { result: any }) => {
  if (typeof result === 'string') return <Alert type="success" showIcon message={result} />;
  const arcIssues = Array.isArray(result?.arc_quality?.issues) ? result.arc_quality.issues : [];
  const arcWarnings = Array.isArray(result?.arc_quality?.warnings) ? result.arc_quality.warnings : [];
  const summaryItems = [
    ['摘要', result?.summary || result?.result_summary || result?.message],
    ['生成内容', result?.content ? `${String(result.content).slice(0, 260)}${String(result.content).length > 260 ? '...' : ''}` : ''],
    ['章节数', result?.chapter_count || result?.segment_count],
    ['生成模式', result?.generation_mode === 'segmented' ? '分段生成（角色 / 势力分别推进）' : result?.generation_mode],
    ['角色数', result?.character_count],
    ['势力数', result?.faction_count],
    ['关系数', result?.relation_count],
    ['弧线数', Array.isArray(result?.arcs) ? result.arcs.length : ''],
    ['弧线质量', result?.arc_quality ? `${result.arc_quality.score ?? '-'} / 100${result.arc_quality.passed ? ' · 通过' : ' · 需检查'}` : ''],
    ['新角色', Array.isArray(result?.new_characters) ? result.new_characters.map((c: any) => c.name || c).join('、') : ''],
  ].filter(([, value]) => value);
  return (
    <div className="task-report">
      {summaryItems.length > 0 && (
        <Descriptions size="small" column={1} bordered>
          {summaryItems.map(([label, value]) => (
            <Descriptions.Item key={label} label={label}>{value}</Descriptions.Item>
          ))}
        </Descriptions>
      )}
      {result?.arc_quality && arcIssues.length > 0 && (
        <Card size="small" title="弧线质量问题" className="task-report-card" style={{ marginTop: 12 }}>
          <div className="task-issue-list">
            {arcIssues.map((issue: any, idx: number) => (
              <div key={idx} className="task-issue-card orange">
                <div className="task-issue-head">
                  <Tag>弧线 {Number(issue.arc_index ?? 0) + 1}</Tag>
                  {issue.name && <Text strong>{issue.name}</Text>}
                </div>
                <Paragraph>{issue.issue}</Paragraph>
              </div>
            ))}
          </div>
        </Card>
      )}
      {result?.arc_quality && arcWarnings.length > 0 && (
        <Card size="small" title="弧线质量提醒" className="task-report-card" style={{ marginTop: 12 }}>
          <Alert
            type="info"
            showIcon
            message="这些不是阻断问题，弧线可以继续展开；如果你追求更严密的交接，可以进入对应弧线点“优化交接”。"
            style={{ marginBottom: 12 }}
          />
          <div className="task-issue-list">
            {arcWarnings.map((issue: any, idx: number) => (
              <div key={idx} className="task-issue-card">
                <div className="task-issue-head">
                  <Tag color="blue">弧线 {Number(issue.arc_index ?? 0) + 1}</Tag>
                  {issue.name && <Text strong>{issue.name}</Text>}
                </div>
                <Paragraph>{issue.issue}</Paragraph>
              </div>
            ))}
          </div>
        </Card>
      )}
      <RawJsonBlock title="原始结果数据" data={result} />
    </div>
  );
};

const TaskResultView = ({ task }: { task: any }) => {
  const result = task?.result;
  if (!result) return null;
  const type = String(task?.task_type || '');
  if (type === 'review_arc' || type === 'review_volume' || type === 'review_project_structure') return <ReviewTaskResult result={result} />;
  if (type === 'repair_from_review') return <RepairTaskResult result={result} />;
  if (type === 'audit_chapter') return <AuditTaskResult result={result} />;
  return <GenericTaskResult result={result} />;
};

const SystemHealthView = ({ data }: { data: any }) => {
  if (!data) return <Empty description="暂无健康数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
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
    <div className="system-drawer-content">
      <Card size="small" className="system-summary-card">
        <div className="system-score-row">
          <Progress type="circle" percent={Number(data.overall_score || 0)} size={88} />
          <div>
            <Title level={5} style={{ margin: 0 }}>项目健康度</Title>
            <Text type="secondary">Prompt {data.prompt_version || '-'}</Text>
          </div>
        </div>
      </Card>
      <Row gutter={[8, 8]}>
        {scoreItems.map(([label, value]) => (
          <Col span={12} key={label}>
            <Card size="small">
              <Text type="secondary">{label}</Text>
              <Progress percent={Number(value || 0)} size="small" />
            </Card>
          </Col>
        ))}
      </Row>
      {Array.isArray(data.fatigue_warnings) && data.fatigue_warnings.length > 0 && (
        <Alert type="warning" showIcon message="长篇疲劳警告" description={renderStringList(data.fatigue_warnings)} />
      )}
      {worldAudit && (
        <Card size="small" title="世界规则闸门">
          <div className="system-score-row compact">
            <Progress percent={Number(worldAudit.score || 0)} size="small" status={worldAudit.passed ? 'success' : 'exception'} />
            <Tag color={worldAudit.passed ? 'green' : 'orange'}>{worldAudit.passed ? '通过' : '需补强'}</Tag>
          </div>
          {Array.isArray(worldAudit.risks) && worldAudit.risks.length > 0 && (
            <div className="system-inline-list">
              {worldAudit.risks.slice(0, 4).map((risk: string, idx: number) => <Tag key={idx} color="orange">{risk}</Tag>)}
            </div>
          )}
        </Card>
      )}
      {Array.isArray(data.arc_issues) && data.arc_issues.length > 0 && (
        <Card size="small" title="弧线问题">
          <div className="system-issue-list">
            {data.arc_issues.slice(0, 12).map((item: any, idx: number) => (
              <div key={idx} className="system-issue-item">
                <Text strong>{item.volume || item.name || `弧线 ${idx + 1}`}</Text>
                <Text type="secondary">{item.quality_gate?.related_issues?.[0]?.issue || (item.needs_repair ? '需要修复承接或台阶' : '连续性风险')}</Text>
              </div>
            ))}
          </div>
        </Card>
      )}
      {Array.isArray(data.blueprint_issues) && data.blueprint_issues.length > 0 && (
        <Card size="small" title="章节蓝图问题">
          <div className="system-issue-list">
            {data.blueprint_issues.slice(0, 12).map((item: any) => (
              <div key={item.chapter_number} className="system-issue-item">
                <Text strong>第{item.chapter_number}章 {item.title || ''}</Text>
                <Text type="secondary">{(item.gate?.issues || []).join('；') || '蓝图质量未通过'}</Text>
              </div>
            ))}
          </div>
        </Card>
      )}
      {Array.isArray(data.foreshadowing) && data.foreshadowing.length > 0 && (
        <Card size="small" title="伏笔状态">
          <Space wrap>
            {data.foreshadowing.slice(0, 24).map((f: any, idx: number) => (
              <Tag key={`${f.name}-${idx}`} color={['已回收', '完成', 'done'].includes(f.status) ? 'green' : 'orange'}>
                {f.name || '未命名'} · {f.status || '未定'}
              </Tag>
            ))}
          </Space>
        </Card>
      )}
    </div>
  );
};

const WorldRuleAuditView = ({ data }: { data: any }) => {
  const audit = data?.audit || data?.world_rule_audit || data;
  if (!audit) return <Empty description="暂无规则审计" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  const coverage = audit.coverage || {};
  return (
    <div className="system-drawer-content">
      <Card size="small" className="system-summary-card">
        <div className="system-score-row">
          <Progress type="circle" percent={Number(audit.score || 0)} size={88} status={audit.passed ? 'success' : 'exception'} />
          <div>
            <Title level={5} style={{ margin: 0 }}>世界规则审计</Title>
            <Space wrap style={{ marginTop: 8 }}>
              <Tag color={audit.passed ? 'green' : 'orange'}>{audit.passed ? '规则稳定' : '需要补规则'}</Tag>
              <Tag>问题 {audit.issue_count ?? 0}</Tag>
            </Space>
          </div>
        </div>
      </Card>
      <Row gutter={[8, 8]}>
        {[
          ['硬规则', coverage.hard_rules],
          ['限制', coverage.constraints],
          ['风格规则', coverage.tone_rules],
          ['运行逻辑', coverage.world_logic_items],
          ['特殊规则', coverage.special_rule_items],
        ].map(([label, value]) => (
          <Col span={12} key={label}>
            <Card size="small" className="system-metric-card">
              <Text type="secondary">{label}</Text>
              <strong>{Number(value || 0)}</strong>
            </Card>
          </Col>
        ))}
      </Row>
      {Array.isArray(audit.conflicts) && audit.conflicts.length > 0 && (
        <Card size="small" title="可能冲突">
          <div className="system-issue-list">
            {audit.conflicts.map((item: any, idx: number) => (
              <div key={idx} className="system-issue-item wide">
                <Text strong>{item.source_a} / {item.source_b}</Text>
                <Text type="secondary">{item.risk}：{item.text_a} ↔ {item.text_b}</Text>
              </div>
            ))}
          </div>
        </Card>
      )}
      <Card size="small" title="缺口">
        {renderStringList(audit.gaps || [], '暂无明显缺口')}
      </Card>
      <Card size="small" title="风险">
        {renderStringList(audit.risks || [], '暂无明显风险')}
      </Card>
      <Card size="small" title="建议动作">
        {renderStringList(audit.recommendations || [], '暂无建议')}
      </Card>
    </div>
  );
};

const PromptModulesView = ({ data }: { data: any }) => {
  const modules = data?.modules || [];
  const coverage = data?.coverage || {};
  if (!data) return <Empty description="暂无提示词模块数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  return (
    <div className="system-drawer-content">
      <Card size="small" className="system-summary-card">
        <div className="system-score-row">
          <div className="system-module-count">{coverage.active || 0}/{coverage.total || modules.length}</div>
          <div>
            <Title level={5} style={{ margin: 0 }}>提示词模块</Title>
            <Text type="secondary">Prompt {data.prompt_version || '-'}</Text>
          </div>
        </div>
      </Card>
      <Card size="small" title="覆盖生成面">
        <Space wrap>{(coverage.generation_surfaces || []).map((x: string) => <Tag key={x}>{x}</Tag>)}</Space>
      </Card>
      <div className="system-module-list">
        {modules.map((m: any) => (
          <Card size="small" key={m.key} className="system-module-card">
            <div className="system-module-head">
              <div>
                <Text strong>{m.name}</Text>
                <div><Text type="secondary">{m.key}</Text></div>
              </div>
              <Tag color={m.status === 'active' ? 'green' : 'default'}>{m.status || 'unknown'}</Tag>
            </div>
            <div className="system-inline-list">
              {(m.used_in || []).map((x: string) => <Tag key={x} color="blue">{x}</Tag>)}
            </div>
            <div className="system-inline-list muted">
              {(m.checks || []).map((x: string) => <Tag key={x}>{x}</Tag>)}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};

const StateLedgerView = ({ data }: { data: any }) => {
  const ledger = data?.ledger;
  if (!ledger) return <Empty description="暂无状态账本" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  return (
    <div className="system-drawer-content">
      <Card size="small" title="出场人物">
        <Space wrap>{(ledger.characters || []).slice(0, 60).map((x: string) => <Tag key={x}>{x}</Tag>)}</Space>
      </Card>
      {[
        ['开放线索', 'open_threads'],
        ['章末钩子', 'hooks'],
        ['关系变化', 'relationships'],
        ['物件状态', 'objects'],
        ['外部压力', 'external_pressures'],
      ].map(([title, key]) => (
        <Card size="small" title={title} key={key}>
          <div className="system-issue-list">
            {(ledger[key] || []).slice(-16).map((item: any, idx: number) => (
              <div key={idx} className="system-issue-item">
                <Text strong>{item.chapter_number ? `第${item.chapter_number}章` : `${idx + 1}`}</Text>
                <Text type="secondary">{item.state || item.hook || item.description || item.name || JSON.stringify(item)}</Text>
              </div>
            ))}
            {(!ledger[key] || ledger[key].length === 0) && <Text type="secondary">暂无</Text>}
          </div>
        </Card>
      ))}
    </div>
  );
};

const ImpactView = ({ data }: { data: any }) => {
  if (!data) return <Empty description="暂无影响分析" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  const levelMap: Record<string, { label: string; color: string }> = {
    high: { label: '高影响', color: 'red' },
    medium: { label: '中影响', color: 'orange' },
    low: { label: '低影响', color: 'green' },
  };
  const info = levelMap[data.impact_level] || { label: data.impact_level || '未知', color: 'default' };
  return (
    <div className="system-drawer-content">
      <Alert
        type={data.impact_level === 'high' ? 'error' : data.impact_level === 'medium' ? 'warning' : 'success'}
        showIcon
        message={<span>{data.chapter?.chapter_number ? `第${data.chapter.chapter_number}章` : '当前章节'} · <Tag color={info.color}>{info.label}</Tag></span>}
      />
      <Card size="small" title="可能受影响章节">
        <div className="system-issue-list">
          {(data.impacted_chapters || []).map((item: any) => (
            <div key={item.chapter_number} className="system-issue-item">
              <Text strong>第{item.chapter_number}章 {item.title || ''}</Text>
              <Text type="secondary">{(item.reasons || []).join('；')}</Text>
            </div>
          ))}
          {(!data.impacted_chapters || data.impacted_chapters.length === 0) && <Text type="secondary">未发现直接依赖章节</Text>}
        </div>
      </Card>
      <Card size="small" title="建议动作">
        {renderStringList(data.recommended_actions || [])}
      </Card>
    </div>
  );
};

const arcQualityFor = (volume: any, arcIndex: number) => {
  const check = (volume?.arc_bridge_checks || []).find((item: any) => item.arc_index === arcIndex);
  return check?.quality_gate || check?.bridge_check || check;
};

const arcQualityIssues = (quality: any) => (
  Array.isArray(quality?.related_issues) ? quality.related_issues
    : Array.isArray(quality?.issues) ? quality.issues
      : quality?.needs_repair ? [{ issue: quality.quality_gate?.related_issues?.[0]?.issue || '需要补齐弧线交接、变化台阶或因果链' }]
        : []
);

const arcQualityWarnings = (quality: any) => (
  Array.isArray(quality?.related_warnings) ? quality.related_warnings
    : Array.isArray(quality?.warnings) ? quality.warnings
      : []
);

const arcContinuityRepairInstruction = (quality: any, arc: any, checks: any[] = []) => {
  const issues = arcQualityIssues(quality).map((item: any) => item.issue || item.description || '').filter(Boolean);
  const missing = checks
    .filter((item: any) => item.failed)
    .map((item: any) => `缺少${item.label}(${item.key})`);
  const issueText = [...issues, ...missing].length
    ? [...issues, ...missing].join('；')
    : '这条弧线可能缺少清晰交接、变化台阶或因果链。';
  return [
    '请只修复这条弧线的连续性结构，不要改变本卷主线目标、章节范围和弧线核心功能。',
    `当前质量问题：${issueText}`,
    '必须补齐或重写：handoff_from_previous、handoff_to_next、opening_state、ending_state、continuity_chain、arc_steps。',
    'arc_steps 必须有 4-7 个变化台阶，每个台阶写清 starting_state、trigger_event、visible_action、friction、state_change、consequence、carry_forward。',
    '交接物必须具体到可写进正文的东西，例如物件、伤势、承诺、误会、秘密、债务、追兵、时间限制或一句话。',
    `当前弧线：${arc?.name || ''}`,
  ].join('\n');
};

const arcHandoffPolishInstruction = (quality: any, arc: any) => {
  const warnings = arcQualityWarnings(quality).map((item: any) => item.issue || item.description || '').filter(Boolean);
  return [
    '请只优化这条弧线与前后弧线的交接表达，不要改变弧线名称、章节范围、核心事件、主角阶段目标和结局。',
    `当前提醒：${warnings.join('；') || '交接语义需要更清晰。'}`,
    '重点调整 handoff_from_previous、handoff_to_next、dependence_on_previous、payoff_for_next、continuity_chain，让上一弧线交出的具体物件/压力/承诺/秘密，能被本弧线明确接住，并把本弧线的新后果交给下一弧线。',
    `当前弧线：${arc?.name || ''}`,
  ].join('\n');
};

const arcQualityStatus = (quality: any, checks: any[] = []) => {
  const score = typeof quality?.score === 'number' ? quality.score : null;
  const issues = arcQualityIssues(quality);
  const warnings = arcQualityWarnings(quality);
  const hasStructuralGaps = checks.some((item: any) => item.failed);
  if (!quality) return { label: '未检查', color: 'default', help: '这条弧线还没有连续性评分。' };
  if (quality.passed === false || hasStructuralGaps) return { label: `结构需修${score !== null ? ` ${score}` : ''}`, color: 'orange', help: '缺少关键结构字段，建议先修复再展开章节。' };
  if (warnings.length) return { label: `交接提醒${score !== null ? ` ${score}` : ''}`, color: 'blue', help: '结构可用，但前后弧线交接表达还可以更清楚。' };
  if (issues.length) return { label: `结构通过${score !== null ? ` ${score}` : ''}`, color: 'green', help: '没有阻断问题，可以继续展开章节。' };
  return { label: `结构通过${score !== null ? ` ${score}` : ''}`, color: 'green', help: '结构完整，可以继续展开章节。' };
};

const arcHasStructuralGaps = (quality: any, checks: any[] = []) => (
  quality?.passed === false || checks.some((item: any) => item.failed)
);

const arcQualityChecks = (arc: any, index: number, quality: any) => {
  const issueFields = new Set(arcQualityIssues(quality).map((x: any) => x.field).filter(Boolean));
  const warningFields = new Set(arcQualityWarnings(quality).map((x: any) => x.field).filter(Boolean));
  const rows = [
    { key: 'opening_state', label: '开局状态', ok: Boolean(arc?.opening_state), help: '弧线开始时人物/局势处在什么状态。' },
    { key: 'ending_state', label: '终点状态', ok: Boolean(arc?.ending_state), help: '弧线结束时产生了什么新局面。' },
    { key: 'handoff_from_previous', label: '上承交接', ok: index === 0 || Boolean(arc?.handoff_from_previous || arc?.dependence_on_previous), help: '是否明确接住上一弧线交出的物件、压力、秘密或承诺。' },
    { key: 'handoff_to_next', label: '下启钩子', ok: Boolean(arc?.handoff_to_next || arc?.payoff_for_next), help: '是否把新压力交给下一弧线或下一卷。' },
    { key: 'continuity_chain', label: '因果链', ok: Boolean(arc?.continuity_chain), help: '是否写清上一状态 -> 触发事件 -> 选择 -> 后果 -> 下一压力。' },
    { key: 'arc_steps', label: '变化台阶', ok: Array.isArray(arc?.arc_steps) && arc.arc_steps.length >= 4, help: '是否有至少 4 个可承载章节的变化台阶。' },
    { key: 'irreplaceable_value', label: '不可替代', ok: Boolean(arc?.irreplaceable_value), help: '是否说明删掉这条弧线后全卷会缺什么。' },
  ];
  return rows.map((row) => ({
    ...row,
    warning: warningFields.has(row.key),
    failed: issueFields.has(row.key) || !row.ok,
  }));
};

const chapterGate = (chapter: any) => (
  chapter?.blueprint?.blueprint_quality_gate || chapter?.continuity_checks?.blueprint_quality_gate || null
);
const AUDIT_SEVERITY_LABELS: Record<string, { label: string; color: string }> = {
  critical: { label: '致命', color: 'red' },
  high: { label: '严重', color: 'orange' },
  medium: { label: '中等', color: 'gold' },
  low: { label: '轻微', color: 'blue' },
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
    // Ignore private mode/storage quota failures; same-tab event still works.
  }
};

const extractAuditTargetText = (issue: any, source: string) => {
  const direct = String(issue?.target_text || '').trim();
  if (direct && source.includes(direct)) return direct;
  const haystack = `${issue?.description || ''}\n${issue?.fix_suggestion || ''}`;
  const matches = [
    ...haystack.matchAll(/“([^”]{2,80})”/g),
    ...haystack.matchAll(/"([^"]{2,80})"/g),
    ...haystack.matchAll(/'([^']{2,80})'/g),
  ];
  const found = matches.map((m) => m[1]?.trim()).find((text) => text && source.includes(text));
  return found || direct;
};

const getParagraphByTarget = (source: string, target: string) => {
  const index = source.indexOf(target);
  if (index < 0) return '';
  const before = source.lastIndexOf('\n', index);
  const after = source.indexOf('\n', index + target.length);
  return source.slice(before + 1, after === -1 ? source.length : after).trim();
};

const getContextBlockByTarget = (source: string, target: string) => {
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
  if (targetIndex < 0) return getParagraphByTarget(source, target);
  return paragraphs.slice(Math.max(0, targetIndex - 2), Math.min(paragraphs.length, targetIndex + 2)).join('\n').trim();
};

export default function WorkbenchPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [project, setProject] = useState<any>(null);
  const [volumes, setVolumes] = useState<any[]>([]);
  const [chapters, setChapters] = useState<any[]>([]);
  const [currentChapter, setCurrentChapter] = useState<any>(null);
  const [content, setContent] = useState('');
  const [saveState, setSaveState] = useState<'saved' | 'dirty' | 'saving' | 'error'>('saved');
  const [loading, setLoading] = useState(true);
  const [projectInfoOpen, setProjectInfoOpen] = useState(false);
  const [projectInfoSaving, setProjectInfoSaving] = useState(false);
  const [projectInfoDraft, setProjectInfoDraft] = useState({ title: '', story_brief: '' });
  const [writing, setWriting] = useState(false);
  const [readabilityMode, setReadabilityMode] = useState('easy');
  const [writingSettingsOpen, setWritingSettingsOpen] = useState(false);
  const [writingSettingsSaving, setWritingSettingsSaving] = useState(false);
  const [writingControlsDraft, setWritingControlsDraft] = useState<any>(DEFAULT_WRITING_CONTROLS);
  const [optimizingMode, setOptimizingMode] = useState<string | null>(null);
  const [splittingChapter, setSplittingChapter] = useState(false);
  const [auditing, setAuditing] = useState(false);
  const [auditResult, setAuditResult] = useState<any>(null);
  const [issueRepairingKey, setIssueRepairingKey] = useState<string | null>(null);
  const [reviewing, setReviewing] = useState(false);
  const [repairingReview, setRepairingReview] = useState(false);
  const [reviewResult, setReviewResult] = useState<any>(null);
  const [reviewScope, setReviewScope] = useState<any>(null);
  const [reviewModalOpen, setReviewModalOpen] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [rightTab, setRightTab] = useState('characters');
  const [rightPanelOpen, setRightPanelOpen] = useState(true);
  const [expandedVolume, setExpandedVolume] = useState<string | null>(null);
  const [expandedArc, setExpandedArc] = useState<number | null>(null);
  const [expandModalOpen, setExpandModalOpen] = useState(false);
  const [expandVol, setExpandVol] = useState<any>(null);
  const [expandMode, setExpandMode] = useState<'arc' | 'chapters'>('arc');
  const [expandArcIdx, setExpandArcIdx] = useState(0);
  const [arcExpandCfg, setArcExpandCfg] = useState(DEFAULT_ARC_EXPAND_CFG);
  const [expandCfg, setExpandCfg] = useState({ pacing: 'medium', event_density: 'medium', expansion_scale: 'standard' });
  const [expandLoading, setExpandLoading] = useState<string | null>(null);
  const [adjustModalOpen, setAdjustModalOpen] = useState(false);
  const [adjustVol, setAdjustVol] = useState<any>(null);
  const [adjustArcIndex, setAdjustArcIndex] = useState<number | null>(null);
  const [adjustScope, setAdjustScope] = useState<'summary_only' | 'outline'>('summary_only');
  const [adjustInstruction, setAdjustInstruction] = useState('');
  const [adjustingOutline, setAdjustingOutline] = useState(false);
  const [adjustMessages, setAdjustMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string }>>([]);
  const [adjustChatInput, setAdjustChatInput] = useState('');
  const [adjustChatLoading, setAdjustChatLoading] = useState(false);
  const [adjustBackendOutdated, setAdjustBackendOutdated] = useState(false);
  const [rightData, setRightData] = useState({ characters: [], factions: [] });
  const [tasks, setTasks] = useState<any[]>([]);
  const [taskDrawerOpen, setTaskDrawerOpen] = useState(false);
  const [taskDetailOpen, setTaskDetailOpen] = useState(false);
  const [taskDetail, setTaskDetail] = useState<any>(null);
  const [taskActionLoading, setTaskActionLoading] = useState<string | null>(null);
  const [batchModalOpen, setBatchModalOpen] = useState(false);
  const [batchVolume, setBatchVolume] = useState<any>(null);
  const [batchArcIdx, setBatchArcIdx] = useState(0);
  const [batchSelectedChs, setBatchSelectedChs] = useState<Set<string>>(new Set());
  const [batchReadabilityMode, setBatchReadabilityMode] = useState('easy');
  const [exportModalOpen, setExportModalOpen] = useState(false);
  const [exportCfg, setExportCfg] = useState({ scope: 'volume', volumeId: '', arcName: '', format: 'md' });
  const [exporting, setExporting] = useState(false);
  const [systemDrawerOpen, setSystemDrawerOpen] = useState(false);
  const [systemTab, setSystemTab] = useState('health');
  const [systemLoading, setSystemLoading] = useState(false);
  const [systemHealth, setSystemHealth] = useState<any>(null);
  const [stateLedger, setStateLedger] = useState<any>(null);
  const [contextPreview, setContextPreview] = useState<any>(null);
  const [worldRuleAudit, setWorldRuleAudit] = useState<any>(null);
  const [promptModules, setPromptModules] = useState<any>(null);
  const [arcDetailOpen, setArcDetailOpen] = useState(false);
  const [arcDetail, setArcDetail] = useState<any>(null);
  const [impactModalOpen, setImpactModalOpen] = useState(false);
  const [impactLoading, setImpactLoading] = useState(false);
  const [impactData, setImpactData] = useState<any>(null);

  const loadAll = () => {
    if (!projectId) return;
    Promise.all([projectApi.get(projectId), volumeApi.list(projectId), chapterApi.list(projectId)])
      .then(([p, v, c]) => { setProject(p); setVolumes(v); setChapters(c); setLoading(false); })
      .catch(() => setLoading(false));
  };

  const loadRightPanel = () => {
    if (!projectId) return;
    Promise.all([
      api.get(`/projects/${projectId}/characters`),
      api.get(`/projects/${projectId}/factions`),
    ]).then(([c, f]) => setRightData({
      characters: c.data?.characters || [],
      factions: f.data?.factions || [],
    }));
  };

  const refreshTasks = () => api.get(`/projects/${projectId}/wizard/tasks`).then(r => setTasks(r.data?.tasks || []));

  const cancelTask = async (taskId: string) => {
    await api.post(`/projects/${projectId}/wizard/cancel-task/${taskId}`);
    refreshTasks();
  };

  const retryTask = async (task: any) => {
    if (!projectId || !task?.id) return;
    setTaskActionLoading(task.id);
    try {
      const res = await api.post(`/projects/${projectId}/wizard/retry-task/${task.id}`);
      message.success('已重新开始任务');
      refreshTasks();
      if (res.data?.task_id) {
        setTaskDetail((prev: any) => prev?.id === task.id ? { ...prev, retry_task_id: res.data.task_id } : prev);
      }
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e.message || '重新开始失败');
    }
    setTaskActionLoading(null);
  };

  useEffect(() => { loadAll(); loadRightPanel(); }, [projectId]);
  useEffect(() => {
    const controls = { ...DEFAULT_WRITING_CONTROLS, ...(project?.writing_style?.writing_controls || {}) };
    setWritingControlsDraft(controls);
    setReadabilityMode(controls.readability_mode || 'easy');
    setBatchReadabilityMode(controls.readability_mode || 'easy');
  }, [project?.id]);
  useEffect(() => {
    if (currentChapter?.id) {
      setContent(currentChapter.content || '');
      setSaveState('saved');
    }
  }, [currentChapter?.id]);

  useEffect(() => {
    if (!currentChapter?.id) return;
    if (content === (currentChapter.content || '')) return;
    setSaveState('dirty');
    const timer = window.setTimeout(() => { saveContent(); }, 1200);
    return () => window.clearTimeout(timer);
  }, [content, currentChapter?.id]);

  const selectChapter = async (ch: any) => {
    if (currentChapter?.id && content !== (currentChapter.content || '')) {
      await saveContent();
    }
    setCurrentChapter(ch);
    setContent(ch.content || '');
    setAuditResult(null);
    if (project?.wizard_step >= 3) setIsFullscreen(false);
  };

  const saveContent = async () => {
    if (!projectId || !currentChapter) return;
    setSaveState('saving');
    try {
      const updated = await chapterApi.update(projectId, currentChapter.id, { content, word_count: content.length });
      setCurrentChapter((prev: any) => prev?.id === updated.id ? { ...prev, content: updated.content, word_count: updated.word_count } : prev);
      setChapters((prev: any[]) => prev.map((ch: any) => ch.id === updated.id ? { ...ch, content: updated.content, word_count: updated.word_count, status: updated.status } : ch));
      setSaveState('saved');
    } catch {
      setSaveState('error');
      message.error('章节保存失败');
    }
  };

  const pollTask = async (taskId: string, maxRetries = 60, key = 'task') => {
    for (let i = 0; i < maxRetries; i++) {
      await new Promise(r => setTimeout(r, 2000));
      const p = await api.get(`/projects/${projectId}/wizard/task/${taskId}`);
      if (p.data.status === 'running' && p.data.progress_label) {
        message.loading({ content: p.data.progress_label, key, duration: 0 });
        refreshTasks();
      }
      if (p.data.status === 'completed') { message.success({ content: '完成', key }); return p.data.result; }
      if (p.data.status === 'failed') throw new Error(p.data.error || '失败');
    }
    throw new Error('超时');
  };

  const openTaskDetail = (task: any) => {
    setTaskDetail(task);
    setTaskDetailOpen(true);
  };

  const openProjectInfo = () => {
    setProjectInfoDraft({
      title: project?.title || '',
      story_brief: project?.story_brief || '',
    });
    setProjectInfoOpen(true);
  };

  const saveProjectInfo = async () => {
    if (!projectId) return;
    setProjectInfoSaving(true);
    try {
      const updated = await projectApi.update(projectId, {
        title: projectInfoDraft.title.trim() || '未命名项目',
        story_brief: projectInfoDraft.story_brief,
      });
      setProject(updated);
      setProjectInfoOpen(false);
      message.success('项目信息已保存');
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e.message || '保存失败');
    }
    setProjectInfoSaving(false);
  };

  const launchRepairFromTask = async (task: any) => {
    if (!projectId || !task?.result || !task?.meta?.volume_id) return;
    setTaskActionLoading(task.id);
    try {
      const res = await api.post(`/projects/${projectId}/wizard/repair-from-review/${task.meta.volume_id}`, {
        review_result: task.result,
        review_scope: task.meta.arc_index !== undefined ? `弧线「${task.meta.arc_index}」` : task.meta.volume_id,
        apply: true,
        reaudit: false,
      });
      message.loading({ content: 'AI 正在按历史评审修复…', key: 'repair-history', duration: 0 });
      const result = await pollTask(res.data.task_id, 1200, 'repair-history');
      const chs = await chapterApi.list(projectId);
      setChapters(chs);
      refreshTasks();
      message.success({ content: `已修复 ${result?.repaired_chapters?.length || 0} 章`, key: 'repair-history' });
    } catch (e: any) {
      message.error({ content: e.message || '修复失败', key: 'repair-history' });
    }
    setTaskActionLoading(null);
  };

  const aiWriteChapter = async () => {
    if (!currentChapter || !projectId) return;
    setWriting(true);
    try {
      if (content !== (currentChapter.content || '')) await saveContent();
      const selectedMode = READABILITY_OPTIONS.find((item) => item.value === readabilityMode)?.label || '通俗易懂';
      const res = await api.post(`/projects/${projectId}/wizard/write-chapter/${currentChapter.id}`, {
        controls: {
          readability_mode: readabilityMode,
          target_words: currentChapter.target_words || 3500,
        },
      });
      message.loading({ content: `AI 正在按「${selectedMode}」写本章…`, key: 'write', duration: 0 });
      const result = await pollTask(res.data.task_id, 120, 'write');
      setContent((prev: string) => prev + (result?.content || ''));
      const ch = await chapterApi.get(projectId, currentChapter.id);
      setCurrentChapter(ch);
      const newChars = result?.new_characters || [];
      if (newChars.length) {
        message.success({ content: `完成，发现 ${newChars.length} 个新角色：${newChars.map((c: any) => c.name).join('、')}`, key: 'write' });
        loadRightPanel();
      } else {
        message.success({ content: 'AI 完成本章', key: 'write' });
      }
    } catch (e: any) { message.error({ content: e.message || '失败', key: 'write' }); }
    setWriting(false);
  };

  const smartSplitChapter = async () => {
    if (!currentChapter || !projectId) return;
    if (content.length < 5400) {
      message.info('当前章节不算长，暂不需要拆分');
      return;
    }
    setSplittingChapter(true);
    try {
      await saveContent();
      const res = await api.post(`/projects/${projectId}/wizard/split-chapter/${currentChapter.id}`, {
        target_words: 3500,
        apply: true,
      });
      message.loading({ content: 'AI 正在按语义拆分章节（约3500-4000字）…', key: 'split', duration: 0 });
      const result = await pollTask(res.data.task_id, 120, 'split');
      const chs = await chapterApi.list(projectId);
      setChapters(chs);
      const latest = await chapterApi.get(projectId, currentChapter.id);
      setCurrentChapter(latest);
      setContent(latest.content || '');
      message.success({ content: `已拆成 ${result?.segment_count || 0} 章`, key: 'split' });
      refreshTasks();
    } catch (e: any) {
      message.error({ content: e.message || '拆分失败', key: 'split' });
    }
    setSplittingChapter(false);
  };

  const auditChapter = async () => {
    if (!currentChapter || !projectId) return;
    if (auditResult) return; // already audited, just view
    setAuditing(true);
    setAuditResult(null);
    try {
      if (content !== (currentChapter.content || '')) await saveContent();
      const res = await api.post(`/projects/${projectId}/wizard/audit-chapter/${currentChapter.id}`);
      message.loading({ content: 'AI 正在审计…', key: 'audit', duration: 0 });
      const result = await pollTask(res.data.task_id, 30, 'audit');
      setAuditResult(result);
      notifyQualityUpdated(projectId, currentChapter.id);
    } catch (e: any) { message.error({ content: e.message || '审计失败', key: 'audit' }); }
    setAuditing(false);
  };

  const saveWritingSettings = async () => {
    if (!projectId || !project) return;
    setWritingSettingsSaving(true);
    try {
      const nextStyle = { ...(project.writing_style || {}), writing_controls: writingControlsDraft };
      const updated = await projectApi.update(projectId, { writing_style: nextStyle });
      setProject(updated);
      setReadabilityMode(writingControlsDraft.readability_mode || 'easy');
      setBatchReadabilityMode(writingControlsDraft.readability_mode || 'easy');
      setWritingSettingsOpen(false);
      message.success('写作总控已保存');
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e.message || '保存失败');
    }
    setWritingSettingsSaving(false);
  };

  const optimizeChapter = async (mode: string) => {
    if (!currentChapter || !projectId) return;
    setOptimizingMode(mode);
    try {
      if (content !== (currentChapter.content || '')) await saveContent();
      const controls = { ...DEFAULT_WRITING_CONTROLS, ...(project?.writing_style?.writing_controls || {}), readability_mode: readabilityMode };
      const res = await api.post(`/projects/${projectId}/wizard/revise-chapter/${currentChapter.id}`, {
        mode,
        instruction: '按预设模式优化当前章节，保留核心剧情、人物关系、关键线索和章末钩子。',
        selection: '',
        controls,
        apply: true,
      });
      const action = OPTIMIZE_ACTIONS.find((item) => item.mode === mode)?.label || '优化';
      message.loading({ content: `AI 正在${action}…`, key: 'optimize', duration: 0 });
      await pollTask(res.data.task_id, 120, 'optimize');
      const latest = await chapterApi.get(projectId, currentChapter.id);
      setCurrentChapter(latest);
      setContent(latest.content || '');
      setAuditResult(null);
      notifyQualityUpdated(projectId, currentChapter.id);
      message.success({ content: `${action}完成`, key: 'optimize' });
    } catch (e: any) {
      message.error({ content: e.message || '优化失败', key: 'optimize' });
    }
    setOptimizingMode(null);
  };

  const repairAuditIssue = async (issue: any, scope: 'sentence' | 'paragraph' | 'context', index: number) => {
    if (!currentChapter || !projectId) return;
    const target = extractAuditTargetText(issue, content);
    if (!target || !content.includes(target)) {
      message.warning('没有在正文里找到这条问题对应的原文，请重新审计或手动修这一处');
      return;
    }
    const selection = scope === 'sentence'
      ? target
      : scope === 'context'
        ? getContextBlockByTarget(content, target)
        : getParagraphByTarget(content, target);
    if (!selection || !content.includes(selection)) {
      message.warning('没有定位到可替换的段落，请先手动保存正文后重新审计');
      return;
    }
    const key = `${index}-${scope}`;
    setIssueRepairingKey(key);
    try {
      if (content !== (currentChapter.content || '')) await saveContent();
      const controls = { ...DEFAULT_WRITING_CONTROLS, ...(project?.writing_style?.writing_controls || {}), readability_mode: readabilityMode };
      const res = await api.post(`/projects/${projectId}/wizard/revise-chapter/${currentChapter.id}`, {
        mode: LOCAL_FIX_MODES[scope],
        instruction: `只修复这条审计问题，不得改动选择范围之外的正文。问题：${JSON.stringify(issue)}`,
        selection,
        controls,
        apply: true,
      });
      const action = scope === 'sentence' ? '原句修复' : scope === 'paragraph' ? '段落修复' : '局部修复';
      message.loading({ content: `AI 正在${action}…`, key: 'issue-repair', duration: 0 });
      await pollTask(res.data.task_id, 120, 'issue-repair');
      const latest = await chapterApi.get(projectId, currentChapter.id);
      setCurrentChapter(latest);
      setContent(latest.content || '');
      setAuditResult(null);
      notifyQualityUpdated(projectId, currentChapter.id);
      message.success({ content: `${action}完成，已清空旧审计结果`, key: 'issue-repair' });
    } catch (e: any) {
      message.error({ content: e?.response?.data?.detail || e.message || '局部修复失败', key: 'issue-repair' });
    }
    setIssueRepairingKey(null);
  };

  const reviseByAudit = async (mode: 'quality_light_fix' | 'audit_full_rewrite') => {
    if (!currentChapter || !projectId || !auditResult) return;
    const key = mode === 'audit_full_rewrite' ? 'audit-rewrite' : 'audit-light';
    setOptimizingMode(key);
    try {
      if (content !== (currentChapter.content || '')) await saveContent();
      const controls = { ...DEFAULT_WRITING_CONTROLS, ...(project?.writing_style?.writing_controls || {}), readability_mode: readabilityMode };
      const res = await api.post(`/projects/${projectId}/wizard/revise-chapter/${currentChapter.id}`, {
        mode,
        instruction: `根据当前单章审计报告处理本章。审计报告：${JSON.stringify(auditResult)}。${mode === 'audit_full_rewrite' ? '请完整重写本章，逐条解决问题，但保留章节核心事实、人物关系、关键线索和章末钩子。' : '请轻量修复审计问题，不改变核心剧情。'}`,
        selection: '',
        controls,
        apply: true,
      });
      const action = mode === 'audit_full_rewrite' ? '按审计重写' : '按审计轻修';
      message.loading({ content: `AI 正在${action}…`, key: 'audit-revise', duration: 0 });
      await pollTask(res.data.task_id, 180, 'audit-revise');
      const latest = await chapterApi.get(projectId, currentChapter.id);
      setCurrentChapter(latest);
      setContent(latest.content || '');
      setAuditResult(null);
      notifyQualityUpdated(projectId, currentChapter.id);
      message.success({ content: `${action}完成，已清空旧审计结果`, key: 'audit-revise' });
    } catch (e: any) {
      message.error({ content: e?.response?.data?.detail || e.message || '按审计处理失败', key: 'audit-revise' });
    }
    setOptimizingMode(null);
  };

  const reviseByAuditTask = async (task: any, mode: 'quality_light_fix' | 'audit_full_rewrite') => {
    if (!projectId || !task?.result || !task?.meta?.chapter_id) return;
    const chapterId = task.meta.chapter_id;
    const key = `${task.id}-${mode}`;
    setTaskActionLoading(key);
    try {
      const controls = { ...DEFAULT_WRITING_CONTROLS, ...(project?.writing_style?.writing_controls || {}), readability_mode: readabilityMode };
      const res = await api.post(`/projects/${projectId}/wizard/revise-chapter/${chapterId}`, {
        mode,
        instruction: `根据这条 AI 任务里的单章审计报告处理本章。审计报告：${JSON.stringify(task.result)}。${mode === 'audit_full_rewrite' ? '请完整重写本章，逐条解决问题，但保留章节核心事实、人物关系、关键线索和章末钩子。' : '请轻量修复审计问题，不改变核心剧情。'}`,
        selection: '',
        controls,
        apply: true,
      });
      const action = mode === 'audit_full_rewrite' ? '按审计重写' : '按审计轻修';
      message.loading({ content: `AI 正在${action}…`, key: 'audit-task-revise', duration: 0 });
      await pollTask(res.data.task_id, 180, 'audit-task-revise');
      const latest = await chapterApi.get(projectId, chapterId);
      setChapters((prev: any[]) => prev.map((ch: any) => ch.id === latest.id ? latest : ch));
      if (currentChapter?.id === chapterId) {
        setCurrentChapter(latest);
        setContent(latest.content || '');
        setAuditResult(null);
      }
      notifyQualityUpdated(projectId, chapterId);
      refreshTasks();
      message.success({ content: `${action}完成`, key: 'audit-task-revise' });
    } catch (e: any) {
      message.error({ content: e?.response?.data?.detail || e.message || '按审计处理失败', key: 'audit-task-revise' });
    }
    setTaskActionLoading(null);
  };

  const reviewArc = async (vol: any, arcIdx: number) => {
    if (!projectId) return;
    setReviewing(true);
    try {
      const res = await api.post(`/projects/${projectId}/wizard/review-arc/${vol.id}`, { arc_index: arcIdx });
      message.loading({ content: 'AI 正在全面评审…', key: 'review', duration: 0 });
      const result = await pollTask(res.data.task_id, 120, 'review');
      setReviewResult(result);
      setReviewScope({ volumeId: vol.id, arcIndex: arcIdx, name: vol.narrative_arcs?.[arcIdx]?.name || vol.title });
      setReviewModalOpen(true);
    } catch (e: any) { message.error({ content: e.message || '评审失败', key: 'review' }); }
    setReviewing(false);
  };

  const repairFromReview = async (payload?: { reviewResult?: any; volumeId?: string; scopeName?: string }) => {
    const targetReview = payload?.reviewResult || reviewResult;
    const targetVolumeId = payload?.volumeId || reviewScope?.volumeId;
    const targetScopeName = payload?.scopeName || reviewScope?.name;
    if (!projectId || !targetReview || !targetVolumeId) return;
    setRepairingReview(true);
    try {
      const res = await api.post(`/projects/${projectId}/wizard/repair-from-review/${targetVolumeId}`, {
        review_result: targetReview,
        review_scope: targetScopeName ? `弧线「${targetScopeName}」` : '',
        apply: true,
        reaudit: false,
      });
      message.loading({ content: 'AI 正在按评审报告修复…', key: 'repair', duration: 0 });
      const result = await pollTask(res.data.task_id, 1200, 'repair');
      const chs = await chapterApi.list(projectId);
      setChapters(chs);
      if (currentChapter?.id) {
        const latest = await chapterApi.get(projectId, currentChapter.id);
        setCurrentChapter(latest);
        setContent(latest.content || '');
      }
      message.success({ content: `已修复 ${result?.repaired_chapters?.length || 0} 章`, key: 'repair' });
      refreshTasks();
      setReviewModalOpen(false);
    } catch (e: any) { message.error({ content: e.message || '修复失败', key: 'repair' }); }
    setRepairingReview(false);
  };

  const batchWriteArc = async (vol: any, arcIdx: number, chapterIds?: string[], mode: string = 'easy') => {
    if (!projectId) return;
    setExpandLoading(`${vol.id}-batch-${arcIdx}`);
    try {
      const selectedMode = READABILITY_OPTIONS.find((item) => item.value === mode)?.label || '通俗易懂';
      const body: any = { arc_index: arcIdx, readability_mode: mode };
      if (chapterIds?.length) body.chapter_ids = chapterIds;
      const res = await api.post(`/projects/${projectId}/wizard/batch-write-arc/${vol.id}`, body);
      message.loading({ content: `后端批量任务已提交，模式：${selectedMode}…`, key: 'batch', duration: 0 });
      await pollTask(res.data.task_id, 1200, 'batch');
      const chs = await chapterApi.list(projectId);
      setChapters(chs);
      message.success({ content: '批量写作完成', key: 'batch' });
      loadRightPanel();
    } catch (e: any) { message.error({ content: e.message || '批量写作失败', key: 'batch' }); }
    setExpandLoading(null);
  };

  const openExportModal = () => {
    const defaultVol = currentVolume || volumes[0];
    const firstArc = defaultVol?.narrative_arcs?.[0]?.name || '';
    setExportCfg({
      scope: 'volume',
      volumeId: defaultVol?.id || '',
      arcName: firstArc,
      format: 'md',
    });
    setExportModalOpen(true);
  };

  const loadSystemPanel = async (tab: string = systemTab) => {
    if (!projectId) return;
    setSystemLoading(true);
    try {
      if (tab === 'health') {
        const res = await api.get(`/projects/${projectId}/wizard/project-health`);
        setSystemHealth(res.data);
      } else if (tab === 'ledger') {
        const res = await api.get(`/projects/${projectId}/wizard/state-ledger`);
        setStateLedger(res.data);
      } else if (tab === 'context') {
        const params: any = {};
        if (currentChapter?.id) params.chapter_id = currentChapter.id;
        else if (currentVolume?.id) params.volume_id = currentVolume.id;
        const res = await api.get(`/projects/${projectId}/wizard/context-preview`, { params });
        setContextPreview(res.data);
      } else if (tab === 'world') {
        const res = await api.get(`/projects/${projectId}/wizard/world-rule-audit`);
        setWorldRuleAudit(res.data);
      } else if (tab === 'prompts') {
        const res = await api.get(`/projects/${projectId}/wizard/prompt-modules`);
        setPromptModules(res.data);
      }
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e.message || '加载系统诊断失败');
    } finally {
      setSystemLoading(false);
    }
  };

  const openSystemDrawer = (tab: string = 'health') => {
    setSystemTab(tab);
    setSystemDrawerOpen(true);
    loadSystemPanel(tab);
  };

  const openArcDetail = (volume: any, arc: any, arcIndex: number, quality: any) => {
    setArcDetail({ volume, arc, arcIndex, quality });
    setArcDetailOpen(true);
  };

  const openImpactAnalysis = async () => {
    if (!projectId || !currentChapter?.id) return;
    setImpactModalOpen(true);
    setImpactLoading(true);
    try {
      const res = await api.get(`/projects/${projectId}/wizard/impact/chapter/${currentChapter.id}`);
      setImpactData(res.data);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e.message || '影响分析失败');
    } finally {
      setImpactLoading(false);
    }
  };

  const doExport = async () => {
    if (!projectId || !exportCfg.volumeId) return;
    setExporting(true);
    try {
      const res = await api.post(`/projects/${projectId}/wizard/export-manuscript`, {
        scope: exportCfg.scope,
        volume_id: exportCfg.volumeId,
        arc_name: exportCfg.scope === 'arc' ? exportCfg.arcName : '',
        format: exportCfg.format,
        include_empty: false,
      }, { responseType: 'blob' });
      const contentType = String(res.headers['content-type'] || 'application/octet-stream');
      const blob = new Blob([res.data], { type: contentType });
      const disposition = String(res.headers['content-disposition'] || '');
      const match = disposition.match(/filename\*=UTF-8''([^;]+)/);
      const fallbackName = `manuscript.${exportCfg.format}`;
      const filename = match ? decodeURIComponent(match[1]) : fallbackName;
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      message.success('导出完成');
      setExportModalOpen(false);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e.message || '导出失败');
    }
    setExporting(false);
  };

  const openExpandModal = (vol: any) => {
    setExpandVol(vol);
    setExpandMode('arc');
    setArcExpandCfg(DEFAULT_ARC_EXPAND_CFG);
    setExpandModalOpen(true);
  };
  const openArcChapterExpandModal = (vol: any, arcIndex: number) => {
    setExpandVol(vol);
    setExpandArcIdx(arcIndex);
    setExpandMode('chapters');
    setExpandCfg({ pacing: 'medium', event_density: 'medium', expansion_scale: 'standard' });
    setExpandModalOpen(true);
  };
  const doExpand = async () => {
    if (!projectId || !expandVol) return;
    setExpandModalOpen(false);
    try {
      if (expandMode === 'arc') {
        setExpandLoading(expandVol.id);
        const res = await api.post(`/projects/${projectId}/wizard/expand-volume-arcs/${expandVol.id}`, {
          ...arcExpandCfg,
          clear_existing_chapters: Boolean(expandVol?.narrative_arcs?.length),
        });
        await pollTask(res.data.task_id, 60);
        const [vols, chs] = await Promise.all([volumeApi.list(projectId), chapterApi.list(projectId)]);
        setVolumes(vols);
        setChapters(chs);
        if (currentChapter && !chs.some((ch: any) => ch.id === currentChapter.id)) {
          setCurrentChapter(null);
          setContent('');
        }
        setExpandLoading(null);
      } else {
        setExpandLoading(`${expandVol.id}-${expandArcIdx}`);
        const res = await api.post(`/projects/${projectId}/wizard/expand-arc-chapters/${expandVol.id}`, {
          arc_index: expandArcIdx, pacing: expandCfg.pacing, event_density: expandCfg.event_density, expansion_scale: expandCfg.expansion_scale,
        });
        await pollTask(res.data.task_id, 120);
        const chs = await chapterApi.list(projectId);
        setChapters(chs);
        setExpandLoading(null);
      }
    } catch (e: any) { message.error(e.message || '失败'); setExpandLoading(null); }
  };

  const reviseVolumeArc = async (vol: any, arcIndex: number, action: string, customInstruction?: string) => {
    if (!projectId) return;
    const key = `${vol.id}-revise-${arcIndex}-${action}`;
    setExpandLoading(key);
    try {
      const res = await api.post(`/projects/${projectId}/wizard/revise-volume-arc/${vol.id}`, {
        arc_index: arcIndex,
        action,
        instruction: customInstruction || (action === '拉长'
          ? '拉长人物反应、误判、铺垫和余波，让这条弧线更适合长篇连载。'
          : action === '压缩'
            ? '删掉可省略过渡，保留核心冲突、关键转折和必要承接。'
            : '重新设计这条弧线的冲突链、质变点、伏笔计划和角色变化，保持前后承接。'),
      });
      await pollTask(res.data.task_id, 90);
      const vols = await volumeApi.list(projectId);
      setVolumes(vols);
      if (arcDetailOpen && arcDetail?.volume?.id === vol.id && arcDetail?.arcIndex === arcIndex) {
        const updatedVol = vols.find((item: any) => item.id === vol.id);
        const updatedArc = updatedVol?.narrative_arcs?.[arcIndex];
        setArcDetail(updatedArc ? {
          volume: updatedVol,
          arc: updatedArc,
          arcIndex,
          quality: arcQualityFor(updatedVol, arcIndex),
        } : null);
      }
    } catch (e: any) {
      message.error(e.message || '调整失败');
    } finally {
      setExpandLoading(null);
    }
  };

  const openAdjustOutlineModal = (vol: any, scope: 'summary_only' | 'outline', arcIndex: number | null = null) => {
    const arc = arcIndex !== null ? vol.narrative_arcs?.[arcIndex] : null;
    setAdjustVol(vol);
    setAdjustArcIndex(arcIndex);
    setAdjustScope(scope);
    setAdjustInstruction(scope === 'summary_only'
      ? '请只优化本卷故事大概/卷概要，不改卷名、卷大纲、章节数量、章节摘要、弧线结构和已写正文。概要要通俗清楚，突出本卷主线目标、主要阻力、关键转折、爽点/悬念和结尾钩子，避免文学化空话。'
      : arc
        ? `请根据已写章节调整「${arc.name}」这条弧线后续大纲，保持已写正文不变，重点修正后续章节的因果、节奏、爽点和章末钩子。不要因为同一场景跨章节就建议合并章节。`
        : '请根据已写章节调整本卷后续大纲，保持已写正文不变，重点修正卷概要、后续弧线、章节蓝图和承接关系。不要因为同一场景跨章节就建议合并章节。');
    setAdjustMessages([{
      role: 'assistant',
      content: scope === 'summary_only'
        ? '你可以直接说想怎么改故事大概，比如“太绕了，改成网文式”“把本卷目标和反派压力写清楚”“前20万字要更抓人”。我会把这些整理成最终调整要求。'
        : '你可以像和责编沟通一样说问题，比如“这卷太散”“主角目标不强”“前十章缺爽点”“不要合并章节，只重排章节功能”。我会先整理要求，不会立刻改库。',
    }]);
    setAdjustChatInput('');
    setAdjustBackendOutdated(false);
    setAdjustModalOpen(true);
  };

  const sendAdjustChatMessage = async (textOverride?: string) => {
    if (!projectId || !adjustVol || adjustChatLoading) return;
    const text = (textOverride ?? adjustChatInput).trim();
    if (!text) return;
    const nextMessages = [...adjustMessages, { role: 'user' as const, content: text }];
    setAdjustMessages(nextMessages);
    if (!textOverride) setAdjustChatInput('');
    setAdjustChatLoading(true);
    const key = 'adjust-outline-chat';
    try {
      const res = await api.post(`/projects/${projectId}/wizard/adjust-outline-chat/${adjustVol.id}`, {
        messages: nextMessages,
        arc_index: adjustArcIndex,
        adjust_scope: adjustScope,
      });
      message.loading({ content: 'AI 正在整理你的调整意见…', key, duration: 0 });
      const result = await pollTask(res.data.task_id, 60, key);
      setAdjustMessages([
        ...nextMessages,
        { role: 'assistant', content: result?.assistant_reply || '我已经整理好这次调整方向，可以继续补充，也可以直接开始调整。' },
      ]);
      if (result?.consolidated_instruction) {
        setAdjustInstruction(result.consolidated_instruction);
      }
      message.success({ content: '调整意见已整理', key });
    } catch (e: any) {
      if (e?.response?.status === 404) {
        setAdjustBackendOutdated(true);
        const fallback = `${adjustInstruction.trim()}\n\n补充调整意见：${text}`.trim();
        setAdjustInstruction(fallback);
        setAdjustMessages([
          ...nextMessages,
          { role: 'assistant', content: '当前后端还没加载对话整理接口，我先把你的意见追加到最终调整要求里。你可以继续补充，或直接点“开始调整”。' },
        ]);
        message.warning({ content: '对话接口未加载，已先追加到最终调整要求', key });
      } else {
        setAdjustMessages(adjustMessages);
        message.error({ content: e.message || '对话失败', key });
      }
    } finally {
      setAdjustChatLoading(false);
    }
  };

  const doAdjustOutline = async () => {
    if (!projectId || !adjustVol || !adjustInstruction.trim()) return;
    if (adjustScope === 'summary_only' && adjustBackendOutdated) {
      message.error('后端还没加载“只改故事大概”的保护接口，为避免误改弧线/章节，先不要执行落库调整。');
      return;
    }
    setAdjustingOutline(true);
    const key = adjustScope === 'summary_only' ? 'adjust-volume-summary' : 'adjust-outline';
    try {
      const res = await api.post(`/projects/${projectId}/wizard/adjust-outline/${adjustVol.id}`, {
        instruction: adjustInstruction,
        arc_index: adjustArcIndex,
        adjust_scope: adjustScope,
        apply: true,
      });
      message.loading({
        content: adjustScope === 'summary_only' ? 'AI 正在调整卷故事大概…' : 'AI 正在调整本卷大纲…',
        key,
        duration: 0,
      });
      const result = await pollTask(res.data.task_id, 120, key);
      const [vols, chs] = await Promise.all([volumeApi.list(projectId), chapterApi.list(projectId)]);
      setVolumes(vols);
      setChapters(chs);
      setAdjustModalOpen(false);
      const warnings = result?.warnings?.length ? `，提示 ${result.warnings.length} 条` : '';
      message.success({
        content: adjustScope === 'summary_only' ? `故事大概已调整${warnings}` : `本卷大纲已调整${warnings}`,
        key,
      });
    } catch (e: any) {
      message.error({ content: e.message || '调整失败', key });
    } finally {
      setAdjustingOutline(false);
    }
  };

  const deleteVolume = async (v: any) => {
    if (!projectId) return;
    try { await volumeApi.remove(projectId, v.id); setVolumes(volumes.filter(x => x.id !== v.id)); } catch { message.error('删除失败'); }
  };

  const deleteChapter = async (ch: any) => {
    if (!projectId) return;
    try { await api.delete(`/projects/${projectId}/chapters/${ch.id}`); setChapters(chapters.filter(x => x.id !== ch.id)); } catch { message.error('删除失败'); }
  };

  const createChapter = (vol: any, afterNum: number) => {
    if (!projectId) return;
    api.post(`/projects/${projectId}/chapters`, {
      volume_id: vol.id, chapter_number: afterNum, title: `第${afterNum}章`,
      arc_name: '', target_words: 3500,
    }).then((r: any) => {
      setChapters([...chapters, r.data.chapter]);
      selectChapter(r.data.chapter);
    }).catch(() => message.error('创建失败'));
  };

  const currentVolume = currentChapter ? volumes.find((v: any) => v.id === currentChapter.volume_id) : null;
  const currentChapterGate = chapterGate(currentChapter);
  const detailArc = arcDetail?.arc;
  const detailVolume = arcDetail?.volume;
  const detailArcIndex = arcDetail?.arcIndex ?? 0;
  const detailQuality = arcDetail?.quality || (detailVolume ? arcQualityFor(detailVolume, detailArcIndex) : null);
  const detailChecks = detailArc ? arcQualityChecks(detailArc, detailArcIndex, detailQuality) : [];
  const detailStatus = arcQualityStatus(detailQuality, detailChecks);
  const detailIssues = arcQualityIssues(detailQuality);
  const detailWarnings = arcQualityWarnings(detailQuality);
  const detailHasStructuralGaps = arcHasStructuralGaps(detailQuality, detailChecks);
  const detailArcChapters = detailArc ? chapters.filter((c: any) => c.volume_id === detailVolume?.id && c.arc_name === detailArc.name) : [];

  if (loading) return <div style={{ padding: 80, textAlign: 'center' }}><Spin size="large" /></div>;

  return (
    <div className={`workbench ${isFullscreen ? 'fullscreen' : ''}`}>
      <header className="workbench-topbar">
        <div className="workbench-project">
          <Link to="/dashboard" className="workbench-back"><LeftOutlined /> 返回项目</Link>
          <div className="workbench-titleblock">
            <div className="workbench-title">{project?.title || '未命名项目'}</div>
            <div className="workbench-subtitle">
              {project?.genre || '未分类'} · {chapters.length} 章 · 目标 {Math.round((project?.target_total_words || 0) / 10000) || '--'} 万字
            </div>
          </div>
        </div>
        <nav className="workbench-nav">
          <Button size="small" icon={<EditOutlined />} onClick={openProjectInfo}>项目信息</Button>
          <Link to={`/projects/${projectId}/characters`}><Button size="small" icon={<TeamOutlined />}>角色</Button></Link>
          <Link to={`/projects/${projectId}/factions`}><Button size="small" icon={<ApartmentOutlined />}>势力</Button></Link>
          <Link to={`/projects/${projectId}/world-setting`}><Button size="small" icon={<EnvironmentOutlined />}>世界观</Button></Link>
          <Link to={`/projects/${projectId}/outline`}><Button size="small" icon={<BookOutlined />}>大纲</Button></Link>
          <Link to={`/projects/${projectId}/narrative-graph`}><Button size="small" icon={<BranchesOutlined />}>故事线</Button></Link>
          <Link to={`/projects/${projectId}/memory-center`}><Button size="small" icon={<DatabaseOutlined />}>记忆中枢</Button></Link>
          <Link to={`/projects/${projectId}/story-graph`}><Button size="small" icon={<NodeIndexOutlined />}>叙事图谱</Button></Link>
          <Link to={`/projects/${projectId}/landscape`}><Button size="small" icon={<EnvironmentOutlined />}>小说景观</Button></Link>
          <Link to={`/projects/${projectId}/quality-dashboard`}><Button size="small" icon={<BarChartOutlined />}>质量</Button></Link>
          <Button size="small" icon={<FileSearchOutlined />} onClick={() => openSystemDrawer('health')}>系统诊断</Button>
          <Button size="small" icon={<DownloadOutlined />} onClick={openExportModal}>导出</Button>
          <Badge count={tasks.filter(t => t.status === 'running').length} size="small">
            <Button size="small" onClick={() => { refreshTasks(); setTaskDrawerOpen(true); }}>任务</Button>
          </Badge>
        </nav>
      </header>

      <main className="workbench-body">
        {!isFullscreen && (
          <aside className="workbench-panel workbench-left">
            <div className="panel-head">
              <div className="panel-title">目录</div>
              <div className="panel-desc">按卷、弧线和章节组织正文</div>
            </div>
            <div className="outline-scroll">
              {volumes.map((v: any) => {
                const volChs = chapters.filter((c: any) => c.volume_id === v.id);
                const arcs = v.narrative_arcs || [];
                const isExpanded = expandedVolume === v.id;

                return (
                  <section key={v.id} className={`volume-card ${isExpanded ? 'active' : ''}`}>
                    <button className="volume-row" onClick={() => setExpandedVolume(isExpanded ? null : v.id)}>
                      <span className="volume-main">
                        <span className="volume-name">{isExpanded ? '▾' : '▸'} 卷{v.volume_number} · {v.title || '未命名卷'}</span>
                        {v.summary && <span className="volume-summary">{v.summary}</span>}
                      </span>
                      <span className="volume-meta">
                        <Tag>{volChs.length}章</Tag>
                        <Popconfirm title="删除？" onConfirm={() => deleteVolume(v)}>
                          <Button size="small" type="text" danger icon={<DeleteOutlined />} />
                        </Popconfirm>
                      </span>
                    </button>

                    {isExpanded && (
                      <div className="volume-body">
                        <div className="volume-overview-box">
                          <div className="volume-overview-head">
                            <Text strong>故事大概</Text>
                            <Space size={4} wrap>
                              <Button
                                size="small"
                                type="link"
                                icon={<ThunderboltOutlined />}
                                loading={adjustingOutline && adjustVol?.id === v.id && adjustScope === 'summary_only'}
                                onClick={() => openAdjustOutlineModal(v, 'summary_only')}
                              >
                                AI调整故事大概
                              </Button>
                              <Button
                                size="small"
                                type="link"
                                icon={<BranchesOutlined />}
                                loading={adjustingOutline && adjustVol?.id === v.id && adjustScope === 'outline'}
                                onClick={() => openAdjustOutlineModal(v, 'outline')}
                              >
                                AI调整本卷
                              </Button>
                              <Button
                                size="small"
                                type="link"
                                icon={<FileSearchOutlined />}
                                onClick={() => {
                                  setSystemDrawerOpen(true);
                                  setSystemTab('context');
                                  api.get(`/projects/${projectId}/wizard/context-preview`, { params: { volume_id: v.id } })
                                    .then((res) => setContextPreview(res.data))
                                    .catch((e) => message.error(e?.response?.data?.detail || e.message || '上下文预览失败'));
                                }}
                              >
                                上下文
                              </Button>
                            </Space>
                          </div>
                          <Paragraph className="volume-overview-text">
                            {v.summary || '本卷还没有故事大概，可以先用「AI调整故事大概」生成一个更清楚的卷概要。'}
                          </Paragraph>
                        </div>
                        {!arcs.length ? (
                          <Button type="dashed" size="small" block icon={<ThunderboltOutlined />}
                            loading={expandLoading === v.id} onClick={() => openExpandModal(v)}>
                            展开弧线
                          </Button>
                        ) : (
                          <>
                            <div className="arc-tools">
                              <Button type="dashed" size="small" block icon={<ReloadOutlined />}
                                loading={expandLoading === v.id}
                                onClick={() => openExpandModal(v)}>
                                重拆整卷弧线
                              </Button>
                            </div>
                            {arcs.map((arc: any, ai: number) => {
                            const arcChs = volChs.filter((c: any) => c.arc_name === arc.name);
                            const arcExpanded = expandedArc === ai;
                            const quality = arcQualityFor(v, ai);
                            const qualityIssues = arcQualityIssues(quality);
                            const qualityWarnings = arcQualityWarnings(quality);
                            const qualityChecks = arcQualityChecks(arc, ai, quality);
                            const hasStructuralGaps = arcHasStructuralGaps(quality, qualityChecks);
                            const qualityStatus = arcQualityStatus(quality, qualityChecks);
                            return (
                              <div key={ai} className="arc-block">
                                <button className={`arc-row ${arcExpanded ? 'active' : ''}`} onClick={() => setExpandedArc(arcExpanded ? null : ai)}>
                                  <span className="arc-main">
                                    <span className="arc-name">{arcExpanded ? '▾' : '▸'} {arc.name}</span>
                                    <span className="arc-subline">
                                      {arc.narrative_function || '叙事功能未定'} · 第{arc.chapter_start || '?'}-{arc.chapter_end || '?'}章
                                    </span>
                                  </span>
                                  <Space size={4}>
                                    {quality && <Tag color={qualityStatus.color}>{qualityStatus.label}</Tag>}
                                    <Tag>{arcChs.length || arc.chapter_count || 0}章</Tag>
                                  </Space>
                                </button>

                                {arcExpanded && (
                                  <div className="chapter-list">
                                    <div className="arc-detail">
                                      {quality && (
                                        <div className="arc-quality-panel">
                                          <div className="arc-quality-head">
                                            <Space size={6} wrap>
                                              <Tag color={qualityStatus.color}>{qualityStatus.label}</Tag>
                                              <Text type="secondary">这是结构连续性分，不是剧情质量分；80 分以上通常可继续展开章节。</Text>
                                            </Space>
                                          </div>
                                          <div className="arc-quality-grid">
                                            {qualityChecks.map((item) => (
                                              <div key={item.key} className={`arc-quality-check ${item.failed ? 'bad' : item.warning ? 'warn' : 'ok'}`}>
                                                <span>{item.failed ? '缺' : item.warning ? '提' : '✓'}</span>
                                                <div>
                                                  <Text strong>{item.label}</Text>
                                                  <Text type="secondary">{item.help}</Text>
                                                </div>
                                              </div>
                                            ))}
                                          </div>
                                        </div>
                                      )}
                                      {hasStructuralGaps && (
                                        <Alert
                                          type="warning"
                                          showIcon
                                          style={{ marginBottom: 8 }}
                                          message="结构缺口需要修复"
                                          description={(
                                            <div>
                                              <div style={{ marginBottom: 8 }}>
                                                {qualityIssues.map((x: any, idx: number) => (
                                                  <Tag key={idx} color="orange" style={{ marginBottom: 4 }}>
                                                    {x.field ? `${x.field}：` : ''}{x.issue || x.description || '连续性风险'}
                                                  </Tag>
                                                ))}
                                                {qualityChecks.filter((x: any) => x.failed).map((x: any) => (
                                                  <Tag key={`missing-${x.key}`} color="orange" style={{ marginBottom: 4 }}>
                                                    缺少{x.label}
                                                  </Tag>
                                                ))}
                                                {qualityIssues.length === 0 && !qualityChecks.some((x: any) => x.failed) && '这条弧线可能缺少清晰交接、变化台阶或因果链。'}
                                              </div>
                                              <Space size={8} wrap>
                                                <Button
                                                  size="small"
                                                  type="primary"
                                                  loading={expandLoading === `${v.id}-revise-${ai}-修复连续性`}
                                                  onClick={(e) => {
                                                    e.stopPropagation();
                                                    reviseVolumeArc(v, ai, '修复连续性', arcContinuityRepairInstruction(quality, arc, qualityChecks));
                                                  }}
                                                >
                                                  按连续性修复
                                                </Button>
                                                <Text type="secondary">修复后会重新计算弧线质量，再决定是否适合展开章节。</Text>
                                              </Space>
                                            </div>
                                          )}
                                        />
                                      )}
                                      {quality && !hasStructuralGaps && qualityWarnings.length > 0 && (
                                        <Alert
                                          type="info"
                                          showIcon
                                          style={{ marginBottom: 8 }}
                                          message="交接提醒，不阻止展开章节"
                                          description={(
                                            <div>
                                              <div style={{ marginBottom: 8 }}>
                                                {qualityWarnings.map((x: any, idx: number) => (
                                                  <Tag key={idx} color="blue" style={{ marginBottom: 4 }}>
                                                    {x.field ? `${x.field}：` : ''}{x.issue || x.description || '交接提醒'}
                                                  </Tag>
                                                ))}
                                              </div>
                                              <Button
                                                size="small"
                                                loading={expandLoading === `${v.id}-revise-${ai}-优化交接`}
                                                onClick={(e) => {
                                                  e.stopPropagation();
                                                  reviseVolumeArc(v, ai, '优化交接', arcHandoffPolishInstruction(quality, arc));
                                                }}
                                              >
                                                优化交接
                                              </Button>
                                            </div>
                                          )}
                                        />
                                      )}
                                      <div className="arc-actionbar">
                                        <Button size="small" type="link" icon={<FileSearchOutlined />} onClick={() => openArcDetail(v, arc, ai, quality)}>详情</Button>
                                        <Button size="small" type="link" loading={expandLoading === `${v.id}-revise-${ai}-重写`} onClick={() => reviseVolumeArc(v, ai, '重写')}>重写</Button>
                                        <Button size="small" type="link" loading={expandLoading === `${v.id}-revise-${ai}-拉长`} onClick={() => reviseVolumeArc(v, ai, '拉长')}>拉长</Button>
                                        <Button size="small" type="link" loading={expandLoading === `${v.id}-revise-${ai}-压缩`} onClick={() => reviseVolumeArc(v, ai, '压缩')}>压缩</Button>
                                      </div>
                                      <div className="arc-tags">
                                        {arc.narrative_function && <Tag color="blue">{arc.narrative_function}</Tag>}
                                        {arc.emotional_color && <Tag color="purple">{arc.emotional_color}</Tag>}
                                        {arc.tension_curve && <Tag>{arc.tension_curve}</Tag>}
                                      </div>
                                      {arc.description && <Paragraph className="arc-desc">{arc.description}</Paragraph>}
                                      <div className="arc-memory-grid">
                                        {arc.opening_state && <div><Text strong>开局</Text><span>{arc.opening_state}</span></div>}
                                        {arc.ending_state && <div><Text strong>终点</Text><span>{arc.ending_state}</span></div>}
                                        {arc.irreplaceable_value && <div><Text strong>不可替代</Text><span>{arc.irreplaceable_value}</span></div>}
                                        {arc.protagonist_change && <div><Text strong>主角变化</Text><span>{arc.protagonist_change}</span></div>}
                                        {arc.dependence_on_previous && <div><Text strong>上承</Text><span>{arc.dependence_on_previous}</span></div>}
                                        {arc.payoff_for_next && <div><Text strong>下启</Text><span>{arc.payoff_for_next}</span></div>}
                                      </div>
                                      {Array.isArray(arc.character_focus) && arc.character_focus.length > 0 && (
                                        <div className="arc-listline">
                                          <Text strong>重点角色</Text>
                                          <Space size={[4, 4]} wrap>{arc.character_focus.map((x: any, i: number) => <Tag key={i}>{typeof x === 'string' ? x : `${x.name || x.character || '角色'}：${x.function || x.role || ''}`}</Tag>)}</Space>
                                        </div>
                                      )}
                                      {Array.isArray(arc.foreshadowing_plan) && arc.foreshadowing_plan.length > 0 && (
                                        <div className="arc-listline">
                                          <Text strong>伏笔计划</Text>
                                          <div className="arc-bullets">
                                            {arc.foreshadowing_plan.slice(0, 5).map((x: any, i: number) => (
                                              <span key={i}>{typeof x === 'string' ? x : `${x.name || x.type || '伏笔'}：${x.detail || x.description || x.action || ''}`}</span>
                                            ))}
                                          </div>
                                        </div>
                                      )}
                                    </div>
                                    {!arcChs.length ? (
                                      <Button type="link" size="small" icon={<ThunderboltOutlined />}
                                        loading={expandLoading === `${v.id}-${ai}`}
                                        onClick={() => openArcChapterExpandModal(v, ai)}>
                                        展开章节
                                      </Button>
                                    ) : (
                                      <>
                                        <div className="arc-tools">
                                          <Button type="link" size="small" icon={<ThunderboltOutlined />}
                                            loading={expandLoading === `${v.id}-batch-${ai}`}
                                            onClick={() => { setBatchVolume(v); setBatchArcIdx(ai); setBatchModalOpen(true); }}>批量写</Button>
                                          <Button type="link" size="small" icon={<AuditOutlined />}
                                            loading={reviewing} onClick={() => reviewArc(v, ai)}>评审</Button>
                                        </div>
                                        {arcChs.map((ch: any) => (
                                          <button key={ch.id} className={`chapter-row ${currentChapter?.id === ch.id ? 'current' : ''}`} onClick={() => selectChapter(ch)}>
                                            <span className="chapter-main">
                                              <span className="chapter-name">第{ch.chapter_number}章 {ch.title || ''}</span>
                                            </span>
                                            <Popconfirm title="删除？" onConfirm={(e: any) => { e.stopPropagation(); deleteChapter(ch); }}>
                                              <Button size="small" type="text" danger icon={<DeleteOutlined />} />
                                            </Popconfirm>
                                          </button>
                                        ))}
                                      </>
                                    )}
                                  </div>
                                )}
                              </div>
                            );
                            })}
                          </>
                        )}
                      </div>
                    )}
                  </section>
                );
              })}
            </div>
          </aside>
        )}

        <section className="workbench-panel editor-shell">
          {currentChapter ? (
            <>
              {isFullscreen ? (
                <div style={{ padding: '6px 24px', borderBottom: '1px solid #f0f0f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
                  <Text style={{ fontSize: 13, color: '#8c8c8c' }}>第{currentChapter.chapter_number}章 · {currentChapter.title} · 字数{content.length}</Text>
                  <Button size="small" icon={<FullscreenExitOutlined />} onClick={() => setIsFullscreen(false)}>退出全屏</Button>
                </div>
              ) : (
                <div className="chapter-toolbar">
                <div>
                  <div className="chapter-kicker">{currentVolume?.title || '未分卷'} / 第{currentChapter.chapter_number}章</div>
                  <div className="chapter-title">{currentChapter.title || '未命名章节'}</div>
                  {currentChapterGate && currentChapterGate.passed === false && (
                    <Alert
                      type="warning"
                      showIcon
                      style={{ marginTop: 6, marginBottom: 6, padding: '6px 10px' }}
                      message={`蓝图风险：${(currentChapterGate.issues || []).join('；') || '需要检查上承下接和状态增量'}`}
                    />
                  )}
                  {currentChapter.connects_from && (
                    <div style={{ fontSize: 11, color: '#8c8c8c', borderLeft: '2px solid #1677ff', paddingLeft: 8, marginTop: 2 }}>
                      📥 {currentChapter.connects_from}
                    </div>
                  )}
                  {currentChapter.summary && (
                    <details style={{ marginTop: 4 }}>
                      <summary style={{ fontSize: 12, color: '#1677ff', cursor: 'pointer' }}>📝 场景蓝图</summary>
                      <div style={{ fontSize: 12, whiteSpace: 'pre-wrap', color: '#595959', marginTop: 4, lineHeight: 1.7, maxHeight: 300, overflow: 'auto' }}>
                        {currentChapter.summary}
                      </div>
                    </details>
                  )}
                  {currentChapter.connects_to && (
                    <div style={{ fontSize: 11, color: '#8c8c8c', borderLeft: '2px solid #fa8c16', paddingLeft: 8, marginTop: 2 }}>
                      📤 {currentChapter.connects_to}
                    </div>
                  )}
                </div>
                <div className="chapter-actions">
                  <Button size="small" icon={isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
                    onClick={() => setIsFullscreen(!isFullscreen)} />
                  <Select
                    size="small"
                    value={readabilityMode}
                    onChange={setReadabilityMode}
                    options={READABILITY_OPTIONS}
                    style={{ width: 104 }}
                  />
                  <Button size="small" type="primary" icon={<ThunderboltOutlined />} onClick={aiWriteChapter} loading={writing}>写本章</Button>
                  <Button size="small" icon={<EditOutlined />} onClick={() => setWritingSettingsOpen(true)}>写作设置</Button>
                  <Button size="small" icon={<WarningOutlined />} onClick={openImpactAnalysis}>影响分析</Button>
                  <Space.Compact size="small">
                    {OPTIMIZE_ACTIONS.map((action) => (
                      <Button
                        key={action.mode}
                        size="small"
                        loading={optimizingMode === action.mode}
                        disabled={!!optimizingMode || !content}
                        onClick={() => optimizeChapter(action.mode)}
                      >
                        {action.label}
                      </Button>
                    ))}
                  </Space.Compact>
                  <Popconfirm title="将当前长章节按约3500-4000字拆成多章，继续吗？" onConfirm={smartSplitChapter}>
                    <Button size="small" icon={<ScissorOutlined />} loading={splittingChapter} disabled={content.length < 5400}>智能拆分</Button>
                  </Popconfirm>
                  <Button size="small" icon={<AuditOutlined />} onClick={auditChapter} loading={auditing}>{auditResult ? '查看' : '审计'}</Button>
                  {!isFullscreen && <Button size="small" icon={<HistoryOutlined />}>版本</Button>}
                  {!isFullscreen && <Button size="small" icon={<BranchesOutlined />}>记忆</Button>}
                  {!isFullscreen && currentVolume && <Button size="small" onClick={() => createChapter(currentVolume, (currentChapter?.chapter_number || 0) + 1)}>补章</Button>}
                  {!isFullscreen && <Button size="small" onClick={() => setRightPanelOpen(!rightPanelOpen)}>{rightPanelOpen ? '收起参考' : '打开参考'}</Button>}
                </div>
              </div>
              )}

              <div className="paper-stage">
                <div className="paper">
                  <Input.TextArea
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    onBlur={saveContent}
                    placeholder="在此写作，或点击右上角「写本章」生成正文..."
                    autoSize={{ minRows: isFullscreen ? 40 : 22 }}
                  style={isFullscreen ? { border: 'none', resize: 'none', fontSize: 18, lineHeight: 2.2, fontFamily: "'思源宋体', serif", background: '#fff', width: '100%', height: 'calc(100vh - 80px)' } : {}}
                  />
                </div>
              </div>

              {!isFullscreen && (
              <div className="statusbar">
                <span>字数：{content.length} / {currentChapter.target_words || 3500}</span>
                <span>质量：{currentChapter.quality_score ? `${currentChapter.quality_score}/10` : '未评分'}</span>
                <span>
                  第{currentChapter.chapter_number}章 · {
                    saveState === 'saving' ? '保存中…' :
                    saveState === 'dirty' ? '未保存修改' :
                    saveState === 'error' ? '保存失败' : '已保存'
                  }
                </span>
              </div>
              )}

              {!isFullscreen && auditResult && (
                <div className={`audit-strip ${auditResult.passed ? 'ok' : 'warn'}`}>
                  <div className="audit-title-row">
                    <div className="audit-title">审计{auditResult.passed ? '通过' : '未通过'} · 评分 {auditResult.overall_score}/10</div>
                    <div className="audit-title-actions">
                      <Button
                        size="small"
                        disabled={!!optimizingMode || !!issueRepairingKey}
                        loading={optimizingMode === 'audit-light'}
                        onClick={() => reviseByAudit('quality_light_fix')}
                      >
                        按审计轻修
                      </Button>
                      <Popconfirm
                        title="按审计重写会覆盖当前章节正文，系统会先保存版本备份。继续吗？"
                        onConfirm={() => reviseByAudit('audit_full_rewrite')}
                      >
                        <Button
                          size="small"
                          danger
                          disabled={!!optimizingMode || !!issueRepairingKey}
                          loading={optimizingMode === 'audit-rewrite'}
                        >
                          按审计重写
                        </Button>
                      </Popconfirm>
                    </div>
                  </div>
                  {auditResult.highlights?.length > 0 && (
                    <Text type="success" style={{ fontSize: 11, display: 'block' }}>亮点：{auditResult.highlights.join('；')}</Text>
                  )}
                  {auditResult.issues?.map((issue: any, i: number) => {
                    const severity = AUDIT_SEVERITY_LABELS[issue.severity] || { label: issue.severity || '问题', color: 'default' };
                    const target = extractAuditTargetText(issue, content);
                    const canRepair = !!target && content.includes(target);
                    const preferredScope = issue.fix_mode === 'paragraph' || issue.fix_mode === 'context' ? issue.fix_mode : 'sentence';
                    return (
                      <div key={i} className="audit-issue">
                        <div className="audit-issue-main">
                          <div className="audit-issue-head">
                            <Tag color={severity.color}>{severity.label}</Tag>
                            <Text strong style={{ fontSize: 11 }}>{issue.dimension}</Text>
                          </div>
                          <Text style={{ fontSize: 11 }}>{issue.description}</Text>
                          {target && (
                            <div className={`audit-target ${canRepair ? '' : 'missing'}`}>
                              定位：{target}
                            </div>
                          )}
                          {issue.fix_suggestion && (
                            <Text type="secondary" style={{ fontSize: 11 }}>建议：{issue.fix_suggestion}</Text>
                          )}
                        </div>
                        <div className="audit-issue-actions">
                          <Button
                            size="small"
                            disabled={!canRepair || !!issueRepairingKey}
                            loading={issueRepairingKey === `${i}-sentence`}
                            onClick={() => repairAuditIssue(issue, 'sentence', i)}
                          >
                            只修原句
                          </Button>
                          <Button
                            size="small"
                            disabled={!canRepair || !!issueRepairingKey}
                            loading={issueRepairingKey === `${i}-paragraph`}
                            onClick={() => repairAuditIssue(issue, preferredScope === 'context' ? 'context' : 'paragraph', i)}
                          >
                            {preferredScope === 'context' ? '修局部' : '修这一段'}
                          </Button>
                          <Button
                            size="small"
                            disabled={!canRepair || !!issueRepairingKey}
                            loading={issueRepairingKey === `${i}-context`}
                            onClick={() => repairAuditIssue(issue, 'context', i)}
                          >
                            深修此问题
                          </Button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          ) : (
            <Empty className="empty-editor" description="选择左侧章节开始写作" />
          )}
        </section>

        {!isFullscreen && rightPanelOpen && (
          <aside className="workbench-panel workbench-right">
            <div className="panel-head">
              <div className="panel-title">写作参考</div>
              <div className="panel-desc">当前项目的角色、势力和大纲</div>
            </div>
            <Tabs className="reference-tabs" activeKey={rightTab} onChange={setRightTab} size="small"
              items={[
                {
                  key: 'characters', label: <span><TeamOutlined /> 角色</span>,
                  children: <div className="reference-scroll">
                    {rightData.characters.length === 0
                      ? <Empty description="无角色" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                      : rightData.characters.map((c: any, i: number) => (
                          <Card key={i} size="small" className="reference-card">
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                              <Text strong style={{ fontSize: 12 }}>{c.name}</Text>
                              <div style={{ display: 'flex', gap: 2 }}>
                                {c.character_class === 'one_off' && <Tag style={{ fontSize: 9, lineHeight: '14px' }} color="default">路人</Tag>}
                                <Tag style={{ fontSize: 9 }}>{translateRole(c.role_type)}</Tag>
                              </div>
                            </div>
                            {c.first_appeared_chapter && <Text type="secondary" style={{ fontSize: 10, display: 'block' }}>首出场：第{c.first_appeared_chapter}章</Text>}
                            {c.personality && <Text style={{ fontSize: 11, display: 'block', color: '#595959' }}>{c.personality?.slice(0, 70)}</Text>}
                            {c.inner_conflict && <Text style={{ fontSize: 11, display: 'block', color: '#b45309' }}>{c.inner_conflict?.slice(0, 48)}</Text>}
                          </Card>
                        ))}
                  </div>,
                },
                {
                  key: 'factions', label: <span><ApartmentOutlined /> 势力</span>,
                  children: <div className="reference-scroll">
                    {rightData.factions.length === 0
                      ? <Empty description="无势力" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                      : rightData.factions.map((f: any, i: number) => (
                          <Card key={i} size="small" className="reference-card">
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                              <Text strong style={{ fontSize: 12 }}>{f.name}</Text>
                              <Tag style={{ fontSize: 9 }} color={factionTypeColor(f.faction_type)}>
                                {translateFactionType(f.faction_type)}
                              </Tag>
                            </div>
                            {f.description && <Text style={{ fontSize: 11, color: '#595959' }}>{f.description?.slice(0, 72)}</Text>}
                          </Card>
                        ))}
                  </div>,
                },
                {
                  key: 'outline', label: <span><BookOutlined /> 大纲</span>,
                  children: <div className="reference-scroll">
                    {volumes.length === 0
                      ? <Empty description="无大纲" />
                      : volumes.map((v: any) => (
                          <Card key={v.id} size="small" className="reference-card">
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                              <Text strong style={{ fontSize: 12 }}>卷{v.volume_number} · {v.title}</Text>
                              <Tag style={{ fontSize: 10 }}>{(v.target_words / 10000).toFixed(1)}万字</Tag>
                            </div>
                            {v.theme && <Text style={{ fontSize: 11, display: 'block', color: '#1677ff' }}>🎯 {v.theme}</Text>}
                            {v.emotional_arc_description && <Text style={{ fontSize: 11, display: 'block', color: '#8c8c8c' }}>📈 {v.emotional_arc_description}</Text>}
                            {v.outline && (
                              <details style={{ marginTop: 4 }}>
                                <summary style={{ fontSize: 11, color: '#1677ff', cursor: 'pointer' }}>📝 大纲</summary>
                                <Paragraph style={{ fontSize: 11, color: '#595959', margin: 4, whiteSpace: 'pre-wrap', lineHeight: 1.6, maxHeight: 400, overflow: 'auto' }}>{v.outline}</Paragraph>
                              </details>
                            )}
                          </Card>
                        ))}
                  </div>,
                },
              ]}
            />
          </aside>
        )}
      </main>

      {/* Adjust Outline Modal */}
      <Modal
        title={adjustScope === 'summary_only'
          ? `AI调整故事大概 · ${adjustVol?.title || ''}`
          : adjustArcIndex !== null
            ? `AI调整弧线 · ${adjustVol?.narrative_arcs?.[adjustArcIndex]?.name || ''}`
            : `AI调整本卷 · ${adjustVol?.title || ''}`}
        open={adjustModalOpen}
        onOk={doAdjustOutline}
        onCancel={() => setAdjustModalOpen(false)}
        okText="开始调整"
        confirmLoading={adjustingOutline}
        width={920}
      >
        <Alert
          type={adjustScope === 'summary_only' ? 'info' : 'warning'}
          showIcon
          style={{ marginBottom: 12 }}
          message={adjustScope === 'summary_only' ? '只调整卷故事大概' : '不会覆盖已写正文'}
          description={adjustScope === 'summary_only'
            ? '这个入口只会保存卷概要字段，不会改章节正文、章节数量、弧线和章节蓝图。'
            : 'AI 会读取已写章节作为事实，只调整卷大纲、弧线、章节摘要和蓝图。已经写出的正文内容不会被改动。'}
        />
        <div className="adjust-dialog-grid">
          <div className="adjust-chat-pane">
            <div className="adjust-pane-title">对话沟通</div>
            <div className="adjust-chat-list">
              {adjustMessages.map((m, idx) => (
                <div key={idx} className={`adjust-chat-msg ${m.role}`}>
                  <span>{m.role === 'user' ? '你' : 'AI'}</span>
                  <p>{m.content}</p>
                </div>
              ))}
            </div>
            <Space size={[6, 6]} wrap className="adjust-quick-row">
              {[
                '太文艺了，改得通俗易懂一点',
                '前20万字要更抓人',
                '主角目标和反派压力写清楚',
              ].map((text) => (
                <Button key={text} size="small" onClick={() => sendAdjustChatMessage(text)} disabled={adjustChatLoading}>{text}</Button>
              ))}
            </Space>
            <div className="adjust-chat-input">
              <Input.TextArea
                value={adjustChatInput}
                onChange={(e) => setAdjustChatInput(e.target.value)}
                autoSize={{ minRows: 2, maxRows: 4 }}
                placeholder="直接说你的感觉，比如：这卷太散，缺少让读者追下去的目标和压力。"
                onPressEnter={(e) => {
                  if ((e.metaKey || e.ctrlKey) && adjustChatInput.trim()) {
                    e.preventDefault();
                    sendAdjustChatMessage();
                  }
                }}
              />
              <Button
                type="primary"
                icon={<SendOutlined />}
                loading={adjustChatLoading}
                disabled={!adjustChatInput.trim()}
                onClick={() => sendAdjustChatMessage()}
              >
                发送
              </Button>
            </div>
          </div>
          <div className="adjust-instruction-pane">
            <div className="adjust-pane-title">最终调整要求</div>
            <Text type="secondary" style={{ fontSize: 12 }}>
              这里会随着对话自动整理；你也可以手动改，点击“开始调整”才会真正写入。
            </Text>
            <Input.TextArea
              value={adjustInstruction}
              onChange={(e) => setAdjustInstruction(e.target.value)}
              rows={10}
              autoSize={{ minRows: 10, maxRows: 16 }}
              style={{ marginTop: 8, lineHeight: 1.8 }}
              placeholder="例如：写得太文艺了，改成网文式、通俗清楚、主线目标明确，突出冲突、爽点和结尾钩子。"
            />
          </div>
        </div>
      </Modal>

      {/* Expand Modal */}
      <Modal
        title={expandMode === 'arc'
          ? `${expandVol?.narrative_arcs?.length ? '重拆整卷弧线' : '展开弧线'} · ${expandVol?.title || ''}`
          : `展开章节 · ${expandVol?.narrative_arcs?.[expandArcIdx]?.name || ''}`}
        open={expandModalOpen} onOk={doExpand} onCancel={() => setExpandModalOpen(false)} okText="生成" width={expandMode === 'arc' ? 640 : 440}>
        {expandMode === 'arc' ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginTop: 8 }}>
            <Alert
              type={expandVol?.narrative_arcs?.length ? 'warning' : 'info'}
              showIcon
              message={expandVol?.narrative_arcs?.length ? '将重新拆分本卷弧线规划' : '系统会按策略自动决定弧线数量，不需要你填具体章节。'}
              description={expandVol?.narrative_arcs?.length
                ? '会覆盖当前卷下面的弧线设定；已写出的章节正文不会在这里直接删除。新弧线确定后，可继续展开章节。'
                : '生成时会要求每条弧线写清开局、终点、不可替代价值、主角变化、重点角色和伏笔计划。'}
            />
            <div>
              <Text strong style={{ fontSize: 13 }}>弧线策略</Text>
              <Radio.Group value={arcExpandCfg.arc_strategy} onChange={(e) => setArcExpandCfg({ ...arcExpandCfg, arc_strategy: e.target.value })}
                style={{ display: 'flex', gap: 8, marginTop: 6, flexWrap: 'wrap' }} size="small" buttonStyle="solid">
                {ARC_STRATEGY_OPTIONS.map(opt => <Radio.Button key={opt.value} value={opt.value}>{opt.label}</Radio.Button>)}
              </Radio.Group>
            </div>
            <div>
              <Text strong style={{ fontSize: 13 }}>弧线密度</Text>
              <Radio.Group value={arcExpandCfg.arc_density} onChange={(e) => setArcExpandCfg({ ...arcExpandCfg, arc_density: e.target.value })}
                style={{ display: 'flex', gap: 8, marginTop: 6, flexWrap: 'wrap' }} size="small" buttonStyle="solid">
                {ARC_DENSITY_OPTIONS.map(opt => <Radio.Button key={opt.value} value={opt.value}>{opt.label}</Radio.Button>)}
              </Radio.Group>
            </div>
            <div>
              <Text strong style={{ fontSize: 13 }}>风格偏向</Text>
              <Radio.Group value={arcExpandCfg.style_focus} onChange={(e) => setArcExpandCfg({ ...arcExpandCfg, style_focus: e.target.value })}
                style={{ display: 'flex', gap: 8, marginTop: 6, flexWrap: 'wrap' }} size="small" buttonStyle="solid">
                {ARC_STYLE_OPTIONS.map(opt => <Radio.Button key={opt.value} value={opt.value}>{opt.label}</Radio.Button>)}
              </Radio.Group>
            </div>
            <div>
              <Text strong style={{ fontSize: 13 }}>长远规划要求</Text>
              <Input.TextArea
                value={arcExpandCfg.length_control}
                onChange={(e) => setArcExpandCfg({ ...arcExpandCfg, length_control: e.target.value })}
                rows={3}
                style={{ marginTop: 6 }}
                placeholder="例如：按150万字长篇规划，本卷要有阶段目标、铺垫、误判、升级和余波。"
              />
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginTop: 12 }}>
            <div>
              <Text strong style={{ fontSize: 13 }}>展开长度</Text>
              <Radio.Group value={expandCfg.expansion_scale} onChange={(e) => setExpandCfg({ ...expandCfg, expansion_scale: e.target.value })}
                style={{ display: 'flex', gap: 8, marginTop: 6, flexWrap: 'wrap' }} size="small" buttonStyle="solid">
                <Radio.Button value="compact">短展开</Radio.Button>
                <Radio.Button value="standard">标准</Radio.Button>
                <Radio.Button value="long">长展开</Radio.Button>
                <Radio.Button value="detailed">细写</Radio.Button>
              </Radio.Group>
              <Paragraph style={{ marginTop: 6, marginBottom: 0, fontSize: 12, color: 'var(--text-secondary)' }}>
                只选展开程度，系统会按弧线复杂度自动决定章节数量。
              </Paragraph>
            </div>
            <div>
              <Text strong style={{ fontSize: 13 }}>叙事节奏</Text>
              <Radio.Group value={expandCfg.pacing} onChange={(e) => setExpandCfg({ ...expandCfg, pacing: e.target.value })}
                style={{ display: 'flex', gap: 8, marginTop: 6 }} size="small" buttonStyle="solid">
                <Radio.Button value="slow">生活流</Radio.Button>
                <Radio.Button value="medium">适中</Radio.Button>
                <Radio.Button value="fast">紧凑</Radio.Button>
              </Radio.Group>
            </div>
            <div>
              <Text strong style={{ fontSize: 13 }}>事件密度</Text>
              <Radio.Group value={expandCfg.event_density} onChange={(e) => setExpandCfg({ ...expandCfg, event_density: e.target.value })}
                style={{ display: 'flex', gap: 8, marginTop: 6 }} size="small" buttonStyle="solid">
                <Radio.Button value="low">精简</Radio.Button>
                <Radio.Button value="medium">适中</Radio.Button>
                <Radio.Button value="high">丰富</Radio.Button>
              </Radio.Group>
            </div>
          </div>
        )}
      </Modal>

      {/* Review Modal */}
      <Modal title="📋 评审报告" open={reviewModalOpen} onCancel={() => setReviewModalOpen(false)} footer={null} width={640}>
        {reviewResult && (
          <div style={{ maxHeight: '60vh', overflow: 'auto' }}>
            <div style={{ textAlign: 'center', marginBottom: 16 }}>
              <Title level={2} style={{ margin: 0, color: reviewResult.overall_score >= 7 ? '#52c41a' : '#f5222d' }}>
                {reviewResult.overall_score}/10
              </Title>
              <Text type="secondary">{reviewResult.summary}</Text>
            </div>
            <Button
              type="primary"
              block
              icon={<EditOutlined />}
              loading={repairingReview}
              disabled={!reviewScope?.volumeId}
            onClick={() => repairFromReview()}
              style={{ marginBottom: 12 }}
            >
              按评审报告自动修复
            </Button>
            {reviewResult.dimensions?.map((d: any, i: number) => (
              <div key={i} style={{ padding: '6px 10px', marginBottom: 4, background: '#fafafa', borderRadius: 6, display: 'flex', justifyContent: 'space-between' }}>
                <Text style={{ fontSize: 12 }}>{d.name}</Text>
                <Tag color={d.score >= 7 ? 'green' : d.score >= 5 ? 'orange' : 'red'}>{d.score}</Tag>
              </div>
            ))}
            {reviewResult.critical_issues?.length > 0 && (
              <div style={{ marginTop: 8 }}>
                <Text strong style={{ color: '#f5222d' }}>🔴 致命问题</Text>
                {reviewResult.critical_issues.map((i: any, ix: number) => (
                  <div key={ix} style={{ marginTop: 4, padding: 8, background: '#fff2f0', borderRadius: 6 }}>
                    <Text strong style={{ fontSize: 12 }}>[第{i.chapter}章]{i.description}</Text>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </Modal>

      <Modal
        title="写作总控"
        open={writingSettingsOpen}
        onCancel={() => setWritingSettingsOpen(false)}
        onOk={saveWritingSettings}
        okText="保存"
        confirmLoading={writingSettingsSaving}
        width={760}
      >
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          message="这里是项目默认写作配置。单章写作和批量写作都会继承，工具栏的阅读难度可以临时覆盖。"
        />
        <Row gutter={[12, 12]}>
          <Col xs={24} md={12}>
            <Text type="secondary">阅读难度</Text>
            <Select value={writingControlsDraft.readability_mode} options={READABILITY_OPTIONS} style={{ width: '100%', marginTop: 4 }}
              onChange={(v) => setWritingControlsDraft((p: any) => ({ ...p, readability_mode: v }))} />
          </Col>
          <Col xs={24} md={12}>
            <Text type="secondary">叙事节奏</Text>
            <Select value={writingControlsDraft.pace_mode} style={{ width: '100%', marginTop: 4 }}
              options={[
                { value: 'slow', label: '慢热' },
                { value: 'standard', label: '标准' },
                { value: 'fast', label: '快节奏' },
                { value: '爽文快推', label: '爽文快推' },
              ]}
              onChange={(v) => setWritingControlsDraft((p: any) => ({ ...p, pace_mode: v }))} />
          </Col>
          <Col xs={24} md={12}>
            <Text type="secondary">对白比例</Text>
            <Select value={writingControlsDraft.dialogue_density} style={{ width: '100%', marginTop: 4 }}
              options={[{ value: 'low', label: '低' }, { value: 'medium', label: '中' }, { value: 'high', label: '高' }]}
              onChange={(v) => setWritingControlsDraft((p: any) => ({ ...p, dialogue_density: v }))} />
          </Col>
          <Col xs={24} md={12}>
            <Text type="secondary">描写密度</Text>
            <Select value={writingControlsDraft.description_density} style={{ width: '100%', marginTop: 4 }}
              options={[{ value: 'light', label: '轻描写' }, { value: 'standard', label: '标准' }, { value: 'rich', label: '细腻' }]}
              onChange={(v) => setWritingControlsDraft((p: any) => ({ ...p, description_density: v }))} />
          </Col>
          <Col xs={24} md={12}>
            <Text type="secondary">幽默强度</Text>
            <Select value={writingControlsDraft.humor_level} style={{ width: '100%', marginTop: 4 }}
              options={[{ value: 'none', label: '无' }, { value: 'light', label: '轻微' }, { value: 'medium', label: '中等' }, { value: 'strong', label: '强' }]}
              onChange={(v) => setWritingControlsDraft((p: any) => ({ ...p, humor_level: v }))} />
          </Col>
          <Col xs={24} md={12}>
            <Text type="secondary">信息密度</Text>
            <Select value={writingControlsDraft.information_density} style={{ width: '100%', marginTop: 4 }}
              options={[{ value: 'low', label: '低' }, { value: 'medium', label: '中' }, { value: 'high', label: '高' }]}
              onChange={(v) => setWritingControlsDraft((p: any) => ({ ...p, information_density: v }))} />
          </Col>
          <Col xs={24} md={12}>
            <Text type="secondary">章节结构</Text>
            <Select value={writingControlsDraft.chapter_template} style={{ width: '100%', marginTop: 4 }}
              options={['standard', '爽点章', '搞笑章', '悬疑章', '感情章', '战斗章', '日常过渡章'].map((v) => ({ value: v, label: v === 'standard' ? '标准推进章' : v }))}
              onChange={(v) => setWritingControlsDraft((p: any) => ({ ...p, chapter_template: v }))} />
          </Col>
          <Col xs={24} md={12}>
            <Text type="secondary">前20万强追读</Text>
            <Select value={writingControlsDraft.early_grip_mode || 'auto'} style={{ width: '100%', marginTop: 4 }}
              options={[
                { value: 'auto', label: '自动：前20万启用' },
                { value: 'force', label: '强制：所有章节启用' },
                { value: 'off', label: '关闭' },
              ]}
              onChange={(v) => setWritingControlsDraft((p: any) => ({ ...p, early_grip_mode: v }))} />
          </Col>
          <Col xs={24} md={12}>
            <Text type="secondary">质量链路</Text>
            <Radio.Group
              value={writingControlsDraft.auto_light_fix ? 'fix' : writingControlsDraft.auto_quality_check ? 'audit' : 'off'}
              style={{ display: 'block', marginTop: 6 }}
              onChange={(e) => {
                const value = e.target.value;
                setWritingControlsDraft((p: any) => ({
                  ...p,
                  auto_quality_check: value !== 'off',
                  auto_light_fix: value === 'fix',
                }));
              }}
            >
              <Radio value="fix">审稿并轻修</Radio>
              <Radio value="audit">只审稿</Radio>
              <Radio value="off">关闭</Radio>
            </Radio.Group>
          </Col>
        </Row>
      </Modal>

      {/* Batch Write Selector */}
      <Modal title="批量写作" open={batchModalOpen} onCancel={() => { setBatchModalOpen(false); setBatchSelectedChs(new Set()); }} footer={null} width={420}>
        {batchVolume && (() => {
          const arc = batchVolume.narrative_arcs?.[batchArcIdx];
          const arcChs = chapters.filter((c: any) => c.volume_id === batchVolume.id && c.arc_name === arc?.name);
          const unwritten = arcChs.filter((c: any) => !c.content);
          const allIds = unwritten.map((c: any) => c.id);
          const selectedCount = batchSelectedChs.size || allIds.length;

          return (
            <div>
              <Text strong style={{ display: 'block', marginBottom: 8 }}>
                {batchVolume.title} · {arc?.name}（{arcChs.length} 章，{unwritten.length} 章未写）
              </Text>
              <div style={{ marginBottom: 12 }}>
                <Text type="secondary" style={{ display: 'block', fontSize: 12, marginBottom: 4 }}>阅读难度</Text>
                <Select
                  size="small"
                  value={batchReadabilityMode}
                  onChange={setBatchReadabilityMode}
                  options={READABILITY_OPTIONS}
                  style={{ width: '100%' }}
                />
              </div>
              <div style={{ maxHeight: 300, overflow: 'auto', marginBottom: 12 }}>
                {unwritten.map((ch: any) => (
                  <div key={ch.id} style={{
                    padding: '6px 10px', marginBottom: 4, borderRadius: 6,
                    background: batchSelectedChs.has(ch.id) || batchSelectedChs.size === 0 ? '#e6f7ff' : '#fafafa',
                    cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8,
                    border: batchSelectedChs.has(ch.id) || batchSelectedChs.size === 0 ? '1px solid #1677ff' : '1px solid #f0f0f0',
                  }} onClick={() => {
                    setBatchSelectedChs(prev => {
                      const next = new Set(prev);
                      if (prev.size === 0) {
                        allIds.forEach(id => next.add(id));
                        next.delete(ch.id);
                      } else if (next.has(ch.id)) next.delete(ch.id);
                      else next.add(ch.id);
                      return next;
                    });
                  }}>
                    <span style={{ fontSize: 12 }}>
                      第{ch.chapter_number}章 {ch.title || ''}
                      {ch.content && <Tag style={{ marginLeft: 4, fontSize: 9 }} color="green">已有</Tag>}
                    </span>
                  </div>
                ))}
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <Button size="small" onClick={() => {
                  if (batchSelectedChs.size === 0) setBatchSelectedChs(new Set(allIds));
                  else setBatchSelectedChs(new Set());
                }}>
                  {batchSelectedChs.size === 0 ? '全选' : '取消全选'}
                </Button>
                <Button type="primary" block
                  disabled={!unwritten.length || (batchSelectedChs.size > 0 && selectedCount === 0)}
                  onClick={() => {
                    const ids = batchSelectedChs.size > 0 ? Array.from(batchSelectedChs) : undefined;
                    const mode = batchReadabilityMode;
                    setBatchModalOpen(false);
                    setBatchSelectedChs(new Set());
                    batchWriteArc(batchVolume, batchArcIdx, ids, mode);
                  }}>
                  写 {selectedCount} 章
                </Button>
              </div>
            </div>
          );
        })()}
      </Modal>

      <Drawer
        title="弧线详情"
        open={arcDetailOpen}
        onClose={() => setArcDetailOpen(false)}
        width={920}
        extra={detailArc ? (
          <Space size={8} wrap>
            {detailHasStructuralGaps && (
              <Button
                size="small"
                type="primary"
                loading={expandLoading === `${detailVolume?.id}-revise-${detailArcIndex}-修复连续性`}
                onClick={() => reviseVolumeArc(detailVolume, detailArcIndex, '修复连续性', arcContinuityRepairInstruction(detailQuality, detailArc, detailChecks))}
              >
                修复结构缺口
              </Button>
            )}
            {!detailHasStructuralGaps && detailWarnings.length > 0 && (
              <Button
                size="small"
                loading={expandLoading === `${detailVolume?.id}-revise-${detailArcIndex}-优化交接`}
                onClick={() => reviseVolumeArc(detailVolume, detailArcIndex, '优化交接', arcHandoffPolishInstruction(detailQuality, detailArc))}
              >
                优化交接
              </Button>
            )}
            <Button size="small" loading={expandLoading === `${detailVolume?.id}-revise-${detailArcIndex}-重写`} onClick={() => reviseVolumeArc(detailVolume, detailArcIndex, '重写')}>重写</Button>
            <Button size="small" loading={expandLoading === `${detailVolume?.id}-revise-${detailArcIndex}-拉长`} onClick={() => reviseVolumeArc(detailVolume, detailArcIndex, '拉长')}>拉长</Button>
            <Button size="small" loading={expandLoading === `${detailVolume?.id}-revise-${detailArcIndex}-压缩`} onClick={() => reviseVolumeArc(detailVolume, detailArcIndex, '压缩')}>压缩</Button>
            {!detailArcChapters.length ? (
              <Button size="small" icon={<ThunderboltOutlined />} onClick={() => openArcChapterExpandModal(detailVolume, detailArcIndex)}>展开章节</Button>
            ) : (
              <Button size="small" icon={<ThunderboltOutlined />} onClick={() => { setBatchVolume(detailVolume); setBatchArcIdx(detailArcIndex); setBatchModalOpen(true); }}>批量写</Button>
            )}
          </Space>
        ) : null}
      >
        {detailArc ? (
          <div className="arc-detail-drawer">
            <div className="arc-detail-hero">
              <div>
                <Text type="secondary">{detailVolume?.title || '未命名卷'} · 第{detailArc.chapter_start || '?'}-{detailArc.chapter_end || '?'}章</Text>
                <Title level={4}>{detailArc.name || `弧线 ${detailArcIndex + 1}`}</Title>
                <Space size={[6, 6]} wrap>
                  <Tag color={detailStatus.color}>{detailStatus.label}</Tag>
                  {detailArc.narrative_function && <Tag color="blue">{detailArc.narrative_function}</Tag>}
                  {detailArc.emotional_color && <Tag color="purple">{detailArc.emotional_color}</Tag>}
                  {detailArc.tension_curve && <Tag>{detailArc.tension_curve}</Tag>}
                  <Tag>{detailArcChapters.length || detailArc.chapter_count || 0}章</Tag>
                </Space>
              </div>
              <Alert
                type={detailHasStructuralGaps ? 'warning' : detailWarnings.length ? 'info' : 'success'}
                showIcon
                message={detailHasStructuralGaps ? '结构缺口需要先修复' : detailWarnings.length ? '交接提醒，不阻止展开章节' : '结构连续性可用'}
                description="这里的分数是结构连续性分，不是剧情质量分；80 分以上通常可继续展开章节。"
              />
            </div>

            <div className="arc-detail-section">
              <div className="arc-detail-section-title">结构检查</div>
              <div className="arc-quality-grid arc-quality-grid-wide">
                {detailChecks.map((item: any) => (
                  <div key={item.key} className={`arc-quality-check ${item.failed ? 'bad' : item.warning ? 'warn' : 'ok'}`}>
                    <span>{item.failed ? '缺' : item.warning ? '提' : '✓'}</span>
                    <div>
                      <Text strong>{item.label}</Text>
                      <Text type="secondary">{item.help}</Text>
                    </div>
                  </div>
                ))}
              </div>
              {(detailIssues.length > 0 || detailChecks.some((x: any) => x.failed)) && (
                <div className="arc-detail-tags">
                  {detailIssues.map((x: any, idx: number) => (
                    <Tag key={idx} color="orange">{x.field ? `${x.field}：` : ''}{x.issue || x.description || '连续性风险'}</Tag>
                  ))}
                  {detailChecks.filter((x: any) => x.failed).map((x: any) => (
                    <Tag key={`missing-${x.key}`} color="orange">缺少{x.label}</Tag>
                  ))}
                </div>
              )}
              {detailWarnings.length > 0 && (
                <div className="arc-detail-tags">
                  {detailWarnings.map((x: any, idx: number) => (
                    <Tag key={idx} color="blue">{x.field ? `${x.field}：` : ''}{x.issue || x.description || '交接提醒'}</Tag>
                  ))}
                </div>
              )}
            </div>

            <div className="arc-detail-section">
              <div className="arc-detail-section-title">弧线内容</div>
              <Descriptions size="small" bordered column={1}>
                <Descriptions.Item label="弧线说明">{renderArcValue(detailArc.description)}</Descriptions.Item>
                <Descriptions.Item label="开局状态">{renderArcValue(detailArc.opening_state)}</Descriptions.Item>
                <Descriptions.Item label="终点状态">{renderArcValue(detailArc.ending_state)}</Descriptions.Item>
                <Descriptions.Item label="上承交接">{renderArcValue(detailArc.handoff_from_previous || detailArc.dependence_on_previous)}</Descriptions.Item>
                <Descriptions.Item label="下启钩子">{renderArcValue(detailArc.handoff_to_next || detailArc.payoff_for_next)}</Descriptions.Item>
                <Descriptions.Item label="因果链">{renderArcValue(detailArc.continuity_chain)}</Descriptions.Item>
                <Descriptions.Item label="不可替代">{renderArcValue(detailArc.irreplaceable_value)}</Descriptions.Item>
                <Descriptions.Item label="主角变化">{renderArcValue(detailArc.protagonist_change)}</Descriptions.Item>
              </Descriptions>
            </div>

            <div className="arc-detail-section">
              <div className="arc-detail-section-title">变化台阶</div>
              {Array.isArray(detailArc.arc_steps) && detailArc.arc_steps.length > 0 ? (
                <div className="arc-step-list">
                  {detailArc.arc_steps.map((step: any, idx: number) => (
                    <div key={idx} className="arc-step-card">
                      <div className="arc-step-head">
                        <Tag color="geekblue">台阶 {idx + 1}</Tag>
                        <Text strong>{step.step_name || step.name || '未命名台阶'}</Text>
                      </div>
                      <Descriptions size="small" column={1}>
                        <Descriptions.Item label="起点">{renderArcValue(step.starting_state)}</Descriptions.Item>
                        <Descriptions.Item label="触发">{renderArcValue(step.trigger_event)}</Descriptions.Item>
                        <Descriptions.Item label="行动">{renderArcValue(step.visible_action)}</Descriptions.Item>
                        <Descriptions.Item label="阻力">{renderArcValue(step.friction)}</Descriptions.Item>
                        <Descriptions.Item label="变化">{renderArcValue(step.state_change)}</Descriptions.Item>
                        <Descriptions.Item label="后果">{renderArcValue(step.consequence)}</Descriptions.Item>
                        <Descriptions.Item label="带给后文">{renderArcValue(step.carry_forward)}</Descriptions.Item>
                      </Descriptions>
                    </div>
                  ))}
                </div>
              ) : <Text type="secondary">暂无变化台阶</Text>}
            </div>

            <div className="arc-detail-section arc-detail-two-col">
              <div>
                <div className="arc-detail-section-title">关键节点</div>
                {renderArcValue(detailArc.key_milestones)}
              </div>
              <div>
                <div className="arc-detail-section-title">伏笔计划</div>
                {renderArcValue(detailArc.foreshadowing_plan)}
              </div>
              <div>
                <div className="arc-detail-section-title">角色引入</div>
                {renderArcValue(detailArc.character_introduction_plan || detailArc.character_focus)}
              </div>
              <div>
                <div className="arc-detail-section-title">势力引入</div>
                {renderArcValue(detailArc.faction_introduction_plan || detailArc.faction_focus)}
              </div>
            </div>
          </div>
        ) : (
          <Empty description="暂无弧线详情" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )}
      </Drawer>

      {/* Task Drawer */}
      <Drawer title="AI 任务" open={taskDrawerOpen} onClose={() => setTaskDrawerOpen(false)} width={680}
        extra={<Button size="small" onClick={refreshTasks}>刷新</Button>}>
        {tasks.length === 0 ? <Empty description="无任务" /> : (
          <Table dataSource={tasks} size="small" pagination={false} rowKey="id" tableLayout="fixed"
            columns={[
              { title: '类型', dataIndex: 'task_type', width: 120, render: (t: string) => <Tag style={{ whiteSpace: 'normal', lineHeight: 1.5 }}>{TASK_LABELS[t] || t}</Tag> },
              { title: '状态', dataIndex: 'status', width: 88, render: (s: string) => {
                  const statusMap: Record<string, { label: string; color: string }> = {
                    running: { label: '运行中', color: 'processing' },
                    completed: { label: '已完成', color: 'green' },
                    failed: { label: '失败', color: 'red' },
                    cancelling: { label: '取消中', color: 'warning' },
                    cancelled: { label: '已取消', color: 'default' },
                    pending: { label: '等待中', color: 'default' },
                  };
                  const info = statusMap[s] || { label: s, color: 'default' };
                  return <Tag color={info.color}>{info.label}</Tag>;
                }},
              { title: '进度', dataIndex: 'progress', width: 230, render: (_: any, rec: any) => {
                  const pct = Math.round((rec.progress || 0) * 100);
                  return (
                    <div>
                      <Progress percent={pct} size="small" status={rec.status === 'failed' ? 'exception' : rec.status === 'completed' ? 'success' : 'active'} />
                      {rec.progress_label && <Text type="secondary" style={{ fontSize: 12, display: 'block', whiteSpace: 'normal', wordBreak: 'break-word' }}>{rec.progress_label}</Text>}
                    </div>
                  );
                }},
                { title: '操作', width: 178, render: (_: any, rec: any) => (
                    <Space size={4}>
                      <Button size="small" icon={<EyeOutlined />} onClick={() => openTaskDetail(rec)} />
                      {rec.status === 'running' ? <Button size="small" danger icon={<StopOutlined />} onClick={() => cancelTask(rec.id)} /> : null}
                      {rec.status === 'failed' ? (
                        <Button size="small" type="primary" icon={<ReloadOutlined />} loading={taskActionLoading === rec.id} onClick={() => retryTask(rec)}>
                          重开
                        </Button>
                      ) : null}
                      {rec.status === 'completed' && String(rec.task_type || '').startsWith('review') && rec.result && rec.meta?.volume_id ? (
                        <Button size="small" type="primary" icon={<PlayCircleOutlined />} loading={taskActionLoading === rec.id}
                          onClick={() => launchRepairFromTask(rec)} />
                      ) : null}
                    </Space>
                  ) },
                { title: '时间', dataIndex: 'created_at', width: 96, render: (t: string) => t ? new Date(t).toLocaleString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '' },
               ]}
               expandable={tasks.some(t => t.error || t.progress_label || t.detail) ? {
                expandedRowRender: (rec: any) => (
                  <div style={{ fontSize: 12 }}>
                    {rec.error && <Text type="danger" style={{ whiteSpace: 'pre-wrap', display: 'block', marginBottom: 8 }}>{rec.error}</Text>}
                    {rec.progress_label && <Text style={{ display: 'block', marginBottom: 6 }}>当前：{rec.progress_label}</Text>}
                    {rec.detail && Object.keys(rec.detail).length > 0 && (
                      <pre style={{ margin: 0, whiteSpace: 'pre-wrap', color: '#64748b' }}>{JSON.stringify(rec.detail, null, 2)}</pre>
                    )}
                  </div>
                ),
                rowExpandable: (rec: any) => !!(rec.error || rec.progress_label || (rec.detail && Object.keys(rec.detail).length)),
              } : undefined}
          />
        )}
      </Drawer>

      <Drawer
        title="系统诊断"
        open={systemDrawerOpen}
        onClose={() => setSystemDrawerOpen(false)}
        width={760}
        extra={<Button size="small" icon={<ReloadOutlined />} loading={systemLoading} onClick={() => loadSystemPanel(systemTab)}>刷新</Button>}
      >
        <Spin spinning={systemLoading}>
          <Tabs
            activeKey={systemTab}
            onChange={(key) => {
              setSystemTab(key);
              loadSystemPanel(key);
            }}
            items={[
              {
                key: 'health',
                label: <span><BarChartOutlined /> 健康</span>,
                children: <SystemHealthView data={systemHealth} />,
              },
              {
                key: 'ledger',
                label: <span><DatabaseOutlined /> 状态账本</span>,
                children: <StateLedgerView data={stateLedger} />,
              },
              {
                key: 'context',
                label: <span><FileSearchOutlined /> 上下文</span>,
                children: contextPreview ? (
                  <div className="system-drawer-content">
                    <Alert type="info" showIcon message={`当前预览范围：${contextPreview.scope || 'project'}`} />
                    <RawJsonBlock title="生成上下文" data={contextPreview} />
                  </div>
                ) : <Empty description="暂无上下文预览" image={Empty.PRESENTED_IMAGE_SIMPLE} />,
              },
              {
                key: 'world',
                label: <span><AuditOutlined /> 规则</span>,
                children: <WorldRuleAuditView data={worldRuleAudit} />,
              },
              {
                key: 'prompts',
                label: <span><BranchesOutlined /> 模块</span>,
                children: <PromptModulesView data={promptModules} />,
              },
            ]}
          />
        </Spin>
      </Drawer>

      <Modal
        title="改章影响分析"
        open={impactModalOpen}
        onCancel={() => setImpactModalOpen(false)}
        footer={<Button onClick={() => setImpactModalOpen(false)}>关闭</Button>}
        width={720}
      >
        <Spin spinning={impactLoading}>
          <ImpactView data={impactData} />
        </Spin>
      </Modal>

      <Modal title="导出正文" open={exportModalOpen} onCancel={() => setExportModalOpen(false)} onOk={doExport} confirmLoading={exporting} okText="导出">
        <Space direction="vertical" style={{ width: '100%' }} size={12}>
          <div>
            <Text style={{ display: 'block', marginBottom: 6 }}>导出范围</Text>
            <Select
              value={exportCfg.scope}
              style={{ width: '100%' }}
              onChange={(scope) => setExportCfg((prev) => ({ ...prev, scope }))}
              options={[
                { label: '按卷导出', value: 'volume' },
                { label: '按故事弧线导出', value: 'arc' },
              ]}
            />
          </div>
          <div>
            <Text style={{ display: 'block', marginBottom: 6 }}>卷</Text>
            <Select
              value={exportCfg.volumeId || undefined}
              style={{ width: '100%' }}
              onChange={(volumeId) => {
                const vol = volumes.find((v: any) => v.id === volumeId);
                const firstArc = vol?.narrative_arcs?.[0]?.name || '';
                setExportCfg((prev) => ({ ...prev, volumeId, arcName: firstArc }));
              }}
              options={volumes.map((v: any) => ({ label: `卷${v.volume_number} · ${v.title || '未命名卷'}`, value: v.id }))}
            />
          </div>
          {exportCfg.scope === 'arc' && (
            <div>
              <Text style={{ display: 'block', marginBottom: 6 }}>故事弧线</Text>
              <Select
                value={exportCfg.arcName || undefined}
                style={{ width: '100%' }}
                onChange={(arcName) => setExportCfg((prev) => ({ ...prev, arcName }))}
                options={(volumes.find((v: any) => v.id === exportCfg.volumeId)?.narrative_arcs || []).map((a: any) => ({
                  label: a.name,
                  value: a.name,
                }))}
                placeholder="请选择弧线"
              />
            </div>
          )}
          <div>
            <Text style={{ display: 'block', marginBottom: 6 }}>格式</Text>
            <Select
              value={exportCfg.format}
              style={{ width: '100%' }}
              onChange={(format) => setExportCfg((prev) => ({ ...prev, format }))}
              options={[
                { label: 'Markdown (.md)', value: 'md' },
                { label: '纯文本 (.txt)', value: 'txt' },
                { label: 'JSON (.json)', value: 'json' },
              ]}
            />
          </div>
        </Space>
      </Modal>

      <Modal title="任务详情" open={taskDetailOpen} onCancel={() => setTaskDetailOpen(false)} footer={null} width={900}>
        {taskDetail && (
          <div style={{ maxHeight: '70vh', overflow: 'auto' }}>
            <Descriptions size="small" column={2} bordered style={{ marginBottom: 16 }}>
              <Descriptions.Item label="类型">{TASK_LABELS[taskDetail.task_type] || taskDetail.task_type}</Descriptions.Item>
              <Descriptions.Item label="状态">{taskDetail.status}</Descriptions.Item>
              <Descriptions.Item label="创建时间">{taskDetail.created_at ? new Date(taskDetail.created_at).toLocaleString('zh-CN') : '-'}</Descriptions.Item>
              <Descriptions.Item label="更新时间">{taskDetail.updated_at ? new Date(taskDetail.updated_at).toLocaleString('zh-CN') : '-'}</Descriptions.Item>
            </Descriptions>
            {taskDetail.progress_label && <Paragraph>当前：{taskDetail.progress_label}</Paragraph>}
            {taskDetail.error && <Paragraph type="danger" style={{ whiteSpace: 'pre-wrap' }}>{taskDetail.error}</Paragraph>}
            {taskDetail.result && <TaskResultView task={taskDetail} />}
            {taskDetail.meta && Object.keys(taskDetail.meta).length > 0 && (
              <RawJsonBlock title="任务参数" data={taskDetail.meta} />
            )}
            {taskDetail.status === 'completed' && taskDetail.task_type === 'audit_chapter' && taskDetail.result && taskDetail.meta?.chapter_id && (
              <div className="task-detail-actions">
                <Button
                  type="primary"
                  icon={<EditOutlined />}
                  loading={taskActionLoading === `${taskDetail.id}-quality_light_fix`}
                  disabled={!!taskActionLoading}
                  onClick={() => reviseByAuditTask(taskDetail, 'quality_light_fix')}
                >
                  按审计轻修
                </Button>
                <Popconfirm
                  title="按审计重写会覆盖该章节正文，系统会先保存版本备份。继续吗？"
                  onConfirm={() => reviseByAuditTask(taskDetail, 'audit_full_rewrite')}
                >
                  <Button
                    danger
                    icon={<ReloadOutlined />}
                    loading={taskActionLoading === `${taskDetail.id}-audit_full_rewrite`}
                    disabled={!!taskActionLoading}
                  >
                    按审计重写
                  </Button>
                </Popconfirm>
              </div>
            )}
            {taskDetail.status === 'completed' && String(taskDetail.task_type || '').startsWith('review') && taskDetail.result && taskDetail.meta?.volume_id && (
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                loading={taskActionLoading === taskDetail.id}
                onClick={() => launchRepairFromTask(taskDetail)}
                style={{ marginTop: 12 }}
              >
                用这条评审记录发起修复
              </Button>
            )}
          </div>
        )}
      </Modal>

      <Modal
        title="项目信息"
        open={projectInfoOpen}
        onCancel={() => setProjectInfoOpen(false)}
        onOk={saveProjectInfo}
        confirmLoading={projectInfoSaving}
        okText="保存"
        width={720}
      >
        <div style={{ marginBottom: 14 }}>
          <Text strong>书名</Text>
          <Input
            value={projectInfoDraft.title}
            onChange={(e) => setProjectInfoDraft((prev) => ({ ...prev, title: e.target.value }))}
            placeholder="输入书名"
            maxLength={100}
            showCount
            style={{ marginTop: 8 }}
          />
        </div>
        <div>
          <Text strong>简介</Text>
          <Input.TextArea
            value={projectInfoDraft.story_brief}
            onChange={(e) => setProjectInfoDraft((prev) => ({ ...prev, story_brief: e.target.value }))}
            placeholder="输入这本书的简介、核心冲突、主角目标和长线悬念"
            autoSize={{ minRows: 8, maxRows: 16 }}
            maxLength={5000}
            showCount
            style={{ marginTop: 8 }}
          />
        </div>
      </Modal>
    </div>
  );
}
