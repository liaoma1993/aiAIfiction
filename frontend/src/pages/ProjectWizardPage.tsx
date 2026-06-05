import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Steps, Button, Card, Input, Slider, Typography, message, Tag, Row, Col, Spin, Descriptions, Progress, Modal, Alert } from 'antd';
import { ThunderboltOutlined, EditOutlined, CheckOutlined, LoadingOutlined } from '@ant-design/icons';
import { projectApi, volumeApi, characterApi, factionApi, chapterApi, worldSettingApi } from '@/services/projectApi';
import api from '@/services/api';

const LEGACY_ROLE_LABELS: Record<string, string> = {
  protagonist: '主角', antagonist: '反派', supporting: '配角', mentor: '导师', love_interest: '恋人',
  comic_relief: '搞笑', other: '其他', hero: '英雄', villain: '恶人', sidekick: '跟班', master: '师父',
};
const LEGACY_FACTION_LABELS: Record<string, string> = {
  sect: '宗门', family: '家族', empire: '帝国', guild: '商会', merchant_guild: '商会',
  dark_org: '暗组织', race: '种族', tribe: '部落', alliance: '联盟', temple: '神殿', academy: '学院', court: '朝廷',
};

const { Title, Paragraph } = Typography;

function useTaskPolling() {
  const [status, setStatus] = useState<'idle' | 'running' | 'completed' | 'failed'>('idle');
  const [error, setError] = useState('');
  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef(0);
  const activeRef = useRef(false);

  const clearTimer = useCallback(() => {
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
  }, []);

  const startPolling = useCallback((taskId: string, projectId: string) => {
    clearTimer();
    activeRef.current = true;
    startTimeRef.current = Date.now();
    setStatus('running');
    setError('');
    setElapsed(0);

    timerRef.current = setInterval(async () => {
      if (!activeRef.current) return;
      try {
        const res = await api.get(`/projects/${projectId}/wizard/task/${taskId}`);
        if (!activeRef.current) return;
        setElapsed(Math.round((Date.now() - startTimeRef.current) / 1000));
        if (res.data.status === 'completed') {
          clearTimer();
          activeRef.current = false;
          setStatus('completed');
        } else if (res.data.status === 'failed') {
          clearTimer();
          activeRef.current = false;
          setStatus('failed');
          setError(res.data.error || '生成失败');
        }
      } catch {
        if (!activeRef.current) return;
        clearTimer();
        activeRef.current = false;
        setStatus('failed');
        setError('轮询失败');
      }
    }, 2000);
  }, [clearTimer]);

  const stopPolling = useCallback(() => {
    activeRef.current = false;
    clearTimer();
  }, [clearTimer]);

  useEffect(() => () => stopPolling(), [stopPolling]);

  return { status, error, elapsed, startPolling, stopPolling };
}

export default function ProjectWizardPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [project, setProject] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!projectId) return;
    projectApi.get(projectId).then((p) => {
      setProject(p);
      if (p.wizard_step >= 4) {
        navigate(`/projects/${projectId}`);
        return;
      }
      setStep(p.wizard_step || 0);
      setLoading(false);
    });
  }, [projectId]);

  const updateProject = async (data: any) => {
    if (!projectId) return;
    const p = await projectApi.update(projectId, data);
    setProject(p);
  };

  const nextStep = () => {
    const next = step + 1;
    setStep(next);
    updateProject({ wizard_step: next });
  };

  if (loading) return <div style={{ padding: 48, textAlign: 'center' }}><Spin size="large" /></div>;
  if (!project) return <div style={{ padding: 48, textAlign: 'center' }}>项目不存在</div>;

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '32px 24px' }}>
      <Steps current={step} style={{ marginBottom: 40 }}
        items={[
          { title: '📖 故事设定', description: 'AI 生成书名梗概' },
          { title: '🌍 世界观', description: 'AI 生成六维设定' },
          { title: '👤 角色势力', description: 'AI 生成角色阵容' },
          { title: '📋 卷章大纲', description: 'AI 生成完整大纲' },
        ]} />
      {step === 0 && <StepStory project={project} update={updateProject} projectId={projectId!} onNext={nextStep} />}
      {step === 1 && <StepWorld project={project} projectId={projectId!} onNext={nextStep} />}
      {step === 2 && <StepCharacters projectId={projectId!} onNext={nextStep} />}
      {step === 3 && <StepOutline projectId={projectId!} project={project} onComplete={async () => { await updateProject({ status: 'writing' }); navigate(`/projects/${projectId}`); }} />}
    </div>
  );
}

