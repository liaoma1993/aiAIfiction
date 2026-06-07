import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Alert, Button, Empty, Input, Popconfirm, Select, Space, Spin, Tag, Typography, Upload, message } from 'antd';
import {
  CheckCircleOutlined,
  DeleteOutlined,
  ExperimentOutlined,
  InboxOutlined,
  LeftOutlined,
  ReadOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { projectApi, writingStyleSkillApi } from '@/services/projectApi';
import './WritingStyleSkillsPage.css';

const { Text, Title, Paragraph } = Typography;
const { TextArea } = Input;
const { Dragger } = Upload;

const GROUPS = [
  { title: '核心风格', keys: ['core_style', 'sample_diagnosis', 'technique_taxonomy'] },
  { title: '前20万字留存', keys: ['early_retention_model', 'length_adaptation'] },
  { title: '人物与关系', keys: ['characterization_style', 'character_voice_style', 'relationship_style'] },
  { title: '角色声音矩阵', keys: ['character_voice_matrix'] },
  { title: '情绪与感情', keys: ['emotion_style', 'dialogue_style'] },
  { title: '场景与细节', keys: ['scene_construction_style', 'scene_description_style', 'detail_style'] },
  { title: '场景施工模板', keys: ['scene_templates'] },
  { title: '世界观与信息', keys: ['worldbuilding_style', 'information_control_style'] },
  { title: '冲突与反馈', keys: ['conflict_style', 'reader_payoff_style'] },
  { title: '语言与节奏', keys: ['language_style', 'chapter_structure_style', 'pov_style', 'pacing_style', 'theme_style'] },
  { title: '文笔工艺', keys: ['prose_craft_style', 'paragraph_flow_style'] },
  { title: '细节与真实感', keys: ['detail_craft_style', 'scene_reality_style'] },
  { title: '人物与情绪工艺', keys: ['character_entrance_style', 'emotion_landing_style'] },
  { title: '章节生产法', keys: ['chapter_production_recipe', 'reusable_patterns'] },
  { title: '证据与迁移', keys: ['evidence_bank'] },
  { title: '流程使用', keys: ['workflow_usage', 'creation_guidance', 'outline_guidance', 'writing_guidance'] },
  { title: '偏离检测与修复', keys: ['deviation_checks', 'repair_strategies', 'avoid_rules'] },
];

const FIELD_LABELS: Record<string, string> = {
  core_style: '核心质感',
  sample_diagnosis: '样本覆盖诊断',
  technique_taxonomy: '技法谱系',
  early_retention_model: '前20万字模型',
  length_adaptation: '篇幅适配',
  pov_style: '视角控制',
  pacing_style: '节奏推进',
  theme_style: '主题表达',
  characterization_style: '人物刻画',
  character_voice_style: '角色声音',
  character_voice_matrix: '角色声音矩阵',
  relationship_style: '关系推进',
  emotion_style: '情绪感情',
  dialogue_style: '对白',
  scene_construction_style: '场景组织',
  scene_description_style: '场景描写',
  scene_templates: '场景施工模板',
  detail_style: '细节选择',
  worldbuilding_style: '世界观揭示',
  information_control_style: '信息控制',
  conflict_style: '冲突设计',
  reader_payoff_style: '读者反馈',
  language_style: '语言手感',
  chapter_structure_style: '章节结构',
  prose_craft_style: '文笔工艺',
  paragraph_flow_style: '段落推进',
  detail_craft_style: '细节工艺',
  scene_reality_style: '场景真实感',
  character_entrance_style: '人物出场',
  emotion_landing_style: '情绪落点',
  chapter_production_recipe: '章节生产法',
  reusable_patterns: '可复用模式',
  evidence_bank: '技法证据库',
  workflow_usage: '全流程使用',
  deviation_checks: '风格偏离检测',
  repair_strategies: '反向修复策略',
  avoid_rules: '禁用规则',
  creation_guidance: '创建小说',
  outline_guidance: '大纲规划',
  writing_guidance: '章节写作',
};

function summarizeField(value: any) {
  if (!value) return '';
  if (typeof value === 'string') return value;
  if (Array.isArray(value)) {
    return value.slice(0, 8).map((item) => {
      if (typeof item === 'string') return item;
      if (item && typeof item === 'object') {
        const steps = Array.isArray(item.steps) ? item.steps.slice(0, 3).join(' -> ') : '';
        return [
          item.name,
          item.when_to_use,
          item.best_for,
          item.technique,
          item.evidence_summary,
          item.transfer_rule,
          item.opening_anchor,
          item.friction,
          item.turn,
          item.exit_hook,
          steps,
          item.avoid,
        ].filter(Boolean).join('：');
      }
      return String(item);
    }).join('；');
  }
  if (typeof value === 'object') {
    const parts = [
      value.summary,
      value.opening,
      value.middle,
      value.ending,
      Array.isArray(value.covered_sections) ? `覆盖：${value.covered_sections.slice(0, 5).join('、')}` : '',
      Array.isArray(value.high_confidence_findings) ? value.high_confidence_findings.slice(0, 4).join('；') : '',
      Array.isArray(value.needs_more_samples) ? `待补样本：${value.needs_more_samples.slice(0, 3).join('；')}` : '',
      Array.isArray(value.techniques) ? value.techniques.slice(0, 3).join('；') : '',
      Array.isArray(value.rules) ? value.rules.slice(0, 3).join('；') : '',
      Array.isArray(value.character) ? `人物：${value.character.slice(0, 2).join('；')}` : '',
      Array.isArray(value.emotion) ? `情绪：${value.emotion.slice(0, 2).join('；')}` : '',
      Array.isArray(value.world) ? `世界：${value.world.slice(0, 2).join('；')}` : '',
      Array.isArray(value.scene) ? `场景：${value.scene.slice(0, 2).join('；')}` : '',
      Array.isArray(value.conflict) ? `冲突：${value.conflict.slice(0, 2).join('；')}` : '',
      Array.isArray(value.relationship) ? `关系：${value.relationship.slice(0, 2).join('；')}` : '',
      Array.isArray(value.detail) ? `细节：${value.detail.slice(0, 2).join('；')}` : '',
      Array.isArray(value.information_gap) ? `信息差：${value.information_gap.slice(0, 2).join('；')}` : '',
      Array.isArray(value.payoff) ? `反馈：${value.payoff.slice(0, 2).join('；')}` : '',
      Array.isArray(value.must_do) ? `必须执行：${value.must_do.slice(0, 4).join('；')}` : '',
      Array.isArray(value.must_not_do) ? `必须避免：${value.must_not_do.slice(0, 4).join('；')}` : '',
      Array.isArray(value.chapter_1) ? `第1章：${value.chapter_1.slice(0, 3).join('；')}` : '',
      Array.isArray(value.first_3_chapters) ? `前3章：${value.first_3_chapters.slice(0, 3).join('；')}` : '',
      Array.isArray(value.first_10_chapters) ? `前10章：${value.first_10_chapters.slice(0, 3).join('；')}` : '',
      Array.isArray(value.first_30_chapters) ? `前30章：${value.first_30_chapters.slice(0, 3).join('；')}` : '',
      Array.isArray(value.first_50_chapters) ? `前50章：${value.first_50_chapters.slice(0, 3).join('；')}` : '',
      value.short ? `短篇：${value.short}` : '',
      value.medium ? `中篇：${value.medium}` : '',
      value.long ? `长篇：${value.long}` : '',
      value.mega ? `超长篇：${value.mega}` : '',
      Array.isArray(value.fatigue_control) ? `疲劳控制：${value.fatigue_control.slice(0, 3).join('；')}` : '',
      Array.isArray(value.protagonist_inner_voice) ? `主角内心：${value.protagonist_inner_voice.slice(0, 3).join('；')}` : '',
      Array.isArray(value.protagonist_spoken_voice) ? `主角对外：${value.protagonist_spoken_voice.slice(0, 3).join('；')}` : '',
      Array.isArray(value.voice_separation_rules) ? `声音区分：${value.voice_separation_rules.slice(0, 3).join('；')}` : '',
      Array.isArray(value.sentence_patterns) ? value.sentence_patterns.slice(0, 3).join('；') : '',
      Array.isArray(value.paragraph_patterns) ? value.paragraph_patterns.slice(0, 3).join('；') : '',
      Array.isArray(value.transition_methods) ? value.transition_methods.slice(0, 3).join('；') : '',
      Array.isArray(value.detail_sources) ? value.detail_sources.slice(0, 3).join('；') : '',
      Array.isArray(value.entrance_methods) ? value.entrance_methods.slice(0, 3).join('；') : '',
      Array.isArray(value.physical_reactions) ? value.physical_reactions.slice(0, 3).join('；') : '',
      Array.isArray(value.practical_obstacles) ? value.practical_obstacles.slice(0, 3).join('；') : '',
      Array.isArray(value.setup) ? value.setup.slice(0, 2).join('；') : '',
      Array.isArray(value.conflict) ? value.conflict.slice(0, 2).join('；') : '',
      Array.isArray(value.emotion) ? value.emotion.slice(0, 2).join('；') : '',
      Array.isArray(value.creation) ? `创建：${value.creation.slice(0, 3).join('；')}` : '',
      Array.isArray(value.worldbuilding) ? `世界观：${value.worldbuilding.slice(0, 3).join('；')}` : '',
      Array.isArray(value.characters) ? `角色：${value.characters.slice(0, 3).join('；')}` : '',
      Array.isArray(value.outline) ? `大纲：${value.outline.slice(0, 3).join('；')}` : '',
      Array.isArray(value.writing) ? `正文：${value.writing.slice(0, 3).join('；')}` : '',
      Array.isArray(value.audit) ? `审计：${value.audit.slice(0, 3).join('；')}` : '',
      Array.isArray(value.repair) ? `修复：${value.repair.slice(0, 3).join('；')}` : '',
      Array.isArray(value.style_fit) ? `风格：${value.style_fit.slice(0, 3).join('；')}` : '',
      Array.isArray(value.voice_fit) ? `声音：${value.voice_fit.slice(0, 3).join('；')}` : '',
      Array.isArray(value.ai_flavor_risks) ? `AI味风险：${value.ai_flavor_risks.slice(0, 3).join('；')}` : '',
      Array.isArray(value.sentence) ? `原句：${value.sentence.slice(0, 3).join('；')}` : '',
      Array.isArray(value.paragraph) ? `段落：${value.paragraph.slice(0, 3).join('；')}` : '',
      Array.isArray(value.chapter_light) ? `轻修：${value.chapter_light.slice(0, 3).join('；')}` : '',
      Array.isArray(value.chapter_rewrite) ? `重写：${value.chapter_rewrite.slice(0, 3).join('；')}` : '',
    ].filter(Boolean);
    return parts.join('；') || JSON.stringify(value);
  }
  return String(value);
}

function clip(text: string, limit = 180) {
  const clean = String(text || '').trim();
  return clean.length > limit ? `${clean.slice(0, limit)}...` : clean;
}

export default function WritingStyleSkillsPage() {
  const [projects, setProjects] = useState<any[]>([]);
  const [skills, setSkills] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [name, setName] = useState('');
  const [sourceNote, setSourceNote] = useState('');
  const [sampleText, setSampleText] = useState('');
  const [sampleFile, setSampleFile] = useState<File | null>(null);
  const [sampleFileInfo, setSampleFileInfo] = useState<{ name: string; size: number } | null>(null);
  const [selectedSkill, setSelectedSkill] = useState<any>(null);
  const [extractTasks, setExtractTasks] = useState<any[]>([]);

  const load = async () => {
    setLoading(true);
    const [projectList, list] = await Promise.all([
      projectApi.list(),
      writingStyleSkillApi.list(),
    ]);
    setProjects(projectList || []);
    setSkills(list || []);
    setSelectedSkill((prev: any) => {
      if (prev) return (list || []).find((item: any) => item.id === prev.id) || null;
      return (list || [])[0] || null;
    });
    writingStyleSkillApi.tasks().then((items) => setExtractTasks(items || [])).catch(() => {});
    setLoading(false);
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    const running = extractTasks.some((task) => ['running', 'cancelling'].includes(task.status));
    if (!running) return;
    const timer = window.setInterval(async () => {
      try {
        const latest = await writingStyleSkillApi.tasks();
        setExtractTasks(latest || []);
        const completedSkill = (latest || [])
          .filter((task: any) => task.status === 'completed')
          .map((task: any) => task.result?.skill)
          .find((skill: any) => skill?.id && !skills.some((item) => item.id === skill.id));
        if (completedSkill) {
          setSkills((prev) => [completedSkill, ...prev.filter((item) => item.id !== completedSkill.id)]);
          setSelectedSkill(completedSkill);
          message.success(`写作风格 Skill 已生成：${completedSkill.name}`);
        }
      } catch {
        // Keep the current task list; the next interval can recover.
      }
    }, 3000);
    return () => window.clearInterval(timer);
  }, [extractTasks, skills]);

  const skillUsage = useMemo(
    () => projects.reduce((acc: Record<string, number>, project: any) => {
      const id = project?.writing_style?.active_style_skill_id;
      if (id) acc[id] = (acc[id] || 0) + 1;
      return acc;
    }, {}),
    [projects],
  );

  const usedProjectCount = useMemo(
    () => projects.filter((project) => project?.writing_style?.active_style_skill_id).length,
    [projects],
  );

  const analyze = async () => {
    if (!sampleFile && !sampleText.trim()) return message.warning('先上传小说样本文件，或少量粘贴补充样本');
    if (!sampleFile && sampleText.trim().length < 1000) return message.warning('样本建议至少 1000 字');
    setAnalyzing(true);
    try {
      if (sampleFile) {
        const form = new FormData();
        form.append('file', sampleFile);
        form.append('name', name.trim());
        form.append('source_note', sourceNote.trim() || sampleFile.name);
        form.append('supplement_text', sampleText.trim());
        form.append('save', 'true');
        const task = await writingStyleSkillApi.analyzeUpload(form);
        setExtractTasks((prev) => [{
          id: task.task_id,
          status: task.status || 'running',
          task_type: 'writing_style_skill_extract',
          progress: 0,
          progress_label: '任务已提交，正在后台抽取写作风格',
          meta: { filename: sampleFile.name, source_note: sourceNote.trim() || sampleFile.name },
          created_at: new Date().toISOString(),
        }, ...prev]);
        setSampleFile(null);
        setSampleFileInfo(null);
        setSampleText('');
        setName('');
        setSourceNote('');
        message.success('写作风格抽取任务已提交，可在任务列表查看进度');
      } else {
        const skill = await writingStyleSkillApi.analyze({
          name: name.trim(),
          source_note: sourceNote.trim(),
          sample_text: sampleText,
          save: true,
        });
        setSkills([skill, ...skills]);
        setSelectedSkill(skill);
        setName('');
        setSourceNote('');
        setSampleText('');
        message.success('写作风格 Skill 已生成');
      }
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '抽取失败');
    } finally {
      setAnalyzing(false);
    }
  };

  const readSampleFile = async (file: File) => {
    const maxSize = 60 * 1024 * 1024;
    if (file.size > maxSize) {
      message.warning('单个样本文件不能超过 60MB，可以分批抽取多个 Skill');
      return false;
    }
    const lowerName = file.name.toLowerCase();
    const allowed = ['.txt', '.md', '.markdown', '.text', '.log'].some((ext) => lowerName.endsWith(ext));
    if (!allowed) {
      message.warning('当前先支持纯文本文件：txt、md、markdown、text');
      return false;
    }
    setSampleFile(file);
    setSampleFileInfo({ name: file.name, size: file.size });
    setSourceNote((prev) => prev || file.name);
    setName((prev) => prev || file.name.replace(/\.[^.]+$/, '').slice(0, 40));
    message.success(`已选择 ${file.name}，点击“抽取并保存 Skill”后上传分析`);
    return false;
  };

  const setProjectSkill = async (projectId: string, skillId: string | null) => {
    const updated = await writingStyleSkillApi.setActive(projectId, skillId);
    setProjects((prev) => prev.map((project) => project.id === projectId ? updated : project));
    message.success(skillId ? '项目写作风格已更新' : '已取消项目写作风格');
  };

  const remove = async (skill: any) => {
    await writingStyleSkillApi.remove(skill.id);
    const next = skills.filter((item) => item.id !== skill.id);
    setSkills(next);
    if (selectedSkill?.id === skill.id) setSelectedSkill(next[0] || null);
    const affected = projects.filter((project) => project?.writing_style?.active_style_skill_id === skill.id);
    await Promise.all(affected.map((project) => writingStyleSkillApi.setActive(project.id, null)));
    if (affected.length) {
      setProjects((prev) => prev.map((project) => (
        project?.writing_style?.active_style_skill_id === skill.id
          ? { ...project, writing_style: { ...(project.writing_style || {}), active_style_skill_id: '' } }
          : project
      )));
    }
    message.success('Skill 已移除');
  };

  if (loading) return <div className="style-skills-loading"><Spin /></div>;

  const detail = selectedSkill?.style_profile || {};

  return (
    <div className="style-skills-page">
      <header className="style-skills-header">
        <Link to="/dashboard"><Button icon={<LeftOutlined />} size="small">返回 Dashboard</Button></Link>
        <div className="style-skills-titleblock">
          <Title level={3}>写作风格 Skill</Title>
          <Text type="secondary">全局共享的写作方法库。项目只选择引用，Skill 不属于某一本书。</Text>
        </div>
      </header>

      <Alert
        className="style-skills-alert"
        type="info"
        showIcon
        message="这里抽取的是人物、情绪、世界、场景、冲突、关系、细节、语言和章节结构等写作手法，不复制原文、情节、人名和专有设定。"
      />

      <section className="style-skills-status">
        <div>
          <Text type="secondary">共享 Skill</Text>
          <strong>{skills.length}</strong>
        </div>
        <div>
          <Text type="secondary">已引用项目</Text>
          <strong>{usedProjectCount}</strong>
        </div>
        <div>
          <Text type="secondary">项目总数</Text>
          <strong>{projects.length}</strong>
        </div>
      </section>

      <main className="style-skills-layout">
        <section className="style-skills-builder">
          <div className="section-title">
            <ExperimentOutlined />
            <span>上传样本抽取写作方法</span>
          </div>
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Skill 名称，如：细腻感情流 / 爽文快节奏 / 群像权谋" />
          <Input value={sourceNote} onChange={(e) => setSourceNote(e.target.value)} placeholder="来源备注，可写作者、书名或你自己的说明，不会参与仿写" />
          <Dragger
            className="style-sample-upload"
            accept=".txt,.md,.markdown,.text,.log"
            multiple={false}
            showUploadList={false}
            beforeUpload={(file) => readSampleFile(file as File)}
          >
            <p className="ant-upload-drag-icon"><InboxOutlined /></p>
            <p className="ant-upload-text">上传小说样本文件</p>
            <p className="ant-upload-hint">支持 txt / md / markdown / text。文件不会显示在页面里，后端会自动取开篇、中段、后段代表样本分析。</p>
          </Dragger>
          {sampleFileInfo && (
            <div className="style-sample-file">
              <div>
                <Text strong>{sampleFileInfo.name}</Text>
                <Text type="secondary">{(sampleFileInfo.size / 1024 / 1024).toFixed(2)} MB · 已选择，未渲染全文</Text>
              </div>
              <Button size="small" onClick={() => { setSampleFile(null); setSampleFileInfo(null); }}>移除文件</Button>
            </div>
          )}
          <TextArea
            value={sampleText}
            onChange={(e) => setSampleText(e.target.value)}
            placeholder="这里只放少量补充样本或说明，不展示上传文件全文。比如补充：重点分析感情戏、人物对白、世界观揭示方式。"
            autoSize={{ minRows: 4, maxRows: 8 }}
          />
          <div className="style-skills-builder-foot">
            <Text type="secondary">{sampleFileInfo ? `文件 ${(sampleFileInfo.size / 1024 / 1024).toFixed(2)} MB` : `${sampleText.trim().length} 字`}</Text>
            <Button type="primary" icon={<ThunderboltOutlined />} loading={analyzing} onClick={analyze}>{sampleFile ? '提交抽取任务' : '抽取并保存 Skill'}</Button>
          </div>
          <div className="style-skills-flow">
            <Tag>创建小说</Tag>
            <Tag>全书大纲</Tag>
            <Tag>卷弧线</Tag>
            <Tag>章节蓝图</Tag>
            <Tag>正文写作</Tag>
          </div>
        </section>

        <section className="style-skills-library">
          <div className="section-title">
            <ReadOutlined />
            <span>共享 Skill 库</span>
          </div>
          {!skills.length ? <Empty description="还没有写作风格 Skill" /> : (
            <div className="style-skill-list">
              {skills.map((skill) => (
                <button
                  key={skill.id}
                  className={`style-skill-item ${selectedSkill?.id === skill.id ? 'selected' : ''}`}
                  onClick={() => setSelectedSkill(skill)}
                >
                  <span className="style-skill-item-main">
                    <Text strong>{skill.name}</Text>
                    <Text type="secondary">{clip(skill.description || skill.style_profile?.core_style || '未填写简介', 90)}</Text>
                  </span>
                  {skillUsage[skill.id] ? <Tag color="green" icon={<CheckCircleOutlined />}>{skillUsage[skill.id]} 个项目</Tag> : <Tag>未引用</Tag>}
                </button>
              ))}
            </div>
          )}
        </section>
      </main>

      <section className="style-skill-tasks">
        <div className="style-skill-detail-head">
          <div>
            <Title level={4}>抽取任务</Title>
            <Paragraph type="secondary">大文件会在后台分析，不需要等待请求返回。任务完成后会自动加入共享 Skill 库。</Paragraph>
          </div>
          <Button onClick={() => writingStyleSkillApi.tasks().then((items) => setExtractTasks(items || []))}>刷新任务</Button>
        </div>
        {!extractTasks.length ? <Empty description="暂无抽取任务" /> : (
          <div className="style-task-list">
            {extractTasks.slice(0, 8).map((task) => {
              const skill = task.result?.skill;
              const statusText = task.status === 'completed' ? '已完成' : task.status === 'failed' ? '失败' : '进行中';
              return (
                <div className="style-task-row" key={task.id}>
                  <div className="style-task-main">
                    <Text strong>{task.meta?.filename || task.meta?.source_note || skill?.name || '写作风格抽取'}</Text>
                    <Text type="secondary">{task.progress_label || (skill ? `已生成：${skill.name}` : '等待后台处理')}</Text>
                    {task.error && <Text type="danger">{task.error}</Text>}
                  </div>
                  <Tag color={task.status === 'completed' ? 'green' : task.status === 'failed' ? 'red' : 'blue'}>{statusText}</Tag>
                </div>
              );
            })}
          </div>
        )}
      </section>

      <section className="style-skill-projects">
        <div className="style-skill-detail-head">
          <div>
            <Title level={4}>项目引用管理</Title>
            <Paragraph type="secondary">在这里给已有项目选择共享 Skill。创建新项目时也可以在创建页直接选择。</Paragraph>
          </div>
        </div>
        {!projects.length ? <Empty description="暂无项目" /> : (
          <div className="style-project-list">
            {projects.map((project) => (
              <div className="style-project-row" key={project.id}>
                <div className="style-project-main">
                  <Text strong>{project.title || '未命名项目'}</Text>
                  <Text type="secondary">{project.genre || '未分类'} · {project.target_total_words ? `${Math.round(project.target_total_words / 10000)}万字` : '字数待定'}</Text>
                </div>
                <Select
                  allowClear
                  value={project?.writing_style?.active_style_skill_id || undefined}
                  placeholder="选择写作风格 Skill"
                  onChange={(value) => setProjectSkill(project.id, value || null)}
                  options={skills.map((skill) => ({ value: skill.id, label: skill.name }))}
                  style={{ minWidth: 260 }}
                />
              </div>
            ))}
          </div>
        )}
      </section>

      {selectedSkill && (
        <section className="style-skill-detail">
          <div className="style-skill-detail-head">
            <div>
              <Title level={4}>{selectedSkill.name}</Title>
              <Paragraph type="secondary">{selectedSkill.description || '暂无简介'}</Paragraph>
            </div>
            <Space wrap>
              <Tag color={skillUsage[selectedSkill.id] ? 'green' : 'default'}>{skillUsage[selectedSkill.id] || 0} 个项目引用</Tag>
              <Popconfirm title="移除这个 Skill？" okText="移除" cancelText="取消" onConfirm={() => remove(selectedSkill)}>
                <Button danger icon={<DeleteOutlined />}>移除</Button>
              </Popconfirm>
            </Space>
          </div>

          <div className="style-skill-groups">
            {GROUPS.map((group) => (
              <div className="style-skill-group" key={group.title}>
                <h4>{group.title}</h4>
                {group.keys.map((key) => {
                  const text = summarizeField(detail[key]);
                  return text ? (
                    <div className="style-skill-field" key={key}>
                      <Text type="secondary">{FIELD_LABELS[key] || key}</Text>
                      <p>{clip(text, 620)}</p>
                    </div>
                  ) : null;
                })}
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
