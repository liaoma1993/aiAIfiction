import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Button, Card, Empty, Segmented, Spin, Tag, Timeline, Typography } from 'antd';
import {
  ApartmentOutlined,
  BranchesOutlined,
  ClockCircleOutlined,
  EnvironmentOutlined,
  FieldTimeOutlined,
  LeftOutlined,
  ReadOutlined,
} from '@ant-design/icons';
import { storyApi } from '@/services/projectApi';
import './LandscapePage.css';

const { Title, Text, Paragraph } = Typography;

const WORLD_SECTIONS = [
  { key: 'geography', title: '地理与场域', icon: EnvironmentOutlined },
  { key: 'social_structure', title: '社会结构', icon: ApartmentOutlined },
  { key: 'power_system', title: '能力/规则', icon: BranchesOutlined },
  { key: 'special_rules', title: '特殊规则', icon: FieldTimeOutlined },
];

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

function textValue(value: any): string {
  if (typeof value === 'string') return value;
  if (Array.isArray(value)) return value.join('；');
  if (value && typeof value === 'object') return Object.values(value).map(textValue).filter(Boolean).join('；');
  return '';
}

function WorldPanel({ section, world }: { section: any; world: any }) {
  const Icon = section.icon;
  const source = section.key === 'special_rules'
    ? { ...(world?.special_rules || {}), ...(world?.world_logic || {}) }
    : world?.[section.key] || {};
  const entries = Object.entries(source || {}).filter(([, value]) => textValue(value));

  return (
    <Card className="landscape-world-card" size="small">
      <div className="landscape-card-title">
        <Icon />
        <Text strong>{section.title}</Text>
      </div>
      {!entries.length ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无设定" />
      ) : (
        <div className="landscape-world-list">
          {entries.slice(0, 4).map(([key, val]) => (
            <div key={key} className="landscape-world-item">
              <Text className="landscape-world-key">{key}</Text>
              <Paragraph className="landscape-world-text">{textValue(val)}</Paragraph>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

function chapterState(ch: any) {
  const written = (ch.word_count || 0) > 0 || ch.status === 'written' || ch.status === 'completed';
  if (written) return { label: '已写', color: 'green' };
  return { label: '规划', color: 'default' };
}

function groupChaptersByArc(chapters: any[]) {
  const groups = new Map<string, any[]>();
  chapters.forEach((ch) => {
    const key = ch.arc_name || '未分弧线';
    groups.set(key, [...(groups.get(key) || []), ch]);
  });
  return Array.from(groups.entries()).map(([arcName, items]) => ({
    arcName,
    chapters: items,
    written: items.filter((ch) => (ch.word_count || 0) > 0 || ch.status === 'written' || ch.status === 'completed').length,
  }));
}

function pct(part: number, total: number) {
  if (!total) return 0;
  return Math.round((part / total) * 100);
}

export default function LandscapePage({ embedded = false }: { embedded?: boolean }) {
  const { projectId } = useParams<{ projectId: string }>();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [eventMode, setEventMode] = useState<'written' | 'planned' | 'all'>('written');
  const [expandedVolumes, setExpandedVolumes] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!projectId) return;
    storyApi.landscape(projectId).then(setData).finally(() => setLoading(false));
  }, [projectId]);

  const chapters = useMemo(
    () => (data?.volumes || []).flatMap((vol: any) => (vol.chapters || []).map((ch: any) => ({ ...ch, volume_title: vol.title }))),
    [data],
  );
  const writtenCount = chapters.filter((ch: any) => (ch.word_count || 0) > 0 || ch.status === 'written' || ch.status === 'completed').length;
  const plannedCount = Math.max(0, chapters.length - writtenCount);
  const eventNodes = data?.event_nodes || [];
  const visibleEvents = eventNodes.filter((event: any) => {
    if (eventMode === 'all') return true;
    if (eventMode === 'written') return event.status === 'written' || event.source === 'timeline';
    return event.status === 'planned';
  });

  if (!projectId) return null;
  if (loading) return <div className="landscape-loading"><Spin size="large" /></div>;

  const world = data?.world || {};
  const toggleVolume = (volumeId: string) => {
    setExpandedVolumes((prev) => {
      const next = new Set(prev);
      if (next.has(volumeId)) next.delete(volumeId);
      else next.add(volumeId);
      return next;
    });
  };

  return (
    <div className={`landscape-page ${embedded ? 'embedded' : ''}`}>
      {!embedded && (
        <header className="landscape-header">
          <Link to={`/projects/${projectId}`}><Button icon={<LeftOutlined />}>返回工作台</Button></Link>
          <div className="landscape-titleblock">
            <Title level={3}>小说景观</Title>
            <Text type="secondary">按世界设定、卷章地图和事件线查看当前小说结构。</Text>
          </div>
        </header>
      )}

      <section className="landscape-summary">
        <div className="landscape-stat">
          <Text type="secondary">分卷</Text>
          <strong>{data?.volumes?.length || 0}</strong>
        </div>
        <div className="landscape-stat">
          <Text type="secondary">章节</Text>
          <strong>{chapters.length}</strong>
        </div>
        <div className="landscape-stat">
          <Text type="secondary">已写</Text>
          <strong>{writtenCount}</strong>
        </div>
        <div className="landscape-stat">
          <Text type="secondary">规划</Text>
          <strong>{plannedCount}</strong>
        </div>
      </section>

      <section className="landscape-world-grid">
        {WORLD_SECTIONS.map((section) => <WorldPanel key={section.key} section={section} world={world} />)}
      </section>

      <section className="landscape-section">
        <div className="landscape-section-head">
          <div>
            <Title level={4}>卷章结构地图</Title>
            <Text type="secondary">用弧线进度和章节点阵查看结构，不默认铺开全部章节。</Text>
          </div>
        </div>
        {!data?.volumes?.length ? <Empty description="暂无卷章数据" /> : (
          <div className="landscape-volume-stack">
            {data.volumes.map((vol: any) => (
              <article key={vol.id} className="landscape-volume">
                <div className="landscape-volume-head">
                  <div>
                    <Text strong>卷{vol.volume_number} · {vol.title}</Text>
                    {vol.summary && <Paragraph className="landscape-volume-summary">{vol.summary}</Paragraph>}
                  </div>
                  <div className="landscape-volume-tags">
                    {vol.theme && <Tag color="blue">{vol.theme}</Tag>}
                    <Tag>第{vol.chapter_range?.[0] || '?'}-{vol.chapter_range?.[1] || '?'}章</Tag>
                    <Tag>{vol.chapters?.length || 0}章</Tag>
                    {!!vol.chapters?.length && (
                      <Button size="small" type="link" onClick={() => toggleVolume(vol.id)}>
                        {expandedVolumes.has(vol.id) ? '收起章节' : '展开章节'}
                      </Button>
                    )}
                  </div>
                </div>
                {(vol.chapters || []).length ? (
                  <>
                    <div className="landscape-arc-map">
                      {groupChaptersByArc(vol.chapters || []).map((group) => (
                        <div key={group.arcName} className="landscape-arc-row">
                          <div className="landscape-arc-info">
                            <Text strong>{group.arcName}</Text>
                            <Text type="secondary">{group.chapters[0]?.chapter_number}-{group.chapters[group.chapters.length - 1]?.chapter_number}章</Text>
                          </div>
                          <div className="landscape-arc-track">
                            <div className="landscape-arc-progress">
                              <span style={{ width: `${pct(group.written, group.chapters.length)}%` }} />
                            </div>
                            <div className="landscape-chapter-dots">
                              {group.chapters.map((ch: any) => {
                                const state = chapterState(ch);
                                return (
                                  <span
                                    key={ch.id}
                                    className={state.color === 'green' ? 'written' : ''}
                                    title={`第${ch.chapter_number}章 ${ch.title || ''} · ${state.label}`}
                                  />
                                );
                              })}
                            </div>
                          </div>
                          <div className="landscape-arc-count">
                            <strong>{group.written}</strong>
                            <Text type="secondary">/{group.chapters.length}</Text>
                          </div>
                        </div>
                      ))}
                    </div>
                    {expandedVolumes.has(vol.id) && (
                      <div className="landscape-chapter-grid">
                        {(vol.chapters || []).map((ch: any) => {
                          const state = chapterState(ch);
                          return (
                            <div key={ch.id} className={`landscape-chapter-card ${state.color === 'green' ? 'written' : ''}`}>
                              <div className="landscape-chapter-top">
                                <Text strong>第{ch.chapter_number}章</Text>
                                <Tag color={state.color}>{state.label}</Tag>
                              </div>
                              <Text className="landscape-chapter-title">{ch.title || '未命名章节'}</Text>
                              {ch.arc_name && <Tag className="landscape-arc-tag">{ch.arc_name}</Tag>}
                              <Paragraph className="landscape-chapter-summary">{ch.summary || ch.hook || '暂无摘要'}</Paragraph>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </>
                ) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="本卷还没有章节" />}
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="landscape-section">
        <div className="landscape-section-head">
          <div>
            <Title level={4}>关键事件景观线</Title>
            <Text type="secondary">正文事件和规划事件分开查看，避免把未写章节误认为已发生。</Text>
          </div>
          <Segmented
            value={eventMode}
            onChange={(value) => setEventMode(value as any)}
            options={[
              { label: '正文事件', value: 'written' },
              { label: '规划事件', value: 'planned' },
              { label: '全部', value: 'all' },
            ]}
          />
        </div>
        {!visibleEvents.length ? <Empty description="暂无关键事件" /> : (
          <Timeline
            className="landscape-event-timeline"
            items={visibleEvents.slice(0, 100).map((event: any) => ({
              dot: event.status === 'planned' ? <ClockCircleOutlined /> : <ReadOutlined />,
              children: (
                <div className="landscape-event-item">
                  <div className="landscape-event-meta">
                    {event.chapter_number ? <Text strong>第{event.chapter_number}章</Text> : <Text strong>{event.chapter_title}</Text>}
                    {event.arc_name && <Tag>{translateEventType(event.arc_name)}</Tag>}
                    <Tag color={event.status === 'planned' ? 'default' : 'green'}>{event.status === 'planned' ? '规划' : '正文'}</Tag>
                  </div>
                  <Paragraph className="landscape-event-label">{event.label}</Paragraph>
                  {!!event.characters?.length && (
                    <div className="landscape-event-characters">
                      {event.characters.slice(0, 4).map((name: string) => <Tag key={name}>{name}</Tag>)}
                    </div>
                  )}
                </div>
              ),
            }))}
          />
        )}
      </section>
    </div>
  );
}
