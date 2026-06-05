import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Alert, Button, Card, Empty, Input, Progress, Segmented, Space, Spin, Statistic, Tag, Typography } from 'antd';
import {
  AlertOutlined, ApartmentOutlined, BookOutlined, ClockCircleOutlined, DatabaseOutlined,
  FlagOutlined, LeftOutlined, SafetyOutlined, SearchOutlined, TeamOutlined,
} from '@ant-design/icons';
import { storyApi } from '@/services/projectApi';
import './MemoryCenterPage.css';

const { Title, Text, Paragraph } = Typography;

const FORESHADOWING_STATUS_LABELS: Record<string, { label: string; color: string }> = {
  planted: { label: '已铺设', color: 'orange' },
  active: { label: '推进中', color: 'blue' },
  progressed: { label: '推进中', color: 'blue' },
  revealed: { label: '已回收', color: 'green' },
  resolved: { label: '已解决', color: 'green' },
  abandoned: { label: '已废弃', color: 'default' },
  播种: { label: '已铺设', color: 'orange' },
  铺设: { label: '已铺设', color: 'orange' },
  推进: { label: '推进中', color: 'blue' },
  回收: { label: '已回收', color: 'green' },
};

const RISK_LABELS: Record<string, { label: string; color: string }> = {
  critical: { label: '致命', color: 'red' },
  high: { label: '严重', color: 'orange' },
  medium: { label: '中等', color: 'gold' },
  low: { label: '轻微', color: 'blue' },
  致命: { label: '致命', color: 'red' },
  严重: { label: '严重', color: 'orange' },
  轻微: { label: '轻微', color: 'blue' },
};

const EVENT_TYPE_LABELS: Record<string, string> = {
  event: '事件',
  encounter: '遭遇',
  meeting: '会面',
  conflict: '冲突',
  confrontation: '对峙',
  battle: '战斗',
  fight: '打斗',
  investigation: '调查',
  discovery: '发现',
  clue: '线索',
  twist: '反转',
  revelation: '揭示',
  reveal: '揭露',
  decision: '抉择',
  setback: '受挫',
  crisis: '危机',
  warning: '警告',
  transition: '过渡',
  emotional_climax: '情感高潮',
  relationship: '关系推进',
  foreshadowing: '伏笔',
  payoff: '伏笔回收',
  daily: '日常',
  formal_event: '正式事件',
};

const translateEventType = (value: string) => {
  if (!value) return '事件';
  return EVENT_TYPE_LABELS[value] || EVENT_TYPE_LABELS[value.toLowerCase()] || value;
};

const renderForeshadowingStatus = (status: string) => {
  const info = FORESHADOWING_STATUS_LABELS[status] || { label: status || '未定', color: 'default' };
  return <Tag color={info.color}>{info.label}</Tag>;
};

const renderRisk = (severity: string) => {
  const info = RISK_LABELS[severity] || { label: severity || '问题', color: 'default' };
  return <Tag color={info.color}>{info.label}</Tag>;
};

const textValue = (value: any): string => {
  if (!value) return '';
  if (typeof value === 'string') return value;
  if (Array.isArray(value)) return value.map(textValue).filter(Boolean).join('；');
  if (typeof value === 'object') {
    return Object.entries(value)
      .filter(([, v]) => v !== undefined && v !== null && String(v).trim() !== '')
      .map(([k, v]) => `${k}：${typeof v === 'string' ? v : JSON.stringify(v)}`)
      .join('；');
  }
  return String(value);
};

const RuleList = ({ items, empty }: { items: any[]; empty: string }) => {
  if (!items?.length) return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={empty} />;
  return (
    <div className="memory-rule-list">
      {items.map((item, index) => (
        <div key={index} className="memory-rule-item">
          {textValue(item)}
        </div>
      ))}
    </div>
  );
};

