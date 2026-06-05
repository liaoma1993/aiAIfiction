import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Typography, Spin, Card, Statistic, Row, Col, Tag, Popconfirm, message, Space, Modal, Input } from 'antd';
import { PlusOutlined, ArrowRightOutlined, DeleteOutlined, SettingOutlined, BookOutlined, EditOutlined } from '@ant-design/icons';
import { useProjectStore } from '@/stores/useProjectStore';
import { chapterApi, volumeApi } from '@/services/projectApi';

const { Title } = Typography;

export default function DashboardPage() {
  const { projects, loading, fetchProjects, deleteProject, updateProject } = useProjectStore();
  const navigate = useNavigate();
  const [metrics, setMetrics] = useState<Record<string, any>>({});
  const [projectInfoOpen, setProjectInfoOpen] = useState(false);
  const [projectInfoSaving, setProjectInfoSaving] = useState(false);
  const [editingProject, setEditingProject] = useState<any>(null);
  const [projectInfoDraft, setProjectInfoDraft] = useState({ title: '', story_brief: '' });

  useEffect(() => { fetchProjects(); }, [fetchProjects]);

  useEffect(() => {
    if (!projects.length) return;
    Promise.all(projects.map(async (p: any) => {
      try {
        const [chapters, volumes] = await Promise.all([chapterApi.list(p.id), volumeApi.list(p.id)]);
        const wordCount = chapters.reduce((sum: number, ch: any) => sum + (ch.word_count || (ch.content || '').length || 0), 0);
        const written = chapters.filter((ch: any) => ch.content).length;
        const audited = chapters.filter((ch: any) => ch.quality_score).length;
        return [p.id, { chapters, volumes, wordCount, written, audited, total: chapters.length }];
      } catch {
        return [p.id, { chapters: [], volumes: [], wordCount: 0, written: 0, audited: 0, total: 0 }];
      }
    })).then((entries) => setMetrics(Object.fromEntries(entries)));
  }, [projects]);

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    try { await deleteProject(id); message.success('已删除'); fetchProjects(); } catch { message.error('删除失败'); }
  };

  const openProjectInfo = (e: React.MouseEvent, project: any) => {
    e.stopPropagation();
    setEditingProject(project);
    setProjectInfoDraft({
      title: project.title || '',
      story_brief: project.story_brief || '',
    });
    setProjectInfoOpen(true);
  };

  const saveProjectInfo = async () => {
    if (!editingProject?.id) return;
    setProjectInfoSaving(true);
    try {
      await updateProject(editingProject.id, {
        title: projectInfoDraft.title.trim() || '未命名项目',
        story_brief: projectInfoDraft.story_brief,
      });
      await fetchProjects();
      setProjectInfoOpen(false);
      message.success('项目信息已保存');
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e.message || '保存失败');
    }
    setProjectInfoSaving(false);
  };

  const statusLabel: Record<string, { color: string; text: string }> = {
    planning: { color: 'blue', text: '规划中' },
    writing: { color: 'orange', text: '写作中' },
    polishing: { color: 'purple', text: '打磨中' },
    completed: { color: 'green', text: '已完成' },
  };

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto', padding: '32px 24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 32 }}>
        <Title level={2} style={{ margin: 0 }}>我的项目</Title>
        <div style={{ display: 'flex', gap: 12 }}>
          <Button icon={<SettingOutlined />} onClick={() => navigate('/settings/providers')}>模型管理</Button>
          <Button type="primary" size="large" icon={<PlusOutlined />} onClick={() => navigate('/projects/create')}>
            创建新项目
          </Button>
        </div>
      </div>

      <Row gutter={[16, 16]} style={{ marginBottom: 32 }}>
        {[
          { title: '进行中', value: projects.filter((p) => p.status === 'writing').length },
          { title: '已完成', value: projects.filter((p) => p.status === 'completed').length },
          { title: '总字数', value: Object.values(metrics).reduce((s: number, m: any) => s + (m.wordCount || 0), 0) },
          { title: '平均完成度', value: projects.length ? `${Math.round(Object.values(metrics).reduce((s: number, m: any) => s + ((m.wordCount || 0) / Math.max(1, projects.find((p: any) => p.id === Object.keys(metrics).find(id => metrics[id] === m))?.target_total_words || 1)), 0) / projects.length * 100)}%` : '--' },
        ].map((s) => (
          <Col xs={12} sm={6} key={s.title}>
            <Card><Statistic title={s.title} value={s.value} /></Card>
          </Col>
        ))}
      </Row>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 48 }}><Spin size="large" /></div>
      ) : projects.length === 0 ? (
        <Card style={{ textAlign: 'center', padding: 48 }}>
          <Title level={4} type="secondary">还没有项目</Title>
          <Button type="primary" size="large" onClick={() => navigate('/projects/create')}>创建第一个项目</Button>
        </Card>
      ) : (
        projects.map((p) => {
          const s = statusLabel[p.status] || { color: 'default', text: p.status };
          const m = metrics[p.id] || {};
          const progress = Math.min(100, Math.round(((m.wordCount || 0) / Math.max(1, p.target_total_words || 1)) * 100));
          const nextAction = p.status === 'planning' ? '继续向导'
            : !m.total ? '展开章节'
            : m.written < m.total ? `继续第${(m.chapters || []).find((ch: any) => !ch.content)?.chapter_number || 1}章`
            : m.audited < m.total ? '审计章节'
            : '查看作品';
          return (
            <Card
              key={p.id}
              hoverable
              style={{ marginBottom: 12, borderRadius: 'var(--radius-lg)' }}
              onClick={() => navigate(`/projects/${p.id}${(p.status === 'planning' && (p.wizard_step || 0) < 4) ? '/wizard' : ''}`)}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <Title level={4} style={{ margin: 0 }}>{p.title || '未命名项目'}</Title>
	                  <div style={{ marginTop: 6, fontSize: 13, color: '#8c8c8c', lineHeight: 1.6, maxWidth: 500 }}>
	                    {p.story_brief ? (
	                      p.story_brief.length > 150
	                        ? <span>{p.story_brief.slice(0, 150)}…</span>
	                        : <span>{p.story_brief}</span>
	                    ) : <span style={{ fontStyle: 'italic' }}>暂无简介</span>}
	                    <Button
	                      type="link"
	                      size="small"
	                      icon={<EditOutlined />}
	                      onClick={(e) => openProjectInfo(e, p)}
	                      style={{ paddingInline: 6 }}
	                    >
	                      查看全部/编辑
	                    </Button>
	                  </div>
                  <div style={{ marginTop: 8 }}>
                    <Tag>{p.genre}</Tag>
                    <Tag>{p.target_total_words ? `${Math.round(p.target_total_words / 10000)}万字` : '--'}</Tag>
                    <Tag color={s.color}>{s.text}</Tag>
                    <Tag>{m.volumes?.length || 0}卷 · {m.total || 0}章 · 已写{m.written || 0}章</Tag>
                  </div>
                  <div style={{ marginTop: 10, width: 420, maxWidth: '60vw' }}>
                    <div style={{ height: 6, borderRadius: 999, background: '#f0f0f0', overflow: 'hidden' }}>
                      <div style={{ width: `${progress}%`, height: '100%', background: progress >= 100 ? '#52c41a' : '#1677ff' }} />
                    </div>
                    <div style={{ marginTop: 4, fontSize: 12, color: 'var(--text-secondary)' }}>
                      {m.wordCount || 0} / {p.target_total_words || 0} 字 · {progress}% · 下一步：{nextAction}
                    </div>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                  <Space>
	                    <Button icon={<EditOutlined />} onClick={(e) => openProjectInfo(e, p)}>
	                      项目信息
	                    </Button>
	                    <Button icon={<BookOutlined />} onClick={(e) => { e.stopPropagation(); navigate(`/projects/${p.id}/preview`); }}>
	                      预览小说
	                    </Button>
                    <Button type="primary" icon={<ArrowRightOutlined />}>
                      {nextAction}
                    </Button>
                  </Space>
                  <Popconfirm title="确定删除这个项目？所有数据将被永久删除。" onConfirm={(e) => handleDelete(e as any, p.id)}
                    onPopupClick={(e) => e.stopPropagation()}>
                    <Button danger icon={<DeleteOutlined />} onClick={(e) => e.stopPropagation()} />
                  </Popconfirm>
                </div>
              </div>
            </Card>
          );
        })
      )}
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
	          <Typography.Text strong>书名</Typography.Text>
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
	          <Typography.Text strong>简介</Typography.Text>
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