function StepStory({ project, update, projectId, onNext }: any) {
  const [title, setTitle] = useState(project.title || '');
  const [totalWords, setTotalWords] = useState(project.target_total_words || 500000);
  const [storyBrief, setStoryBrief] = useState(project.story_brief || '');
  const [tags, setTags] = useState<string[]>(project.writing_style?.tags || []);
  const [regenerating, setRegenerating] = useState(false);
  const [editing, setEditing] = useState(false);

  const regenerate = async () => {
    setRegenerating(true);
    try {
      const res = await api.post(`/projects/${projectId}/wizard/suggest-stories`, { inspiration: project.story_brief, genres: project.genre });
      const taskId = res.data.task_id;
      await pollUntilDone(projectId, taskId);
      const data = await api.get(`/projects/${projectId}`);
      const p = data.data.project;
      setTitle(p.title || title);
      setStoryBrief(p.story_brief || storyBrief);
      setTags(p.writing_style?.tags || []);
      message.success('已重新生成');
    } catch { message.error('AI 生成失败'); }
    setRegenerating(false);
  };

  const handleConfirm = async () => {
    await update({ title, target_total_words: totalWords, story_brief: storyBrief, writing_style: { ...project.writing_style, tags } });
    onNext();
  };

  return (
    <Card style={{ borderRadius: 'var(--radius-lg)' }} title="📖 故事设定 — AI 已为你生成初稿">
      {!editing ? (
        <>
          <Title level={2} style={{ marginBottom: 4 }}>{title || '未命名项目'}</Title>
          <Tag color="blue">{project.genre}</Tag>
          <Paragraph style={{ marginTop: 16, fontSize: 16, lineHeight: 1.8, whiteSpace: 'pre-wrap' }}>{storyBrief || '暂未生成梗概'}</Paragraph>
          <div style={{ marginBottom: 16 }}>{tags.map((t: string) => <Tag key={t}>{t}</Tag>)}</div>
          <Paragraph>目标总字数：<strong>{(totalWords / 10000).toFixed(1)} 万字</strong></Paragraph>
          <div style={{ display: 'flex', gap: 12, marginTop: 24 }}>
            <Button type="primary" size="large" onClick={handleConfirm} icon={<CheckOutlined />}>确认，进入世界观</Button>
            <Button size="large" onClick={() => setEditing(true)} icon={<EditOutlined />}>手动调整</Button>
            <Button size="large" onClick={regenerate} loading={regenerating} icon={<ThunderboltOutlined />}>重新生成</Button>
          </div>
        </>
      ) : (
        <>
          <Paragraph>书名：</Paragraph>
          <Input value={title} onChange={(e) => setTitle(e.target.value)} size="large" style={{ marginBottom: 16 }} />
          <Paragraph>全书目标字数：{(totalWords / 10000).toFixed(0)}万字</Paragraph>
          <Slider min={50000} max={1000000} step={10000} value={totalWords} onChange={setTotalWords} marks={{ 50000: '5万', 500000: '50万', 1000000: '100万' }} style={{ marginBottom: 16 }} />
          <Paragraph>故事梗概：</Paragraph>
          <Input.TextArea value={storyBrief} onChange={(e) => setStoryBrief(e.target.value)} autoSize={{ minRows: 4 }} style={{ marginBottom: 16 }} />
          <div style={{ display: 'flex', gap: 12 }}><Button type="primary" onClick={handleConfirm}>确认</Button><Button onClick={() => setEditing(false)}>取消</Button></div>
        </>
      )}
    </Card>
  );
}

async function pollUntilDone(projectId: string, taskId: string, timeoutMs = 360000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    await new Promise((r) => setTimeout(r, 2000));
    try {
      const res = await api.get(`/projects/${projectId}/wizard/task/${taskId}`);
      if (res.data.status === 'completed') return res.data.result;
      if (res.data.status === 'failed') throw new Error(res.data.error || '生成失败');
    } catch (e: any) { if (e.message !== '生成失败') continue; throw e; }
  }
  throw new Error('生成超时');
}

