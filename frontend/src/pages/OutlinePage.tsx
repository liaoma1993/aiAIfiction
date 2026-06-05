import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Alert, Button, Card, Collapse, Empty, Input, message, Modal, Popconfirm, Progress, Radio, Space, Spin, Tag, Tooltip, Typography } from 'antd';
import {
  AuditOutlined, BookOutlined, BranchesOutlined, CheckOutlined, CloseOutlined, DeleteOutlined,
  EditOutlined, FileTextOutlined, LeftOutlined, NodeIndexOutlined, ReadOutlined, ThunderboltOutlined,
  SendOutlined,
} from '@ant-design/icons';
import { volumeApi, chapterApi, projectApi, wizardApi } from '@/services/projectApi';
import api from '@/services/api';
import './OutlinePage.css';

const { Title, Paragraph, Text } = Typography;

export default function OutlinePage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [volumes, setVolumes] = useState<any[]>([]);
  const [chapters, setChapters] = useState<any[]>([]);
  const [project, setProject] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [expandLoading, setExpandLoading] = useState<string | null>(null);
  const [expandModalOpen, setExpandModalOpen] = useState(false);
  const [expandVol, setExpandVol] = useState<any>(null);
  const [expandMode, setExpandMode] = useState<'arc' | 'chapters'>('arc');
  const [expandArcIndex, setExpandArcIndex] = useState(0);
  const [expandConfig, setExpandConfig] = useState({ pacing: 'medium', event_density: 'medium', expansion_scale: 'standard' });
  const [editingField, setEditingField] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const [activeVolTab, setActiveVolTab] = useState<string>('');
  const [structureReview, setStructureReview] = useState<any>(null);
  const [reviewOpen, setReviewOpen] = useState(false);
  const [reviewingStructure, setReviewingStructure] = useState(false);
  const [adjustModalOpen, setAdjustModalOpen] = useState(false);
  const [adjustVol, setAdjustVol] = useState<any>(null);
  const [adjustArcIndex, setAdjustArcIndex] = useState<number | null>(null);
  const [adjustScope, setAdjustScope] = useState<'summary_only' | 'outline'>('outline');
  const [adjustInstruction, setAdjustInstruction] = useState('');
  const [adjustingOutline, setAdjustingOutline] = useState(false);
  const [adjustMessages, setAdjustMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string }>>([]);
  const [adjustChatInput, setAdjustChatInput] = useState('');
  const [adjustChatLoading, setAdjustChatLoading] = useState(false);
  const [adjustBackendOutdated, setAdjustBackendOutdated] = useState(false);

  const loadData = () => {
    if (!projectId) return;
    Promise.all([projectApi.get(projectId), volumeApi.list(projectId), chapterApi.list(projectId)])
      .then(([p, vols, chs]) => { setProject(p); setVolumes(vols); setChapters(chs); setLoading(false); });
  };

  useEffect(() => { loadData(); }, [projectId]);

  const startEdit = (field: string, currentValue: string) => {
    setEditingField(field);
    setEditValue(currentValue);
  };

  const saveEdit = async () => {
    if (!projectId || !editingField) return;
    try {
      const [type, id, key] = editingField.split(':');
      if (type === 'project') {
        const storyBrief = project?.story_brief || '';
        const idx = storyBrief.indexOf('【全书大纲】');
        const prefix = idx >= 0 ? storyBrief.slice(0, idx + 6) : '';
        const newBrief = prefix ? (prefix + '\n' + editValue) : editValue;
        await projectApi.update(projectId, { story_brief: newBrief });
        loadData();
      } else if (type === 'volume') {
        await volumeApi.update(projectId, id, { [key]: editValue });
        loadData();
      }
      message.success('已保存');
    } catch { message.error('保存失败'); }
    setEditingField(null);
  };

  const openExpandModal = (vol: any) => {
    setExpandVol(vol);
    setExpandMode('arc');
    setExpandModalOpen(true);
  };

  const openArcExpandModal = (vol: any, arcIndex: number) => {
    setExpandVol(vol);
    setExpandArcIndex(arcIndex);
    setExpandMode('chapters');
    setExpandConfig({ pacing: 'medium', event_density: 'medium', expansion_scale: 'standard' });
    setExpandModalOpen(true);
  };

  const doExpand = async () => {
    if (!projectId || !expandVol) return;
    setExpandModalOpen(false);
    try {
      if (expandMode === 'arc') {
        setExpandLoading(expandVol.id);
        const res = await api.post(`/projects/${projectId}/wizard/expand-volume-arcs/${expandVol.id}`);
        await pollTask(projectId, res.data.task_id, 60);
        const vols = await volumeApi.list(projectId);
        setVolumes(vols);
        message.success({ content: '弧线已生成', key: 'exp' });
        setExpandLoading(null);
      } else {
        setExpandLoading(`${expandVol.id}-${expandArcIndex}`);
        const res = await api.post(`/projects/${projectId}/wizard/expand-arc-chapters/${expandVol.id}`, {
          arc_index: expandArcIndex, ...expandConfig,
        });
        await pollTask(projectId, res.data.task_id, 120);
        const chs = await chapterApi.list(projectId);
        setChapters(chs);
        message.success({ content: '章节已展开', key: 'exp' });
        setExpandLoading(null);
      }
    } catch (e: any) { message.error({ content: e.message || '操作失败', key: 'exp' }); setExpandLoading(null); }
  };

  const batchWriteArc = async (vol: any, arcIndex: number) => {
    if (!projectId) return;
    const arc = vol.narrative_arcs?.[arcIndex];
    if (!arc) return;
    const arcChapters = chapters.filter((c: any) => c.volume_id === vol.id && c.arc_name === arc.name);
    const todo = arcChapters.filter((c: any) => !c.content);
    if (todo.length === 0) { message.info('该弧线所有章节已有内容'); return; }

    setExpandLoading(`${vol.id}-batch-${arcIndex}`);
    let done = 0;
    message.loading({ content: `正在写第1/${todo.length}章…`, key: 'batch', duration: 0 });

    for (const ch of todo) {
      try {
        const res = await api.post(`/projects/${projectId}/wizard/write-chapter/${ch.id}`);
        await pollTask(projectId, res.data.task_id, 180);
        done++;
        const chs = await chapterApi.list(projectId);
        setChapters(chs);
        message.loading({ content: `已完成 ${done}/${todo.length} 章`, key: 'batch', duration: 2 });
      } catch (e: any) {
        message.error({ content: `第${ch.chapter_number}章失败`, key: 'batch' });
        setExpandLoading(null);
        return;
      }
    }
    message.success({ content: `全部 ${done} 章完成`, key: 'batch' });
    setExpandLoading(null);
  };

  const reviewStructure = async () => {
    if (!projectId) return;
    setReviewingStructure(true);
    try {
      const res = await wizardApi.reviewProjectStructure(projectId);
      const result = await pollTask(projectId, res.task_id, 120);
      setStructureReview(result);
      setReviewOpen(true);
    } catch (e: any) {
      message.error(e.message || '结构审计失败');
    }
    setReviewingStructure(false);
  };

  const openAdjustModal = (vol: any, arcIndex: number | null = null, scope: 'summary_only' | 'outline' = 'outline') => {
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
    const key = 'outline-adjust-chat';
    try {
      const res = await api.post(`/projects/${projectId}/wizard/adjust-outline-chat/${adjustVol.id}`, {
        messages: nextMessages,
        arc_index: adjustArcIndex,
        adjust_scope: adjustScope,
      });
      message.loading({ content: 'AI 正在整理你的调整意见…', key, duration: 0 });
      const result = await pollTask(projectId, res.data.task_id, 60);
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
    try {
      const res = await api.post(`/projects/${projectId}/wizard/adjust-outline/${adjustVol.id}`, {
        instruction: adjustInstruction,
        arc_index: adjustArcIndex,
        adjust_scope: adjustScope,
        apply: true,
      });
      message.loading({ content: adjustScope === 'summary_only' ? 'AI 正在调整卷故事大概…' : 'AI 正在按已写内容调整大纲…', key: 'adjust-outline', duration: 0 });
      const result = await pollTask(projectId, res.data.task_id, 120);
      const [vols, chs] = await Promise.all([volumeApi.list(projectId), chapterApi.list(projectId)]);
      setVolumes(vols);
      setChapters(chs);
      setAdjustModalOpen(false);
      const warnings = result?.warnings?.length ? `，提示 ${result.warnings.length} 条` : '';
      message.success({ content: adjustScope === 'summary_only' ? `故事大概已调整${warnings}` : `大纲已调整${warnings}`, key: 'adjust-outline' });
    } catch (e: any) {
      message.error({ content: e.message || '调整失败', key: 'adjust-outline' });
    }
    setAdjustingOutline(false);
  };

  if (loading) return <div style={{ textAlign: 'center', padding: 48 }}><Spin size="large" /></div>;

  const EditableBlock = ({ field, value, label, rows = 4 }: { field: string; value: string; label?: string; rows?: number }) => {
    const isEditing = editingField === field;
    return isEditing ? (
      <div style={{ marginBottom: 8 }}>
        <Input.TextArea value={editValue} onChange={(e) => setEditValue(e.target.value)} rows={rows} autoSize={{ minRows: rows, maxRows: 20 }}
          style={{ fontSize: 13, lineHeight: 1.8 }} />
        <div style={{ marginTop: 4, display: 'flex', gap: 4 }}>
          <Button size="small" type="primary" icon={<CheckOutlined />} onClick={saveEdit}>保存</Button>
          <Button size="small" icon={<CloseOutlined />} onClick={() => setEditingField(null)}>取消</Button>
        </div>
      </div>
    ) : (
      <div style={{ marginBottom: 8 }}>
        {label && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 4 }}>
            <Text strong style={{ fontSize: 13 }}>{label}</Text>
            <Button size="small" type="link" icon={<EditOutlined />} onClick={() => startEdit(field, value || '')}
              style={{ fontSize: 11, padding: 0 }}>编辑</Button>
          </div>
        )}
        <Paragraph style={{ fontSize: 13, whiteSpace: 'pre-wrap', lineHeight: 1.8, margin: 0 }}>{value || '(空)'}</Paragraph>
        {!label && (
          <Button size="small" type="link" icon={<EditOutlined />} onClick={() => startEdit(field, value || '')}
            style={{ fontSize: 11, padding: 0, display: 'block', marginTop: 2 }}>编辑</Button>
        )}
      </div>
    );
  };

  const storyOverview = (() => {
    if (!project?.story_brief) return '';
    const idx = project.story_brief.indexOf('【全书大纲】');
    return idx >= 0 ? project.story_brief.slice(idx + 6).trim() : '';
  })();

  const expandVolObj = expandVol ? volumes.find((v: any) => v.id === expandVol?.id) : null;

  const VolumeContent = ({ v }: { v: any }) => {
    const volChapters = chapters.filter((c: any) => c.volume_id === v.id);
    const arcs = v.narrative_arcs || [];
    const hasArcs = arcs.length > 0;
    const writtenCount = volChapters.filter((c: any) => c.content).length;
    const progress = volChapters.length ? Math.round((writtenCount / volChapters.length) * 100) : 0;

    return (
      <div className="outline-volume-detail">
        <div className="outline-volume-head">
          <div className="outline-title-stack">
            <div className="outline-eyebrow">第 {v.volume_number} 卷</div>
            <div className="outline-volume-title">
              <BookOutlined />
              <span>{v.title}</span>
              <Tooltip title="编辑卷名">
                <Button size="small" type="text" icon={<EditOutlined />} onClick={() => startEdit(`volume:${v.id}:title`, v.title)} />
              </Tooltip>
            </div>
          </div>
          <div className="outline-volume-actions">
            <Button size="small" icon={<FileTextOutlined />} onClick={() => openAdjustModal(v, null, 'summary_only')}>AI调整故事大概</Button>
            <Button size="small" icon={<ThunderboltOutlined />} onClick={() => openAdjustModal(v)}>AI调整本卷</Button>
            <Popconfirm title="删除此卷及所有章节？" onConfirm={() => { volumeApi.remove(projectId!, v.id); setVolumes(volumes.filter(x => x.id !== v.id)); message.success('已删除'); }}>
              <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
            </Popconfirm>
          </div>
        </div>

        <div className="outline-meta-grid">
          <div className="outline-meta-item">
            <span>章节进度</span>
            <strong>{writtenCount}/{volChapters.length || v.chapter_count || 0}</strong>
            <Progress percent={progress} size="small" showInfo={false} />
          </div>
          <div className="outline-meta-item">
            <span>目标字数</span>
            <strong>{((v.target_words || 0) / 10000).toFixed(1)} 万</strong>
          </div>
          <div className="outline-meta-item">
            <span>弧线数量</span>
            <strong>{arcs.length}</strong>
          </div>
          <div className="outline-meta-item editable">
            <span>主题</span>
            {editingField === `volume:${v.id}:theme` ? (
              <div className="outline-inline-edit">
                <Input size="small" value={editValue} onChange={(e) => setEditValue(e.target.value)} />
                <Button size="small" type="primary" icon={<CheckOutlined />} onClick={saveEdit} />
                <Button size="small" icon={<CloseOutlined />} onClick={() => setEditingField(null)} />
              </div>
            ) : (
              <button onClick={() => startEdit(`volume:${v.id}:theme`, v.theme || '')}>{v.theme || '未设置'}</button>
            )}
          </div>
          <div className="outline-meta-item editable wide">
            <span>情绪弧线</span>
            {editingField === `volume:${v.id}:emotional_arc_description` ? (
              <div className="outline-inline-edit">
                <Input size="small" value={editValue} onChange={(e) => setEditValue(e.target.value)} />
                <Button size="small" type="primary" icon={<CheckOutlined />} onClick={saveEdit} />
                <Button size="small" icon={<CloseOutlined />} onClick={() => setEditingField(null)} />
              </div>
            ) : (
              <button onClick={() => startEdit(`volume:${v.id}:emotional_arc_description`, v.emotional_arc_description || '')}>
                {v.emotional_arc_description || '未设置'}
              </button>
            )}
          </div>
        </div>

        <div className="outline-text-grid">
          {v.summary && (
            <Card size="small" title={<span><FileTextOutlined /> 卷概要</span>} className="outline-text-panel">
              <EditableBlock field={`volume:${v.id}:summary`} value={v.summary} rows={3} />
            </Card>
          )}
          <Card size="small" title={<span><ReadOutlined /> 卷大纲</span>} className="outline-text-panel">
            <EditableBlock field={`volume:${v.id}:outline`} value={v.outline || ''} rows={5} />
          </Card>
        </div>

        {hasArcs ? (
          <div className="outline-arcs">
            <div className="outline-section-head">
              <div>
                <Text strong>故事弧线</Text>
                <div className="outline-section-sub">按叙事单元查看弧线、章节、蓝图和因果链</div>
              </div>
              <Button size="small" icon={<BranchesOutlined />} onClick={() => openExpandModal(v)} loading={expandLoading === v.id}>重拆弧线</Button>
            </div>
            {arcs.map((arc: any, ai: number) => {
              const arcChapters = volChapters.filter((c: any) => c.arc_name === arc.name);
              const arcWritten = arcChapters.filter((c: any) => c.content).length;
              return (
                <Card key={ai} size="small" className="outline-arc-card">
                  <div className="outline-arc-head">
                    <div className="outline-arc-title">
                      <NodeIndexOutlined />
                      <span>{arc.name || `弧线 ${ai + 1}`}</span>
                    </div>
                    <div className="outline-arc-tags">
                      {arc.narrative_function && <Tag color="blue">{arc.narrative_function}</Tag>}
                      {arc.emotional_color && <Tag color="purple">{arc.emotional_color}</Tag>}
                      <Tag>{arcWritten}/{arcChapters.length}章已写</Tag>
                      <Button size="small" icon={<ThunderboltOutlined />} onClick={() => openAdjustModal(v, ai)}>AI调整</Button>
                    </div>
                  </div>
                  <Paragraph className="outline-arc-desc">{arc.description || '暂无弧线描述'}</Paragraph>
                  {arc.tension_curve && (
                    <div className="outline-tension-curve">
                      <span>张力曲线</span>
                      <p>{arc.tension_curve}</p>
                    </div>
                  )}
                  {arc.key_milestones?.length > 0 && (
                    <Paragraph className="outline-milestones">
                      关键节点：{arc.key_milestones.map((m: any) => typeof m === 'string' ? m : (m.name || m.stage || '')).filter(Boolean).join(' → ')}
                    </Paragraph>
                  )}
                  {arcChapters.length === 0 ? (
                    <Button type="dashed" icon={<ThunderboltOutlined />}
                      loading={expandLoading === `${v.id}-${ai}`}
                      onClick={() => openArcExpandModal(v, ai)}>展开章节</Button>
                  ) : (
                    <div>
                      <div className="outline-arc-actions">
                        <Button type="dashed" size="small" icon={<ThunderboltOutlined />}
                          loading={expandLoading === `${v.id}-${ai}`}
                          onClick={() => openArcExpandModal(v, ai)}>重新展开</Button>
                        <Button type="dashed" size="small" icon={<EditOutlined />}
                          loading={expandLoading === `${v.id}-batch-${ai}`}
                          onClick={() => batchWriteArc(v, ai)}>批量写全部</Button>
                      </div>
                      <Collapse size="small" className="outline-chapter-collapse"
                        items={arcChapters.map((ch: any) => ({
                          key: ch.id,
                          label: (
                            <div className="outline-chapter-row">
                              <span><Text strong>第{ch.chapter_number}章</Text> {ch.title}</span>
                              <Tag color={ch.content ? 'green' : 'default'}>{ch.content ? '已写' : '待写'}</Tag>
                            </div>
                          ),
                          children: (
                            <div className="outline-chapter-detail">
                              {ch.summary && <Paragraph style={{ marginBottom: 8 }}>{ch.summary}</Paragraph>}
                              {ch.blueprint && Object.keys(ch.blueprint).length > 0 && (
                                <Card size="small" title="章节蓝图" className="outline-blueprint-card">
                                  {ch.blueprint.opening_state && <Paragraph style={{ marginBottom: 4 }}><Text strong>开场：</Text>{ch.blueprint.opening_state}</Paragraph>}
                                  {ch.blueprint.main_conflict && <Paragraph style={{ marginBottom: 4 }}><Text strong>冲突：</Text>{ch.blueprint.main_conflict}</Paragraph>}
                                  {ch.blueprint.turning_point && <Paragraph style={{ marginBottom: 4 }}><Text strong>转折：</Text>{ch.blueprint.turning_point}</Paragraph>}
                                  {ch.blueprint.ending_hook && <Paragraph style={{ marginBottom: 4 }}><Text strong>钩子：</Text>{ch.blueprint.ending_hook}</Paragraph>}
                                  {ch.blueprint.must_include?.length > 0 && <div style={{ marginBottom: 4 }}><Text strong>必含：</Text>{ch.blueprint.must_include.map((x: string, i: number) => <Tag key={i}>{x}</Tag>)}</div>}
                                  {ch.blueprint.foreshadowing_tasks?.length > 0 && <div style={{ marginBottom: 4 }}><Text strong>伏笔任务：</Text>{ch.blueprint.foreshadowing_tasks.map((x: string, i: number) => <Tag color="purple" key={i}>{x}</Tag>)}</div>}
                                </Card>
                              )}
                              {ch.rhythm_profile && Object.keys(ch.rhythm_profile).length > 0 && (
                                <div style={{ marginBottom: 6 }}>
                                  <Text strong>节奏画像：</Text>
                                  {Object.entries(ch.rhythm_profile).map(([k, val]: any) => <Tag key={k} color="blue">{k}:{String(val)}</Tag>)}
                                </div>
                              )}
                              {ch.causality_links?.length > 0 && (
                                <div style={{ marginBottom: 6 }}>
                                  <Text strong>因果链：</Text>
                                  {ch.causality_links.map((c: any, i: number) => <Tag key={i} color="orange">{c.cause || c.source} → {c.effect || c.target}</Tag>)}
                                </div>
                              )}
                              {ch.story_state_snapshot && <Paragraph className="outline-memory"><Text strong>记忆快照：</Text>{ch.story_state_snapshot.slice(0, 500)}</Paragraph>}
                            </div>
                          ),
                        }))}
                      />
                    </div>
                  )}
                </Card>
              );
            })}
          </div>
        ) : (
          <Button type="dashed" icon={<ThunderboltOutlined />} loading={expandLoading === v.id}
            onClick={() => openExpandModal(v)} block className="outline-empty-action">展开弧线</Button>
        )}
      </div>
    );
  };

  const activeVolume = volumes.find((v: any) => v.id === (activeVolTab || volumes[0]?.id)) || volumes[0];
  const writtenChapters = chapters.filter((c: any) => c.content).length;
  const totalWords = chapters.reduce((sum: number, ch: any) => sum + (ch.word_count || 0), 0);
  const totalTargetWords = volumes.reduce((sum: number, v: any) => sum + (v.target_words || 0), 0);

  return (
    <div className="outline-page">
      <div className="outline-topbar">
        <div className="outline-top-left">
          <Link to={`/projects/${projectId}`}><Button icon={<LeftOutlined />}>返回工作台</Button></Link>
          <div>
            <Title level={3} className="outline-page-title">大纲管理</Title>
            <div className="outline-page-subtitle">管理全书大纲、分卷弧线、章节蓝图和后续调整</div>
          </div>
        </div>
        <Button icon={<AuditOutlined />} loading={reviewingStructure} onClick={reviewStructure}>全书结构审计</Button>
      </div>

      {volumes.length === 0 ? (
        <Card className="outline-empty-card">
          <Empty description="尚未生成大纲，请先通过创作向导完成规划" />
        </Card>
      ) : (
        <div className="outline-layout">
          <aside className="outline-sidebar">
            <div className="outline-stats">
              <div><span>分卷</span><strong>{volumes.length}</strong></div>
              <div><span>章节</span><strong>{chapters.length}</strong></div>
              <div><span>已写</span><strong>{writtenChapters}</strong></div>
              <div><span>字数</span><strong>{(totalWords / 10000).toFixed(1)}万</strong></div>
            </div>
            <Progress percent={totalTargetWords ? Math.min(100, Math.round((totalWords / totalTargetWords) * 100)) : 0} size="small" />
            <div className="outline-volume-list">
              {volumes.map((v: any) => {
                const volChapters = chapters.filter((c: any) => c.volume_id === v.id);
                const volWritten = volChapters.filter((c: any) => c.content).length;
                const active = activeVolume?.id === v.id;
                return (
                  <button key={v.id} className={`outline-volume-nav ${active ? 'active' : ''}`} onClick={() => setActiveVolTab(v.id)}>
                    <span>卷{v.volume_number}</span>
                    <strong>{v.title}</strong>
                    <em>{volWritten}/{volChapters.length || v.chapter_count || 0} 章 · {((v.target_words || 0) / 10000).toFixed(1)}万字</em>
                  </button>
                );
              })}
            </div>
          </aside>

          <main className="outline-main">
            <Alert
              type="info"
              showIcon
              className="outline-info"
              message="章节展开后会展示蓝图、节奏画像、因果链和记忆快照；这些信息会参与后续章节生成。"
            />
          {storyOverview && (
            <Card size="small" className="outline-overview-card" title={<span><BookOutlined /> 全书大纲</span>}>
              <EditableBlock field="project:story" value={storyOverview} rows={6} />
            </Card>
          )}

            {activeVolume && <VolumeContent v={activeVolume} />}
          </main>
        </div>
      )}

      <Modal title={expandMode === 'arc' ? `展开弧线 · ${expandVol?.title || ''}` : `展开章节 · ${expandVolObj?.narrative_arcs?.[expandArcIndex]?.name || ''}`}
        open={expandModalOpen} onOk={doExpand} onCancel={() => setExpandModalOpen(false)} okText="开始生成" width={480}>
        {expandMode === 'arc' ? (
          <div style={{ marginTop: 16 }}>
            <Text>AI 将分析本卷结构，根据内容复杂度自行决定弧线数量。</Text>
            <Paragraph style={{ marginTop: 8, fontSize: 12, color: 'var(--text-secondary)' }}>
              每条弧线是一个完整的叙事单元，包含核心冲突和关键节点。之后逐条展开为详细章节。
            </Paragraph>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20, marginTop: 16 }}>
            <div>
              <Text strong>展开长度</Text>
              <Radio.Group value={expandConfig.expansion_scale} onChange={(e) => setExpandConfig({ ...expandConfig, expansion_scale: e.target.value })}
                style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap' }} buttonStyle="solid" size="small">
                <Radio.Button value="compact">短展开</Radio.Button>
                <Radio.Button value="standard">标准</Radio.Button>
                <Radio.Button value="long">长展开</Radio.Button>
                <Radio.Button value="detailed">细写</Radio.Button>
              </Radio.Group>
              <Paragraph style={{ marginTop: 6, marginBottom: 0, fontSize: 12, color: 'var(--text-secondary)' }}>
                只选择展开程度，系统会按弧线复杂度自动决定章节数量。
              </Paragraph>
            </div>
            <div>
              <Text strong>叙事节奏</Text>
              <Radio.Group value={expandConfig.pacing} onChange={(e) => setExpandConfig({ ...expandConfig, pacing: e.target.value })}
                style={{ display: 'flex', gap: 8, marginTop: 8 }} buttonStyle="solid" size="small">
                <Radio.Button value="slow">生活流</Radio.Button>
                <Radio.Button value="medium">适中</Radio.Button>
                <Radio.Button value="fast">紧凑</Radio.Button>
              </Radio.Group>
            </div>
            <div>
              <Text strong>事件密度</Text>
              <Radio.Group value={expandConfig.event_density} onChange={(e) => setExpandConfig({ ...expandConfig, event_density: e.target.value })}
                style={{ display: 'flex', gap: 8, marginTop: 8 }} buttonStyle="solid" size="small">
                <Radio.Button value="low">精简</Radio.Button>
                <Radio.Button value="medium">适中</Radio.Button>
                <Radio.Button value="high">丰富</Radio.Button>
              </Radio.Group>
            </div>
          </div>
        )}
      </Modal>
      <Modal title="全书结构审计" open={reviewOpen} onCancel={() => setReviewOpen(false)} footer={null} width={760}>
        {structureReview && (
          <div style={{ maxHeight: '70vh', overflow: 'auto' }}>
            <Title level={3} style={{ marginTop: 0 }}>{structureReview.overall_score}/10</Title>
            <Paragraph>{structureReview.summary}</Paragraph>
            {structureReview.structure_issues?.length > 0 && (
              <Card size="small" title="结构问题" style={{ marginBottom: 8 }}>
                {structureReview.structure_issues.map((i: any, idx: number) => (
                  <Alert key={idx} type={i.severity === '致命' ? 'error' : 'warning'} showIcon style={{ marginBottom: 8 }}
                    message={`${i.dimension || '结构'}：${i.description}`} description={i.fix_suggestion} />
                ))}
              </Card>
            )}
            {['missing_payoffs', 'weak_volumes', 'recommended_rewrites', 'next_actions'].map((key) => (
              structureReview[key]?.length > 0 && (
                <Card key={key} size="small" title={key} style={{ marginBottom: 8 }}>
                  <Space wrap>{structureReview[key].map((x: string, i: number) => <Tag key={i}>{x}</Tag>)}</Space>
                </Card>
              )
            ))}
          </div>
        )}
      </Modal>
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
        <div className="outline-adjust-dialog-grid">
          <div className="outline-adjust-chat-pane">
            <div className="outline-adjust-pane-title">对话沟通</div>
            <div className="outline-adjust-chat-list">
              {adjustMessages.map((m, idx) => (
                <div key={idx} className={`outline-adjust-chat-msg ${m.role}`}>
                  <span>{m.role === 'user' ? '你' : 'AI'}</span>
                  <p>{m.content}</p>
                </div>
              ))}
            </div>
            <Space size={[6, 6]} wrap className="outline-adjust-quick-row">
              {[
                '太文艺了，改得通俗易懂一点',
                '前20万字要更抓人',
                '主角目标和反派压力写清楚',
              ].map((text) => (
                <Button key={text} size="small" onClick={() => sendAdjustChatMessage(text)} disabled={adjustChatLoading}>{text}</Button>
              ))}
            </Space>
            <div className="outline-adjust-chat-input">
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
          <div className="outline-adjust-instruction-pane">
            <div className="outline-adjust-pane-title">最终调整要求</div>
            <Text type="secondary" style={{ fontSize: 12 }}>
              对话会自动整理到这里；点“开始调整”才会真正写入。
            </Text>
            <Input.TextArea
              value={adjustInstruction}
              onChange={(e) => setAdjustInstruction(e.target.value)}
              rows={10}
              autoSize={{ minRows: 10, maxRows: 16 }}
              style={{ marginTop: 8, lineHeight: 1.8 }}
              placeholder="例如：后半段节奏太散，加强主角和反派的正面对抗；不要改前面已写事实。"
            />
          </div>
        </div>
      </Modal>
    </div>
  );
}

async function pollTask(projectId: string, taskId: string, maxRetries: number) {
  for (let i = 0; i < maxRetries; i++) {
    await new Promise(r => setTimeout(r, 2000));
    const poll = await api.get(`/projects/${projectId}/wizard/task/${taskId}`);
    if (poll.data.status === 'completed') return poll.data.result;
    if (poll.data.status === 'failed') throw new Error(poll.data.error || '失败');
  }
  throw new Error('任务超时');
}