export default function MemoryCenterPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeView, setActiveView] = useState('角色');
  const [query, setQuery] = useState('');

  useEffect(() => {
    if (!projectId) return;
    storyApi.memoryCenter(projectId).then(setData).finally(() => setLoading(false));
  }, [projectId]);

  const stats = data?.stats || {};
  const worldRules = data?.world_rules || {};
  const q = query.trim().toLowerCase();
  const writtenPercent = stats.chapter_count ? Math.round(((stats.written_chapter_count || 0) / stats.chapter_count) * 100) : 0;

  const filtered = useMemo(() => {
    const includes = (value: any) => !q || textValue(value).toLowerCase().includes(q);
    return {
      characters: (data?.characters || []).filter((item: any) => includes(item)),
      foreshadowing: (data?.foreshadowing || []).filter((item: any) => includes(item)),
      events: (data?.recent_events || []).filter((item: any) => includes(item)),
      chapters: (data?.chapter_memory || []).filter((item: any) => includes(item)),
      risks: (data?.risks || []).filter((item: any) => includes(item)),
      factions: (data?.factions || []).filter((item: any) => includes(item)),
    };
  }, [data, q]);

  if (!projectId) return null;
  if (loading) return <div className="memory-loading"><Spin size="large" /></div>;

  return (
    <div className="memory-page">
      <div className="memory-topbar">
        <div className="memory-top-left">
          <Link to={`/projects/${projectId}`}><Button icon={<LeftOutlined />}>返回工作台</Button></Link>
          <div>
            <Title level={3} className="memory-title">记忆中枢</Title>
            <div className="memory-subtitle">查看写作时会被引用的规则、人物状态、伏笔、事件和风险</div>
          </div>
        </div>
        <Input
          className="memory-search"
          prefix={<SearchOutlined />}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="搜索角色、伏笔、事件、规则"
          allowClear
        />
      </div>

      <div className="memory-layout">
        <aside className="memory-sidebar">
          <Card className="memory-project-card">
            <div className="memory-project-icon"><DatabaseOutlined /></div>
            <Title level={4}>{data?.project?.title || '未命名项目'}</Title>
            <Paragraph>{data?.project?.story_brief || '暂无简介'}</Paragraph>
            <Space wrap>
              {data?.project?.genre && <Tag color="blue">{data.project.genre}</Tag>}
              {data?.project?.core_theme && <Tag color="purple">核心主题：{data.project.core_theme}</Tag>}
              {(data?.project?.secondary_themes || []).slice(0, 4).map((t: string) => <Tag key={t}>副主题：{t}</Tag>)}
            </Space>
          </Card>

          <div className="memory-stat-grid">
            <Card><Statistic title="角色" value={stats.character_count || 0} prefix={<TeamOutlined />} /></Card>
            <Card><Statistic title="组织" value={stats.faction_count || 0} prefix={<ApartmentOutlined />} /></Card>
            <Card><Statistic title="章节" value={stats.chapter_count || 0} prefix={<BookOutlined />} /></Card>
            <Card><Statistic title="伏笔" value={stats.foreshadowing_count || 0} prefix={<FlagOutlined />} /></Card>
          </div>

          <Card className="memory-progress-card">
            <div className="memory-card-head">
              <Text strong>写作进度</Text>
              <Text type="secondary">{stats.written_chapter_count || 0}/{stats.chapter_count || 0} 章</Text>
            </div>
            <Progress percent={writtenPercent} />
            <div className="memory-progress-meta">
              <span>总字数</span>
              <strong>{((stats.total_words || 0) / 10000).toFixed(1)} 万</strong>
            </div>
          </Card>

          {stats.risk_count > 0 && (
            <Alert
              type="warning"
              showIcon
              className="memory-risk-alert"
              message={`写作风险 ${stats.risk_count} 条`}
              description="写下一章前建议先处理质量仪表盘中的严重问题。"
            />
          )}
        </aside>

        <main className="memory-main">
          <div className="memory-section-grid">
            <Card title={<span><SafetyOutlined /> 硬约束</span>} className="memory-rule-card">
              <RuleList items={worldRules.hard_rules || []} empty="暂无硬约束" />
            </Card>
            <Card title={<span><BookOutlined /> 文风氛围</span>} className="memory-rule-card">
              <RuleList items={worldRules.tone_rules || []} empty="暂无文风氛围" />
            </Card>
            <Card title={<span><AlertOutlined /> 生成限制</span>} className="memory-rule-card">
              <RuleList items={worldRules.constraints || []} empty="暂无生成限制" />
            </Card>
          </div>

          <Card className="memory-work-card">
            <div className="memory-work-head">
              <Segmented
                value={activeView}
                onChange={(value) => setActiveView(String(value))}
                options={['角色', '伏笔', '事件', '章节记忆', '风险', '组织']}
              />
              <Text type="secondary">
                {activeView === '角色' && `${filtered.characters.length} 个角色`}
                {activeView === '伏笔' && `${filtered.foreshadowing.length} 条伏笔`}
                {activeView === '事件' && `${filtered.events.length} 条事件`}
                {activeView === '章节记忆' && `${filtered.chapters.length} 章记忆`}
                {activeView === '风险' && `${filtered.risks.length} 条风险`}
                {activeView === '组织' && `${filtered.factions.length} 个组织`}
              </Text>
            </div>

            {activeView === '角色' && (
              <div className="memory-card-list">
                {filtered.characters.length === 0 ? <Empty description="暂无角色" /> : filtered.characters.map((char: any) => (
                  <Card key={char.id} size="small" className="memory-item-card">
                    <div className="memory-item-head">
                      <div>
                        <Text strong>{char.name}</Text>
                        <Space wrap size={4}>
                          {char.role_type && <Tag>{char.role_type}</Tag>}
                          {char.primary_faction && <Tag color="blue">{char.primary_faction}</Tag>}
                        </Space>
                      </div>
                      {char.first_appeared_chapter && <Tag>初登场：第{char.first_appeared_chapter}章</Tag>}
                    </div>
                    {char.motivation && <Paragraph><Text strong>动机：</Text>{char.motivation}</Paragraph>}
                    {textValue(char.current_state) && <Paragraph><Text strong>当前状态：</Text>{textValue(char.current_state)}</Paragraph>}
                    {char.growth_arc && <Paragraph><Text strong>成长线：</Text>{char.growth_arc}</Paragraph>}
                  </Card>
                ))}
              </div>
            )}

            {activeView === '伏笔' && (
              <div className="memory-card-list">
                {filtered.foreshadowing.length === 0 ? <Empty description="暂无伏笔" /> : filtered.foreshadowing.map((item: any) => (
                  <Card key={item.id} size="small" className="memory-item-card">
                    <div className="memory-item-head">
                      <Text strong>{item.name}</Text>
                      {renderForeshadowingStatus(item.status)}
                    </div>
                    {item.description && <Paragraph>{item.description}</Paragraph>}
                    <div className="memory-two-col">
                      <div><span>铺设</span><strong>{item.plant_stage || (item.plant_chapter ? `第${item.plant_chapter}章` : '未定')}</strong></div>
                      <div><span>回收</span><strong>{item.reveal_stage || (item.reveal_chapter ? `第${item.reveal_chapter}章` : '未定')}</strong></div>
                    </div>
                  </Card>
                ))}
              </div>
            )}

            {activeView === '事件' && (
              <div className="memory-timeline">
                {filtered.events.length === 0 ? <Empty description="暂无事件" /> : filtered.events.map((event: any) => (
                  <div key={event.id} className="memory-timeline-item">
                    <div className="memory-timeline-dot" />
                    <div>
                      <Space wrap>
                        <Tag icon={<ClockCircleOutlined />}>{event.time_point || '未知时间'}</Tag>
                        <Tag color={event.is_major ? 'red' : 'default'}>{translateEventType(event.event_type)}</Tag>
                      </Space>
                      <Paragraph>{event.description}</Paragraph>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {activeView === '章节记忆' && (
              <div className="memory-card-list">
                {filtered.chapters.length === 0 ? <Empty description="暂无章节记忆" /> : filtered.chapters.map((ch: any) => (
                  <Card key={ch.id} size="small" className="memory-item-card">
                    <div className="memory-item-head">
                      <Text strong>第{ch.chapter_number}章 · {ch.title}</Text>
                      <Space wrap size={4}>
                        {ch.arc_name && <Tag color="blue">{ch.arc_name}</Tag>}
                        {ch.quality_score && <Tag color={ch.quality_score >= 7 ? 'green' : 'orange'}>{ch.quality_score}/10</Tag>}
                      </Space>
                    </div>
                    {ch.summary && <Paragraph>{ch.summary}</Paragraph>}
                    {ch.hook && <Paragraph><Text strong>钩子：</Text>{ch.hook}</Paragraph>}
                    {ch.story_state_snapshot && <Paragraph><Text strong>状态快照：</Text>{ch.story_state_snapshot}</Paragraph>}
                  </Card>
                ))}
              </div>
            )}

            {activeView === '风险' && (
              <div className="memory-card-list">
                {filtered.risks.length === 0 ? <Empty description="暂无风险" /> : filtered.risks.map((risk: any, index: number) => (
                  <Card key={`${risk.chapter_number}-${index}`} size="small" className="memory-item-card risk">
                    <div className="memory-item-head">
                      <Text strong>第{risk.chapter_number}章 · {risk.chapter_title}</Text>
                      {renderRisk(risk.severity)}
                    </div>
                    <Paragraph>{risk.issue}</Paragraph>
                  </Card>
                ))}
              </div>
            )}

            {activeView === '组织' && (
              <div className="memory-card-list">
                {filtered.factions.length === 0 ? <Empty description="暂无组织" /> : filtered.factions.map((faction: any) => (
                  <Card key={faction.id} size="small" className="memory-item-card">
                    <div className="memory-item-head">
                      <Text strong>{faction.name}</Text>
                      {faction.faction_type && <Tag>{faction.faction_type}</Tag>}
                    </div>
                    {faction.description && <Paragraph>{faction.description}</Paragraph>}
                    {faction.core_creed && <Paragraph><Text strong>核心信条：</Text>{faction.core_creed}</Paragraph>}
                    {faction.core_conflict_of_interest && <Paragraph><Text strong>利益冲突：</Text>{faction.core_conflict_of_interest}</Paragraph>}
                  </Card>
                ))}
              </div>
            )}
          </Card>
        </main>
      </div>
    </div>
  );
}