function GeneratingCard({ title, description, elapsed }: { title: string; description?: string; elapsed: number }) {
  return (
    <Card style={{ borderRadius: 'var(--radius-lg)', textAlign: 'center', padding: 48 }}>
      <Spin size="large" indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />} />
      <Title level={4} style={{ marginTop: 24 }}>{title}</Title>
      <Progress percent={Math.floor(Math.min(99, (elapsed / 120) * 100))} status="active" showInfo={false} style={{ maxWidth: 300, margin: '16px auto' }} />
      <Paragraph type="secondary">{description || 'AI 正在调用大模型生成内容，请耐心等待…'}</Paragraph>
      <Paragraph type="secondary">已等待 {elapsed} 秒</Paragraph>
    </Card>
  );
}

function StepWorld({ project, projectId, onNext }: any) {
  const [worldSetting, setWorldSetting] = useState<any>(null);
  const { status, elapsed, startPolling, stopPolling } = useTaskPolling();
  const [coreTheme, setCoreTheme] = useState(project.core_theme || '');
  const [draft, setDraft] = useState<any>(null);
  const [draftOpen, setDraftOpen] = useState(false);
  const [drafting, setDrafting] = useState(false);
  const startedRef = useRef(false);

  const dims = [
    { key: 'geography', label: '地理环境', icon: '🌍' },
    { key: 'social_structure', label: '社会结构', icon: '🏛' },
    { key: 'power_system', label: '力量体系', icon: '⚡' },
    { key: 'history', label: '历史背景', icon: '📜' },
    { key: 'culture', label: '文化习俗', icon: '🎭' },
    { key: 'special_rules', label: '特殊规则', icon: '🔒' },
  ];
  const ruleBlocks = [
    { key: 'hard_rules', label: '硬约束', color: 'red', desc: '绝对不能违反的世界规则' },
    { key: 'tone_rules', label: '文风氛围', color: 'blue', desc: '用于保持世界质感和叙事风格' },
    { key: 'constraints', label: '生成限制', color: 'orange', desc: '写作时需要避开的内容或边界' },
  ];

  useEffect(() => {
    if (startedRef.current) return;
    worldSettingApi.get(projectId).then((ws) => {
      if (ws?.geography?.content) { setWorldSetting(ws); return; }
      startedRef.current = true;
      api.post(`/projects/${projectId}/wizard/generate-world`).then((res) => {
        startPolling(res.data.task_id, projectId);
      });
    });
  }, [projectId]);

  useEffect(() => {
    if (status !== 'completed') return;
    worldSettingApi.get(projectId).then(setWorldSetting);
  }, [status, projectId]);

  if (status === 'running' || (!worldSetting?.geography?.content && status !== 'completed')) {
    return <GeneratingCard title="AI 正在生成世界观" description="正在构建六维度世界观设定…" elapsed={elapsed} />;
  }

  const previewDraft = async () => {
    setDrafting(true);
    try {
      const res = await api.post(`/projects/${projectId}/wizard/generate-world-draft`);
      const data = await pollUntilDone(projectId, res.data.task_id);
      setDraft(data);
      setDraftOpen(true);
    } catch { message.error('生成草稿失败'); }
    setDrafting(false);
  };

  const applyDraft = async () => {
    try {
      await api.post(`/projects/${projectId}/wizard/apply-draft`, { draft_type: 'world', payload: draft });
      const updated = await worldSettingApi.get(projectId);
      setWorldSetting(updated);
      setDraftOpen(false);
      message.success('已采纳世界观草稿');
    } catch { message.error('采纳失败'); }
  };

  return (
    <Card style={{ borderRadius: 'var(--radius-lg)' }} title="🌍 世界观 — AI 已生成六维度设定">
      <Alert type="info" showIcon message="重新生成可先作为草稿预览，不会直接覆盖当前设定。" style={{ marginBottom: 16 }} />
      <Row gutter={[12, 12]} style={{ marginBottom: 24 }}>
        {dims.map((d) => (
          <Col xs={24} sm={12} md={8} key={d.key}>
            <Card size="small" style={{ borderRadius: 'var(--radius-md)', height: '100%' }} title={<>{d.icon} {d.label}</>}>
              <Paragraph style={{ fontSize: 13, whiteSpace: 'pre-wrap' }}>{worldSetting?.[d.key]?.content || '待生成'}</Paragraph>
            </Card>
          </Col>
        ))}
      </Row>
      <Row gutter={[12, 12]} style={{ marginBottom: 24 }}>
        {ruleBlocks.map((block) => (
          <Col xs={24} md={8} key={block.key}>
            <Card size="small" title={block.label} style={{ borderRadius: 'var(--radius-md)', height: '100%' }}>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>{block.desc}</div>
              {(worldSetting?.[block.key] || []).length ? (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {(worldSetting?.[block.key] || []).map((item: string, idx: number) => (
                    <Tag key={`${block.key}-${idx}`} color={block.color} style={{ whiteSpace: 'normal', lineHeight: '20px' }}>{item}</Tag>
                  ))}
                </div>
              ) : (
                <Paragraph style={{ fontSize: 13, color: 'var(--text-secondary)', margin: 0 }}>待生成</Paragraph>
              )}
            </Card>
          </Col>
        ))}
      </Row>
      <Paragraph>核心主题：</Paragraph>
      <Input value={coreTheme} onChange={(e) => setCoreTheme(e.target.value)} placeholder="如：自由 vs 责任" style={{ marginBottom: 24 }} />
      <div style={{ display: 'flex', gap: 12 }}>
        <Button type="primary" size="large" onClick={async () => { await projectApi.update(projectId, { core_theme: coreTheme }); onNext(); }} icon={<CheckOutlined />}>确认，进入角色设定</Button>
        <Button size="large" onClick={() => { setWorldSetting(null); startedRef.current = true; api.post(`/projects/${projectId}/wizard/generate-world`).then((res) => startPolling(res.data.task_id, projectId)); }} icon={<ThunderboltOutlined />}>重新生成</Button>
        <Button size="large" loading={drafting} onClick={previewDraft}>生成草稿预览</Button>
      </div>
      <Modal title="世界观草稿预览" open={draftOpen} onCancel={() => setDraftOpen(false)} onOk={applyDraft} okText="采纳草稿" width={760}>
        {draft && Object.keys(draft).map((key) => {
          const value = draft[key];
          return (
            <Card key={key} size="small" title={key} style={{ marginBottom: 8 }}>
              {Array.isArray(value) ? (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {value.map((item: string, idx: number) => <Tag key={`${key}-${idx}`}>{item}</Tag>)}
                </div>
              ) : (
                <Paragraph style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{value?.content || ''}</Paragraph>
              )}
            </Card>
          );
        })}
      </Modal>
    </Card>
  );
}

