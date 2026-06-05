import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Typography, Spin, Button, Tag, Select, Empty } from 'antd';
import { LeftOutlined, ApartmentOutlined } from '@ant-design/icons';
import { volumeApi } from '@/services/projectApi';
import api from '@/services/api';

const { Title, Text, Paragraph } = Typography;

const ARC_COLORS: Record<string, string> = {
  '主线推进': '#1677ff', '角色深化': '#722ed1', '世界观展开': '#52c41a',
  '伏笔铺设': '#fa8c16', '节奏缓冲': '#8c8c8c', '高潮爆发': '#f5222d',
};

export default function NarrativeGraphPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [volumes, setVolumes] = useState<any[]>([]);
  const [selectedVolId, setSelectedVolId] = useState<string>('');
  const [graphData, setGraphData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [hoveredCh, setHoveredCh] = useState<any>(null);

  useEffect(() => {
    if (!projectId) return;
    volumeApi.list(projectId).then((vols) => {
      setVolumes(vols);
      if (vols.length > 0) {
        setSelectedVolId(vols[0].id);
      }
      setLoading(false);
    });
  }, [projectId]);

  useEffect(() => {
    if (!projectId || !selectedVolId) return;
    setLoading(true);
    api.get(`/projects/${projectId}/wizard/narrative-graph/${selectedVolId}`)
      .then((r) => setGraphData(r.data))
      .finally(() => setLoading(false));
  }, [projectId, selectedVolId]);

  const getArcColor = (func: string) => ARC_COLORS[func] || '#1677ff';

  const tensionColor = (level: number) =>
    level >= 8 ? '#f5222d' : level >= 6 ? '#fa8c16' : level >= 4 ? '#1677ff' : '#8c8c8c';

  if (!projectId) return null;

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: '#f5f5f5' }}>
      {/* Header */}
      <div style={{ padding: '12px 24px', background: '#fff', borderBottom: '1px solid #e8e8e8', display: 'flex', alignItems: 'center', gap: 16, flexShrink: 0 }}>
        <Link to={`/projects/${projectId}`}><Button icon={<LeftOutlined />}>返回工作台</Button></Link>
        <ApartmentOutlined style={{ fontSize: 20, color: '#1677ff' }} />
        <Title level={4} style={{ margin: 0 }}>叙事图</Title>
        {volumes.length > 1 && (
          <Select value={selectedVolId} onChange={setSelectedVolId} style={{ width: 200 }}
            options={volumes.map((v) => ({ label: `卷${v.volume_number} · ${v.title}`, value: v.id }))} />
        )}
        {graphData && (
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'center' }}>
            {graphData.arcs?.map((arc: any, ai: number) => (
              <Tag key={ai} color={getArcColor(arc.narrative_function)} style={{ fontSize: 11 }}>
                {arc.name} · {arc.chapters?.length || 0}章
              </Tag>
            ))}
          </div>
        )}
      </div>

      {/* Body */}
      <div style={{ flex: 1, overflow: 'auto', padding: 24 }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>
        ) : !graphData ? (
          <Empty description="该卷暂无章节数据" />
        ) : (
          <div>
            {/* Arc legend overview */}
            <div style={{ display: 'flex', gap: 16, marginBottom: 24, flexWrap: 'wrap' }}>
              {graphData.arcs?.map((arc: any, ai: number) => (
                <div key={ai} style={{
                  flex: '1 1 200px', minWidth: 180, padding: 16, borderRadius: 12,
                  background: '#fff', borderLeft: `4px solid ${getArcColor(arc.narrative_function)}`,
                  boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
                }}>
                  <Text strong style={{ fontSize: 14, color: getArcColor(arc.narrative_function) }}>{arc.name}</Text>
                  <div style={{ display: 'flex', gap: 4, marginTop: 4, flexWrap: 'wrap' }}>
                    <Tag color="blue" style={{ fontSize: 10 }}>{arc.narrative_function}</Tag>
                    {arc.emotional_color && <Tag color="purple" style={{ fontSize: 10 }}>{arc.emotional_color}</Tag>}
                    <Tag style={{ fontSize: 10 }}>{arc.chapters?.length || 0}章</Tag>
                  </div>
                  {arc.tension_curve && (
                    <Text type="secondary" style={{ fontSize: 10, display: 'block', marginTop: 4 }}>📈 {arc.tension_curve}</Text>
                  )}
                </div>
              ))}
            </div>

            {/* Arc swimlanes */}
            {graphData.arcs?.map((arc: any, ai: number) => {
              const color = getArcColor(arc.narrative_function);
              return (
                <div key={ai} style={{ marginBottom: 32 }}>
                  {/* Arc lane header */}
                  <div style={{
                    display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12,
                    padding: '8px 16px', borderRadius: '8px 8px 0 0',
                    background: `${color}08`, borderLeft: `4px solid ${color}`,
                  }}>
                    <Text strong style={{ fontSize: 14, color }}>📌 {arc.name}</Text>
                    <Tag color="blue" style={{ fontSize: 10 }}>{arc.narrative_function}</Tag>
                    {arc.emotional_color && <Tag color="purple" style={{ fontSize: 10 }}>{arc.emotional_color}</Tag>}
                  </div>

                  {/* Chapter cards row */}
                  <div style={{ display: 'flex', gap: 12, overflowX: 'auto', padding: '8px 4px 16px' }}>
                    {arc.chapters?.map((ch: any, ci: number) => (
                      <div key={ci}
                        onMouseEnter={() => setHoveredCh(ch)}
                        onMouseLeave={() => setHoveredCh(null)}
                        style={{
                          minWidth: 220, maxWidth: 260, flexShrink: 0,
                          transition: 'transform 0.2s, box-shadow 0.2s',
                          transform: hoveredCh?.id === ch.id ? 'translateY(-4px)' : 'none',
                        }}>
                        <div style={{
                          background: '#fff', borderRadius: 10, padding: 14,
                          border: `2px solid ${color}20`, borderTop: `4px solid ${color}`,
                          boxShadow: hoveredCh?.id === ch.id ? '0 4px 16px rgba(0,0,0,0.1)' : '0 1px 4px rgba(0,0,0,0.04)',
                          cursor: 'default', height: '100%',
                          opacity: ch.has_content ? 1 : 0.45,
                        }}>
                          {/* Chapter number & tension */}
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                            <Text strong style={{ fontSize: 12, color }}>第{ch.chapter_number}章</Text>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                              <div style={{ width: 36, height: 4, borderRadius: 2, background: '#f0f0f0' }}>
                                <div style={{
                                  width: `${ch.tension_level * 10}%`, height: '100%', borderRadius: 2,
                                  background: tensionColor(ch.tension_level), transition: 'width 0.3s',
                                }} />
                              </div>
                              <Text style={{ fontSize: 10, color: tensionColor(ch.tension_level), fontWeight: 600 }}>
                                {ch.tension_level}
                              </Text>
                            </div>
                          </div>

                          {/* Title */}
                          <Text style={{ fontSize: 11, display: 'block', marginBottom: 6, fontWeight: 500 }}>
                            {ch.title || `第${ch.chapter_number}章`}
                          </Text>

                          {/* Events */}
                          {ch.key_events?.length > 0 && (
                            <div style={{ marginBottom: 6 }}>
                              {ch.key_events.slice(0, 3).map((e: string, ei: number) => (
                                <div key={ei} style={{ display: 'flex', alignItems: 'flex-start', gap: 4, marginBottom: 2 }}>
                                  <span style={{ color: '#f5222d', fontSize: 10, flexShrink: 0 }}>⚡</span>
                                  <Text style={{ fontSize: 9, color: '#595959', lineHeight: 1.4 }}>
                                    {e.length > 35 ? e.slice(0, 35) + '…' : e}
                                  </Text>
                                </div>
                              ))}
                            </div>
                          )}

                          {/* Characters */}
                          {ch.characters_in_chapter?.length > 0 && (
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 2, marginBottom: 6 }}>
                              {ch.characters_in_chapter.map((c: string, ci2: number) => (
                                <span key={ci2} style={{
                                  fontSize: 9, padding: '1px 6px', borderRadius: 10,
                                  background: `${color}10`, color, border: `1px solid ${color}30`,
                                }}>{c}</span>
                              ))}
                            </div>
                          )}

                          {/* Hook */}
                          {ch.hook && (
                            <div style={{
                              borderLeft: `2px solid ${color}60`, paddingLeft: 6, marginTop: 6,
                              background: `${color}04`, borderRadius: '0 4px 4px 0',
                            }}>
                              <Text style={{ fontSize: 8, color: '#8c8c8c' }}>🪝 {ch.hook.length > 45 ? ch.hook.slice(0, 45) + '…' : ch.hook}</Text>
                            </div>
                          )}

                          {/* Badges */}
                          <div style={{ display: 'flex', gap: 4, marginTop: 6 }}>
                            {ch.is_key_chapter && <Tag color="red" style={{ fontSize: 8, lineHeight: '14px', margin: 0 }}>关键章</Tag>}
                            {!ch.has_content && <Tag style={{ fontSize: 8, lineHeight: '14px', margin: 0 }}>未写</Tag>}
                            {ch.word_count > 0 && (
                              <Text type="secondary" style={{ fontSize: 9 }}>{Math.round(ch.word_count / 1000)}k字</Text>
                            )}
                          </div>
                        </div>

                        {/* Down arrow */}
                        {ci < (arc.chapters?.length || 0) - 1 && (
                          <div style={{ textAlign: 'center', padding: '6px 0 0' }}>
                            <svg width="20" height="16" viewBox="0 0 20 16">
                              <line x1="10" y1="0" x2="10" y2="12" stroke={color} strokeWidth="2" strokeOpacity="0.5" />
                              <polyline points="4,8 10,14 16,8" fill="none" stroke={color} strokeWidth="2" strokeOpacity="0.5" />
                            </svg>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>

                  {/* Arc connector */}
                  {ai < (graphData.arcs?.length || 0) - 1 && (
                    <div style={{
                      textAlign: 'center', padding: '16px 0', marginBottom: 8,
                      borderTop: '2px dashed #d9d9d9',
                    }}>
                      <div style={{
                        display: 'inline-flex', alignItems: 'center', gap: 8,
                        padding: '4px 16px', borderRadius: 20, background: '#fafafa',
                      }}>
                        <div style={{ width: 8, height: 8, borderRadius: '50%', background: color }} />
                        <Text type="secondary" style={{ fontSize: 11 }}>
                          承接下一弧线 → {graphData.arcs[ai + 1]?.name}
                        </Text>
                        <div style={{ width: 8, height: 8, borderRadius: '50%', background: getArcColor(graphData.arcs[ai + 1]?.narrative_function) }} />
                      </div>
                    </div>
                  )}
                </div>
              );
            })}

            {/* Tension overview chart */}
            {graphData.all_chapters?.length > 0 && (
              <div style={{
                marginTop: 32, padding: 20, borderRadius: 12, background: '#fff',
                boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
              }}>
                <Text strong style={{ fontSize: 14, display: 'block', marginBottom: 12 }}>📈 全卷张力走势</Text>
                <div style={{ display: 'flex', alignItems: 'flex-end', gap: 2, height: 80, overflowX: 'auto', paddingBottom: 8 }}>
                  {graphData.all_chapters.map((ch: any, ci: number) => (
                    <div key={ci} title={`第${ch.chapter_number}章 张力${ch.tension_level}`} style={{
                      flex: '1 1 16px', minWidth: 12, maxWidth: 30,
                      height: `${ch.tension_level * 10}%`,
                      background: tensionColor(ch.tension_level),
                      borderRadius: '2px 2px 0 0',
                      transition: 'height 0.3s',
                      cursor: 'pointer',
                    }} />
                  ))}
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
                  <Text type="secondary" style={{ fontSize: 10 }}>第{graphData.all_chapters[0]?.chapter_number}章</Text>
                  <Text type="secondary" style={{ fontSize: 10 }}>第{graphData.all_chapters[graphData.all_chapters.length - 1]?.chapter_number}章</Text>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