function StepCharacters({ projectId, onNext }: any) {
  const [characters, setCharacters] = useState<any[]>([]);
  const [factions, setFactions] = useState<any[]>([]);
  const { status, elapsed, startPolling, stopPolling } = useTaskPolling();
  const [draft, setDraft] = useState<any>(null);
  const [draftOpen, setDraftOpen] = useState(false);
  const [drafting, setDrafting] = useState(false);
  const startedRef = useRef(false);

  useEffect(() => {
    if (startedRef.current) return;
    Promise.all([characterApi.list(projectId), factionApi.list(projectId)]).then(([chs, fcs]) => {
      if (chs.length > 0 || fcs.length > 0) { setCharacters(chs); setFactions(fcs); return; }
      startedRef.current = true;
      api.post(`/projects/${projectId}/wizard/generate-characters`, { char_count: 6, faction_count: 3 }).then((res) => {
        startPolling(res.data.task_id, projectId);
      });
    });
  }, [projectId]);

  useEffect(() => {
    if (status !== 'completed') return;
    Promise.all([characterApi.list(projectId), factionApi.list(projectId)]).then(([chs, fcs]) => { setCharacters(chs); setFactions(fcs); });
  }, [status, projectId]);

  if (status === 'running') {
    return <GeneratingCard title="AI 正在生成角色和势力" description="正在构思角色阵容和势力关系…" elapsed={elapsed} />;
  }

  if (characters.length === 0 && status !== 'completed') {
    return <GeneratingCard title="正在加载角色数据…" elapsed={0} />;
  }

  const previewDraft = async () => {
    setDrafting(true);
    try {
      const res = await api.post(`/projects/${projectId}/wizard/generate-characters-draft`, { char_count: 6, faction_count: 3 });
      const data = await pollUntilDone(projectId, res.data.task_id);
      setDraft(data);
      setDraftOpen(true);
    } catch { message.error('生成草稿失败'); }
    setDrafting(false);
  };

  const applyDraft = async () => {
    try {
      await api.post(`/projects/${projectId}/wizard/apply-draft`, { draft_type: 'characters', payload: draft });
      const [chs, fcs] = await Promise.all([characterApi.list(projectId), factionApi.list(projectId)]);
      setCharacters(chs);
      setFactions(fcs);
      setDraftOpen(false);
      message.success('已追加采纳角色势力草稿');
    } catch { message.error('采纳失败'); }
  };

  return (
    <div>
      <Alert type="info" showIcon message="角色和势力支持先生成候选草稿，确认后再追加入库。" style={{ marginBottom: 16 }} />
      <Card style={{ borderRadius: 'var(--radius-lg)', marginBottom: 16 }} title="👤 AI 生成的角色阵容">
        <Row gutter={[12, 12]}>
          {characters.map((c) => (
            <Col xs={24} sm={12} key={c.id}>
              <Card size="small" style={{ borderRadius: 'var(--radius-md)' }}>
                <strong>{c.name}</strong><Tag style={{ marginLeft: 8 }}>{LEGACY_ROLE_LABELS[c.role_type] || c.role_type}</Tag>
                <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 8 }}>{c.personality || c.background?.slice(0, 60) || '—'}</div>
              </Card>
            </Col>
          ))}
        </Row>
      </Card>
      <Card style={{ borderRadius: 'var(--radius-lg)', marginBottom: 16 }} title="🏛 AI 生成的势力">
        <Row gutter={[12, 12]}>
          {factions.map((f) => (
            <Col xs={24} sm={12} key={f.id}>
              <Card size="small" style={{ borderRadius: 'var(--radius-md)' }}>
                <strong>{f.name}</strong><Tag style={{ marginLeft: 8 }}>{LEGACY_FACTION_LABELS[f.faction_type] || f.faction_type}</Tag>
                <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 8 }}>{f.core_creed || f.description?.slice(0, 60) || '—'}</div>
              </Card>
            </Col>
          ))}
        </Row>
      </Card>
      <div style={{ display: 'flex', gap: 12 }}>
        <Button type="primary" size="large" onClick={onNext} icon={<CheckOutlined />}>确认，生成大纲</Button>
        <Button size="large" onClick={() => { setCharacters([]); setFactions([]); startedRef.current = true; api.post(`/projects/${projectId}/wizard/generate-characters`, { char_count: 6, faction_count: 3 }).then((res) => startPolling(res.data.task_id, projectId)); }} icon={<ThunderboltOutlined />}>重新生成</Button>
        <Button size="large" loading={drafting} onClick={previewDraft}>生成草稿预览</Button>
      </div>
      <Modal title="角色势力草稿预览" open={draftOpen} onCancel={() => setDraftOpen(false)} onOk={applyDraft} okText="采纳并追加" width={860}>
        <Title level={5}>角色</Title>
        <Row gutter={[8, 8]}>
          {(draft?.characters || []).map((c: any, i: number) => (
            <Col xs={24} md={12} key={i}>
              <Card size="small" title={c.name}>{c.personality || c.background}</Card>
            </Col>
          ))}
        </Row>
        <Title level={5} style={{ marginTop: 16 }}>势力</Title>
        <Row gutter={[8, 8]}>
          {(draft?.factions || []).map((f: any, i: number) => (
            <Col xs={24} md={12} key={i}>
              <Card size="small" title={f.name}>{f.core_creed || f.description}</Card>
            </Col>
          ))}
        </Row>
      </Modal>
    </div>
  );
}

function StepOutline({ projectId, project, onComplete }: any) {
  const [volumes, setVolumes] = useState<any[]>([]);
  const [chapterCount, setChapterCount] = useState(0);
  const [storyOverview, setStoryOverview] = useState('');
  const { status, elapsed, startPolling } = useTaskPolling();
  const startedRef = useRef(false);

  useEffect(() => {
    if (startedRef.current) return;
    volumeApi.list(projectId).then((vols) => {
      if (vols.length > 0) {
        setVolumes(vols);
        setChapterCount(vols.reduce((s: number, v: any) => s + (v.chapter_count || 0), 0));
        projectApi.get(projectId).then((p) => {
          const brief = p.story_brief || '';
          const idx = brief.indexOf('【全书大纲】');
          if (idx >= 0) setStoryOverview(brief.slice(idx));
        });
        return;
      }
      startedRef.current = true;
      api.post(`/projects/${projectId}/wizard/generate-outline`).then((res) => {
        startPolling(res.data.task_id, projectId);
      });
    });
  }, [projectId]);

  useEffect(() => {
    if (status !== 'completed') return;
    volumeApi.list(projectId).then((vols) => {
      setVolumes(vols);
      setChapterCount(vols.reduce((s: number, v: any) => s + (v.chapter_count || 0), 0));
    });
    projectApi.get(projectId).then((p) => {
      const brief = p.story_brief || '';
      const idx = brief.indexOf('【全书大纲】');
      if (idx >= 0) setStoryOverview(brief.slice(idx));
    });
  }, [status, projectId]);

  if (status === 'running') {
    return <GeneratingCard title="AI 正在规划全书结构" description="AI 正在自主决定卷数，生成全书大纲和每卷大纲…" elapsed={elapsed} />;
  }

  if (volumes.length === 0) {
    return <GeneratingCard title="正在准备生成大纲…" elapsed={0} />;
  }

  return (
    <Card style={{ borderRadius: 'var(--radius-lg)' }}
      title={`📋 全书结构：${volumes.length} 卷，${chapterCount} 章（AI 自主规划）`}>
      {storyOverview && (
        <Card size="small" style={{ borderRadius: 'var(--radius-md)', marginBottom: 16, background: 'var(--bg)' }}>
          <Paragraph style={{ fontSize: 14, whiteSpace: 'pre-wrap', margin: 0 }}>{storyOverview}</Paragraph>
        </Card>
      )}
      {volumes.map((v) => (
        <Card key={v.id} size="small" style={{ marginBottom: 12, borderRadius: 'var(--radius-md)' }}
          title={`📚 卷${v.volume_number} · ${v.title} — ${v.chapter_count}章 · ${(v.target_words / 10000).toFixed(1)}万字`}>
          <Descriptions size="small" column={2}>
            <Descriptions.Item label="主题">{v.theme || '—'}</Descriptions.Item>
            <Descriptions.Item label="情绪弧线">{v.emotional_arc_description || '—'}</Descriptions.Item>
          </Descriptions>
          {v.outline && (
            <div style={{ marginTop: 12 }}>
              <Paragraph strong style={{ fontSize: 13, marginBottom: 4 }}>📝 本卷大纲：</Paragraph>
              <Paragraph style={{ fontSize: 13, whiteSpace: 'pre-wrap', color: 'var(--text-secondary)', background: 'var(--bg)', padding: 12, borderRadius: 8 }}>
                {v.outline}
              </Paragraph>
            </div>
          )}
          <Paragraph type="secondary" style={{ fontSize: 12, marginTop: 8 }}>
            第{v.chapter_range_start}章 ~ 第{v.chapter_range_end}章 · 每章{v.default_chapter_words}字
          </Paragraph>
        </Card>
      ))}
      <div style={{ display: 'flex', gap: 12, marginTop: 24 }}>
        <Button type="primary" size="large" onClick={onComplete} icon={<CheckOutlined />}>确认大纲，开始写作！</Button>
        <Button size="large" onClick={() => { setVolumes([]); setStoryOverview(''); startedRef.current = true; api.post(`/projects/${projectId}/wizard/generate-outline`).then((res) => startPolling(res.data.task_id, projectId)); }} icon={<ThunderboltOutlined />}>重新生成</Button>
      </div>
    </Card>
  );
}
