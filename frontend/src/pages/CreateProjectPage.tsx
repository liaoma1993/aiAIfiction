import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Input, Button, Typography, Tag, Row, Col, Spin, message, Space, Alert, List, Divider, Select } from 'antd';
import { ArrowLeftOutlined, ThunderboltOutlined, ReloadOutlined, LoadingOutlined, SendOutlined, CheckOutlined } from '@ant-design/icons';
import { useProjectStore } from '@/stores/useProjectStore';
import api from '@/services/api';
import { writingStyleSkillApi } from '@/services/projectApi';

const { Title, Paragraph, Text } = Typography;
const { TextArea } = Input;

const GENRES = [
  '玄幻', '奇幻', '仙侠', '修真', '武侠', '科幻', '星际', '赛博朋克',
  '都市', '现实', '职场', '官场', '商战', '娱乐圈', '校园', '青春',
  '悬疑', '推理', '刑侦', '惊悚', '恐怖', '灵异', '克苏鲁',
  '历史', '架空历史', '军事', '战争', '权谋', '宫斗',
  '言情', '古言', '现言', '纯爱', '轻小说', '二次元',
  '游戏', '电竞', '体育', '末世', '废土', '无限流', '系统流', '穿越', '重生',
];

const TONE_PREFERENCES = [
  '轻松爽文', '热血燃向', '冷峻悬疑', '压抑现实', '温暖治愈', '黑色幽默',
  '史诗厚重', '甜宠轻喜', '克制文艺', '紧张高压', '群像权谋', '日常陪伴',
];
const PLANNING_DRAFT_KEY = 'aifiction:create-project-planning-draft:v1';

type ChatMessage = {
  role: 'user' | 'assistant';
  content: string;
};

const normalizeTotalWords = (value: any) => {
  const num = Number(value);
  return Number.isFinite(num) && num > 0 ? num : null;
};

const formatTotalWords = (value: any) => {
  const num = normalizeTotalWords(value);
  return num ? `${Math.round(num / 10000)}万字` : '字数待定';
};

const appendInputText = (current: string, addition: string) => {
  const base = current.trimEnd();
  const next = addition.trim();
  if (!next) return current;
  return base ? `${base}\n${next}` : next;
};

const structuredText = (value: any): string => {
  if (value === undefined || value === null) return '';
  if (typeof value === 'string') return value.trim();
  if (Array.isArray(value)) return value.map(structuredText).filter(Boolean).join('；');
  if (typeof value === 'object') {
    const labels: Record<string, string> = {
      stage: '阶段',
      title: '标题',
      goal: '目标',
      pressure_upgrade: '压力升级',
      protagonist_change: '主角变化',
      hook: '钩子',
      event: '事件',
      protagonist_action: '行动',
      obstacle: '阻力',
      payoff: '反馈',
      carry_forward: '后续',
      name: '名称',
      description: '说明',
      plant_stage: '埋设',
      reveal_stage: '回收',
      payoff_type: '兑现',
    };
    return Object.entries(value)
      .map(([key, item]) => {
        const text = structuredText(item);
        return text ? `${labels[key] || key}：${text}` : '';
      })
      .filter(Boolean)
      .join('；');
  }
  return String(value).trim();
};

const asTextList = (value: any): string[] => {
  if (Array.isArray(value)) {
    return value.map(structuredText).filter(Boolean);
  }
  return typeof value === 'string' && value.trim() ? [value.trim()] : [];
};

const DraftSection = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <>
    <Divider style={{ margin: '12px 0' }} />
    <Text strong>{title}</Text>
    <div style={{ marginTop: 8 }}>{children}</div>
  </>
);

const renderMetaLine = (label: string, value: any) => {
  if (value === undefined || value === null || value === '') return null;
  const text = Array.isArray(value) ? value.join('；') : String(value);
  return (
    <Paragraph key={label} style={{ marginBottom: 6, lineHeight: 1.7 }}>
      <Text type="secondary">{label}：</Text>{text}
    </Paragraph>
  );
};

const renderEventChainItem = (item: any, i: number) => {
  if (!item || typeof item !== 'object') return <List.Item style={{ padding: '4px 0' }}>{String(item)}</List.Item>;
  const parts = [
    item.event && `事件：${item.event}`,
    item.protagonist_action && `行动：${item.protagonist_action}`,
    item.obstacle && `阻力：${item.obstacle}`,
    item.payoff && `反馈：${item.payoff}`,
    item.carry_forward && `后续：${item.carry_forward}`,
  ].filter(Boolean);
  return (
    <List.Item style={{ padding: '6px 0', alignItems: 'flex-start' }}>
      <Text type="secondary" style={{ marginRight: 6 }}>{i + 1}.</Text>
      <span>{parts.join('；')}</span>
    </List.Item>
  );
};

const renderStagePlanItem = (item: any, i: number) => {
  if (!item || typeof item !== 'object') {
    return (
      <List.Item style={{ padding: '8px 0' }}>
        <Text type="secondary" style={{ marginRight: 6 }}>{i + 1}.</Text>{String(item)}
      </List.Item>
    );
  }
  const stageTitle = item.stage || item.title || `阶段 ${i + 1}`;
  const rows = [
    ['目标', item.goal],
    ['压力升级', item.pressure_upgrade],
    ['主角变化', item.protagonist_change],
    ['阶段钩子', item.hook],
  ].filter(([, value]) => value);
  return (
    <List.Item style={{ padding: '8px 0' }}>
      <div style={{ width: '100%', borderLeft: '3px solid #1677ff', padding: '6px 0 6px 12px', background: 'rgba(22, 119, 255, 0.04)' }}>
        <Text strong>{i + 1}. {stageTitle}</Text>
        <div style={{ marginTop: 6 }}>
          {rows.map(([label, value]) => (
            <Paragraph key={label} style={{ marginBottom: 4, lineHeight: 1.7 }}>
              <Text type="secondary">{label}：</Text>{structuredText(value)}
            </Paragraph>
          ))}
        </div>
      </div>
    </List.Item>
  );
};

const renderWrappedTextList = (items: any[], accent: 'blue' | 'purple' | 'green' | 'orange' = 'blue') => {
  const borderColor = {
    blue: '#1677ff',
    purple: '#722ed1',
    green: '#52c41a',
    orange: '#fa8c16',
  }[accent];
  const background = {
    blue: 'rgba(22, 119, 255, 0.04)',
    purple: 'rgba(114, 46, 209, 0.04)',
    green: 'rgba(82, 196, 26, 0.05)',
    orange: 'rgba(250, 140, 22, 0.05)',
  }[accent];
  return (
    <List
      size="small"
      dataSource={items}
      renderItem={(item, i) => (
        <List.Item style={{ padding: '6px 0' }}>
          <div style={{
            width: '100%',
            minWidth: 0,
            borderLeft: `3px solid ${borderColor}`,
            background,
            padding: '6px 10px',
            lineHeight: 1.7,
            whiteSpace: 'pre-wrap',
            overflowWrap: 'anywhere',
            wordBreak: 'break-word',
          }}>
            <Text type="secondary" style={{ marginRight: 6 }}>{i + 1}.</Text>
            {structuredText(item)}
          </div>
        </List.Item>
      )}
    />
  );
};

export default function CreateProjectPage() {
  const [chatInput, setChatInput] = useState('');
  const [selectedGenres, setSelectedGenres] = useState<string[]>([]);
  const [selectedTones, setSelectedTones] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState<any>(null);
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [selectedSuggestionIndex, setSelectedSuggestionIndex] = useState(0);
  const [nextQuestions, setNextQuestions] = useState<string[]>([]);
  const [detailOptions, setDetailOptions] = useState<string[]>([]);
  const [styleSkills, setStyleSkills] = useState<any[]>([]);
  const [selectedStyleSkillId, setSelectedStyleSkillId] = useState<string>('');
  const { createProject } = useProjectStore();
  const navigate = useNavigate();
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const generatingRef = useRef(false);
  const restoredRef = useRef(false);

  const stopPolling = useCallback(() => {
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
  }, []);

  const applySavedSession = (saved: any) => {
    if (!saved) return;
    if (Array.isArray(saved.messages)) setMessages(saved.messages);
    if (Array.isArray(saved.selected_genres)) setSelectedGenres(saved.selected_genres);
    if (Array.isArray(saved.selectedGenres)) setSelectedGenres(saved.selectedGenres);
    if (Array.isArray(saved.selected_tones)) setSelectedTones(saved.selected_tones);
    if (Array.isArray(saved.selectedTones)) setSelectedTones(saved.selectedTones);
    if (typeof saved.chat_input === 'string') setChatInput(saved.chat_input);
    if (typeof saved.chatInput === 'string') setChatInput(saved.chatInput);
    if (saved.current_draft) setDraft(saved.current_draft);
    if (saved.draft) setDraft(saved.draft);
    const tonePref = saved.current_draft?.user_tone_preferences || saved.draft?.user_tone_preferences;
    if (typeof tonePref === 'string' && tonePref.trim()) setSelectedTones(tonePref.split(',').map((x: string) => x.trim()).filter(Boolean));
    if (Array.isArray(saved.suggestions)) setSuggestions(saved.suggestions);
    if (Number.isInteger(saved.selected_suggestion_index)) setSelectedSuggestionIndex(saved.selected_suggestion_index);
    if (Number.isInteger(saved.selectedSuggestionIndex)) setSelectedSuggestionIndex(saved.selectedSuggestionIndex);
    if (Array.isArray(saved.next_questions)) setNextQuestions(saved.next_questions);
    if (Array.isArray(saved.nextQuestions)) setNextQuestions(saved.nextQuestions);
    if (Array.isArray(saved.detail_options)) setDetailOptions(saved.detail_options);
    if (Array.isArray(saved.detailOptions)) setDetailOptions(saved.detailOptions);
    if (typeof saved.selected_style_skill_id === 'string') setSelectedStyleSkillId(saved.selected_style_skill_id);
    if (typeof saved.selectedStyleSkillId === 'string') setSelectedStyleSkillId(saved.selectedStyleSkillId);
  };

  const hasSavedSession = (saved: any) => Boolean(
    saved && (
      saved.chat_input?.trim?.()
      || saved.chatInput?.trim?.()
      || saved.messages?.length
      || saved.current_draft
      || saved.draft
      || saved.suggestions?.length
      || saved.selected_genres?.length
      || saved.selectedGenres?.length
      || saved.selected_tones?.length
      || saved.selectedTones?.length
      || saved.selected_style_skill_id
      || saved.selectedStyleSkillId
    )
  );

  useEffect(() => {
    let cancelled = false;
    const restore = async () => {
      try {
        const res = await api.get('/projects/plan-session');
        if (!cancelled && hasSavedSession(res.data?.session)) {
          applySavedSession(res.data.session);
          restoredRef.current = true;
          return;
        }
      } catch {
        // Local draft is still useful when the API is temporarily unavailable.
      }
      try {
        const raw = localStorage.getItem(PLANNING_DRAFT_KEY);
        if (!cancelled && raw) applySavedSession(JSON.parse(raw));
      } catch {
        localStorage.removeItem(PLANNING_DRAFT_KEY);
      }
      restoredRef.current = true;
    };
    restore();
    return () => {
      cancelled = true;
      stopPolling();
    };
  }, [stopPolling]);

  useEffect(() => {
    writingStyleSkillApi.list().then(setStyleSkills).catch(() => setStyleSkills([]));
  }, []);

  useEffect(() => {
    if (!restoredRef.current) return;
    const payload = {
      messages,
      selectedGenres,
      selectedTones,
      chatInput,
      draft,
      suggestions,
      selectedSuggestionIndex,
      nextQuestions,
      detailOptions,
      selectedStyleSkillId,
      updatedAt: Date.now(),
    };
    const hasDraft = chatInput.trim() || messages.length || draft || suggestions.length || selectedGenres.length || selectedTones.length || selectedStyleSkillId;
    if (hasDraft) {
      localStorage.setItem(PLANNING_DRAFT_KEY, JSON.stringify(payload));
      if (saveTimerRef.current) window.clearTimeout(saveTimerRef.current);
      saveTimerRef.current = window.setTimeout(() => {
        api.put('/projects/plan-session', {
          messages,
          selected_genres: selectedGenres,
          selected_tones: selectedTones,
          chat_input: chatInput,
          current_draft: { ...(draft || {}), user_tone_preferences: selectedTones.join(',') },
          suggestions,
          selected_suggestion_index: selectedSuggestionIndex,
          next_questions: nextQuestions,
          detail_options: detailOptions,
        }).catch(() => {});
      }, 700);
    } else {
      localStorage.removeItem(PLANNING_DRAFT_KEY);
    }
    return () => {
      if (saveTimerRef.current) window.clearTimeout(saveTimerRef.current);
    };
  }, [messages, selectedGenres, selectedTones, chatInput, draft, suggestions, selectedSuggestionIndex, nextQuestions, detailOptions, selectedStyleSkillId]);

  const pollTask = async (taskId: string) => new Promise<any>((resolve, reject) => {
    const startedAt = Date.now();
    stopPolling();
    timerRef.current = setInterval(async () => {
      setElapsed(Math.round((Date.now() - startedAt) / 1000));
      try {
        const poll = await api.get(`/projects/plan-task/${taskId}`);
        if (poll.data.status === 'completed') {
          stopPolling();
          resolve(poll.data.result || {});
        } else if (poll.data.status === 'failed') {
          stopPolling();
          reject(new Error(poll.data.error || 'AI 生成失败'));
        }
      } catch {
        stopPolling();
        reject(new Error('请求失败'));
      }
    }, 2000);
  });

  const sendPlanMessage = async (overrideText?: string, intent: 'chat' | 'generate' = 'chat') => {
    const text = (overrideText ?? chatInput).trim();
    if (!text || generatingRef.current) return;
    generatingRef.current = true;
    setLoading(true);
    setElapsed(0);
    const nextMessages: ChatMessage[] = [...messages, { role: 'user', content: text }];
    setMessages(nextMessages);
    if (!overrideText) setChatInput('');
    try {
      const res = await api.post('/projects/plan-chat', {
        messages: nextMessages,
        genres: selectedGenres.join(','),
        style_preferences: selectedTones.join(','),
        current_draft: { ...(draft || {}), user_tone_preferences: selectedTones.join(',') },
        intent,
        style_skill_id: selectedStyleSkillId || null,
      });
      message.loading({ content: intent === 'generate' ? 'AI 正在整理候选方案…' : 'AI 正在和你继续推敲…', key: 'plan', duration: 0 });
      const result = await pollTask(res.data.task_id);
      const assistantReply = result.assistant_reply || '我已经根据你的补充更新了项目草案。';
      const projectDraft = result.project_draft || null;
      setMessages([...nextMessages, { role: 'assistant', content: assistantReply }]);
      const nextSuggestions = intent === 'generate'
        ? (result.suggestions?.length ? result.suggestions.slice(0, 6) : projectDraft ? [projectDraft] : [])
        : (result.suggestions?.length ? result.suggestions.slice(0, 1) : []);
      setDraft(projectDraft || nextSuggestions[0] || null);
      setSuggestions(nextSuggestions);
      setSelectedSuggestionIndex(0);
      setNextQuestions(Array.isArray(result.next_questions) ? result.next_questions.slice(0, 3) : []);
      setDetailOptions(Array.isArray(result.detail_options) ? result.detail_options.slice(0, 5) : []);
      message.success({ content: intent === 'generate' ? `已生成 ${nextSuggestions.length || 1} 个项目方案` : '已更新当前草案', key: 'plan' });
    } catch (e: any) {
      setMessages(messages);
      message.error({ content: e.message || '创建项目失败', key: 'plan' });
    } finally {
      setLoading(false);
      generatingRef.current = false;
    }
  };

  const handleGenerate = async () => {
    if (messages.length === 0) {
      await sendPlanMessage(undefined, 'generate');
      return;
    }
    if (generatingRef.current) return;
    const text = '请基于当前全部对话，重新整理 3-6 个更成熟、更适合长篇连载的项目方案，每个方案都要有明显差异。';
    await sendPlanMessage(text, 'generate');
  };

  const previewSuggestion = (index: number) => {
    const item = suggestions[index];
    if (!item) return;
    setSelectedSuggestionIndex(index);
    setDraft(item);
  };

  const confirmSuggestion = async (s: any) => {
    try {
      const totalWords = normalizeTotalWords(s.total_words) || 300000;
      const pid = await createProject({
        genre: s.genre || selectedGenres[0] || '',
        target_total_words: totalWords,
        story_suggestion: s.brief || '',
        style_skill_id: selectedStyleSkillId || null,
      });
      await api.post(`/projects/${pid}/wizard/apply-story`, {
        title: s.title || '未命名作品',
        genre: s.genre || selectedGenres[0] || '',
        brief: s.brief || '',
        tags: s.tags || [],
        total_words: totalWords,
        planning_messages: messages,
        planning_suggestions: suggestions,
        selected_draft: s,
      });
      localStorage.removeItem(PLANNING_DRAFT_KEY);
      await api.delete('/projects/plan-session').catch(() => {});
      navigate(`/projects/${pid}/wizard`);
    } catch { message.error('保存方案失败'); }
  };

  const resetConversation = () => {
    setMessages([]);
    setDraft(null);
    setSuggestions([]);
    setNextQuestions([]);
    setDetailOptions([]);
    setSelectedSuggestionIndex(0);
    setChatInput('');
    setSelectedTones([]);
    setSelectedStyleSkillId('');
    localStorage.removeItem(PLANNING_DRAFT_KEY);
    api.delete('/projects/plan-session').catch(() => {});
    stopPolling();
    generatingRef.current = false;
  };

  const currentDraft = suggestions[selectedSuggestionIndex] || draft || suggestions[0];

  return (
    <div style={{ maxWidth: 1120, margin: '0 auto', padding: '36px 24px' }}>
      <Space align="center" style={{ marginBottom: 8 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/dashboard')}>返回项目列表</Button>
        <Title level={2} style={{ margin: 0 }}>创建小说项目</Title>
      </Space>
      <Paragraph style={{ color: 'var(--text-secondary)', marginBottom: 24 }}>
        先像聊天一样把想法说出来，AI 会先陪你把细节聊清楚；等方向稳定后再生成 3-6 个候选方案。未确认创建前，对话会自动保存在本机浏览器草稿里。
      </Paragraph>

      <Row gutter={[20, 20]}>
        <Col xs={24} lg={14}>
          <Card title="项目策划对话" style={{ borderRadius: 'var(--radius-lg)' }}>
            <div style={{ marginBottom: 16 }}>
              <Text type="secondary">类型偏好（可选）：</Text>
              <Row gutter={[8, 8]} style={{ marginTop: 8 }}>
                {GENRES.map((g) => (
                  <Col key={g}>
                    <Tag style={{ cursor: 'pointer', userSelect: 'none', padding: '4px 14px', fontSize: 14 }}
                      color={selectedGenres.includes(g) ? 'blue' : 'default'}
                      onClick={() => setSelectedGenres(selectedGenres.includes(g) ? selectedGenres.filter(x => x !== g) : [...selectedGenres, g])}>
                      {g}
                    </Tag>
                  </Col>
                ))}
              </Row>
            </div>

            <div style={{ marginBottom: 16 }}>
              <Text type="secondary">总体风格偏好（可选）：</Text>
              <Row gutter={[8, 8]} style={{ marginTop: 8 }}>
                {TONE_PREFERENCES.map((g) => (
                  <Col key={g}>
                    <Tag style={{ cursor: 'pointer', userSelect: 'none', padding: '4px 14px', fontSize: 14 }}
                      color={selectedTones.includes(g) ? 'geekblue' : 'default'}
                      onClick={() => setSelectedTones(selectedTones.includes(g) ? selectedTones.filter(x => x !== g) : [...selectedTones, g])}>
                      {g}
                    </Tag>
                  </Col>
                ))}
              </Row>
              <Text type="secondary" style={{ display: 'block', marginTop: 6, fontSize: 12 }}>
                这里决定后续大纲、拆卷和正文的整体语气；题材和风格可以组合，比如玄幻也可以轻松、热血或冷峻。
              </Text>
            </div>

            <div style={{ marginBottom: 16 }}>
              <Text type="secondary">共享写作风格 Skill（可选）：</Text>
              <Select
                allowClear
                value={selectedStyleSkillId || undefined}
                onChange={(value) => setSelectedStyleSkillId(value || '')}
                placeholder="选择一个共享 Skill，策划对话和后续大纲/写作会使用"
                style={{ width: '100%', marginTop: 8 }}
                options={styleSkills.map((skill) => ({
                  value: skill.id,
                  label: `${skill.name}${skill.description ? `｜${skill.description}` : ''}`,
                }))}
              />
              <Text type="secondary" style={{ display: 'block', marginTop: 6, fontSize: 12 }}>
                Skill 是共享写作方法库，不属于当前项目；创建后项目只保存引用。
              </Text>
            </div>

            <div style={{ minHeight: 260, maxHeight: 420, overflow: 'auto', padding: 12, background: 'var(--bg)', borderRadius: 8, marginBottom: 16 }}>
              {messages.length === 0 ? (
                <Alert type="info" showIcon message="直接描述你想写的故事，也可以只说一个设定、一个人物、一个爽点。" />
              ) : (
                <List
                  dataSource={messages}
                  renderItem={(m) => (
                    <List.Item style={{ justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start', borderBlockEnd: 0, padding: '6px 0' }}>
                      <div style={{
                        maxWidth: '82%',
                        whiteSpace: 'pre-wrap',
                        background: m.role === 'user' ? '#1677ff' : 'var(--surface)',
                        color: m.role === 'user' ? '#fff' : 'var(--text)',
                        border: '1px solid var(--border)',
                        borderRadius: 8,
                        padding: '10px 12px',
                        lineHeight: 1.7,
                      }}>
                        {m.content}
                      </div>
                    </List.Item>
                  )}
                />
              )}
              {loading && (
                <div style={{ textAlign: 'center', padding: 20 }}>
                  <Spin indicator={<LoadingOutlined spin />} /> <Text type="secondary">AI 正在整理，已等待 {elapsed} 秒</Text>
                </div>
              )}
            </div>

            {(nextQuestions.length > 0 || detailOptions.length > 0) && (
              <div style={{ marginBottom: 12 }}>
                {nextQuestions.length > 0 && (
                  <div style={{ marginBottom: 8 }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>可以继续确认：</Text>
                    <Space wrap style={{ marginTop: 6 }}>
                      {nextQuestions.map((q, i) => (
                        <Tag key={`${q}-${i}`} color="blue" style={{ cursor: 'pointer', padding: '4px 10px' }}
                          onClick={() => setChatInput((prev) => appendInputText(prev, q))}>
                          {q}
                        </Tag>
                      ))}
                    </Space>
                  </div>
                )}
                {detailOptions.length > 0 && (
                  <div>
                    <Text type="secondary" style={{ fontSize: 12 }}>快速补充方向：</Text>
                    <Space wrap style={{ marginTop: 6 }}>
                      {detailOptions.map((q, i) => (
                        <Tag key={`${q}-${i}`} style={{ cursor: 'pointer', padding: '4px 10px' }}
                          onClick={() => setChatInput((prev) => appendInputText(prev, q))}>
                          {q}
                        </Tag>
                      ))}
                    </Space>
                  </div>
                )}
              </div>
            )}

            <TextArea value={chatInput} onChange={(e) => setChatInput(e.target.value)}
              placeholder="比如：都市官场，省委书记找了个和儿子很像的武警当替身，主角一边想上位一边怕被权力吞掉。帮我把这个故事做得更抓人。"
              autoSize={{ minRows: 4, maxRows: 8 }}
              onPressEnter={(e) => {
                if ((e.metaKey || e.ctrlKey) && chatInput.trim()) sendPlanMessage();
              }}
              style={{ borderRadius: 'var(--radius-lg)', fontSize: 15, marginBottom: 12 }} />
            <Space wrap>
              <Button type="primary" icon={<SendOutlined />} onClick={() => sendPlanMessage()} disabled={!chatInput.trim()} loading={loading}>
                继续沟通
              </Button>
              <Button icon={<ThunderboltOutlined />} onClick={handleGenerate} disabled={loading || (!chatInput.trim() && messages.length === 0)}>
                生成3-6个方案
              </Button>
              <Button icon={<ReloadOutlined />} onClick={resetConversation} disabled={loading}>
                清空本地草稿
              </Button>
            </Space>
          </Card>
        </Col>

        <Col xs={24} lg={10}>
          <Card title="当前项目草案" style={{ borderRadius: 'var(--radius-lg)', marginBottom: 16 }}>
            {currentDraft ? (
              <>
                <Title level={4} style={{ marginTop: 0 }}>{currentDraft.title || '未命名作品'}</Title>
                <Space wrap style={{ marginBottom: 12 }}>
                  {currentDraft.genre && <Tag color="blue">{currentDraft.genre}</Tag>}
                  {currentDraft.length_type && <Tag color="purple">{currentDraft.length_type}</Tag>}
                  {currentDraft.tone_profile?.tone_label && <Tag color="geekblue">{currentDraft.tone_profile.tone_label}</Tag>}
                  {(currentDraft.tags || []).map((t: string) => <Tag key={t}>{t}</Tag>)}
                  <Tag>{formatTotalWords(currentDraft.total_words)}</Tag>
                </Space>
                {currentDraft.reader_promise && (
                  <Alert type="success" showIcon message={currentDraft.reader_promise} style={{ marginBottom: 12 }} />
                )}
                {currentDraft.core_engine && (
                  <Paragraph style={{ marginBottom: 8 }}>
                    <Text strong>核心引擎：</Text>{currentDraft.core_engine}
                  </Paragraph>
                )}
                <Paragraph style={{ whiteSpace: 'pre-wrap', lineHeight: 1.8 }}>{currentDraft.brief || '暂无梗概'}</Paragraph>
                {currentDraft.tone_profile && (
                  <DraftSection title="总体风格">
                    {[
                      renderMetaLine('风格定位', currentDraft.tone_profile.tone_label),
                      renderMetaLine('叙事质感', currentDraft.tone_profile.narrative_texture),
                      renderMetaLine('节奏', currentDraft.tone_profile.pacing),
                      renderMetaLine('幽默程度', currentDraft.tone_profile.humor_level),
                      renderMetaLine('情绪温度', currentDraft.tone_profile.emotional_temperature),
                      renderMetaLine('语言手感', currentDraft.tone_profile.language_style),
                      renderMetaLine('写作禁忌', currentDraft.tone_profile.taboos),
                    ].filter(Boolean)}
                  </DraftSection>
                )}
                {currentDraft.type_model && (
                  <DraftSection title="题材模型">
                    {[
                      renderMetaLine('主类型', currentDraft.type_model.primary_genre),
                      renderMetaLine('读者期待', currentDraft.type_model.reader_expectation),
                      renderMetaLine('核心奖励', currentDraft.type_model.core_reader_reward),
                      renderMetaLine('冲突形态', currentDraft.type_model.main_conflict_form),
                      renderMetaLine('反馈循环', currentDraft.type_model.upgrade_feedback_loop),
                      renderMetaLine('早期阻力', currentDraft.type_model.early_obstacle_pattern),
                    ].filter(Boolean)}
                  </DraftSection>
                )}
                {currentDraft.first_volume_engine && (
                  <DraftSection title="第一卷发动机">
                    {[
                      renderMetaLine('第一卷承诺', currentDraft.first_volume_engine.volume_promise),
                      renderMetaLine('主角第一动作', currentDraft.first_volume_engine.protagonist_first_move),
                      renderMetaLine('早期可见阻力', currentDraft.first_volume_engine.early_visible_opponent),
                      renderMetaLine('第一反馈', currentDraft.first_volume_engine.first_reward),
                      renderMetaLine('第一代价', currentDraft.first_volume_engine.first_cost),
                      renderMetaLine('卷末钩子', currentDraft.first_volume_engine.volume_hook),
                    ].filter(Boolean)}
                  </DraftSection>
                )}
                {Array.isArray(currentDraft.early_event_chain) && currentDraft.early_event_chain.length > 0 && (
                  <DraftSection title="早期事件链">
                    <List
                      size="small"
                      dataSource={currentDraft.early_event_chain.slice(0, 6)}
                      renderItem={renderEventChainItem}
                    />
                  </DraftSection>
                )}
                {currentDraft.readability_gate && (
                  <DraftSection title="可读性闸门">
                    {currentDraft.readability_gate.passed !== undefined && (
                      <Tag color={currentDraft.readability_gate.passed ? 'green' : 'orange'}>
                        {currentDraft.readability_gate.passed ? '已通过' : '需加固'}
                      </Tag>
                    )}
                    {asTextList(currentDraft.readability_gate.risks).map((item, i) => <Tag key={`risk-${i}`} color="orange" style={{ marginBottom: 6 }}>{item}</Tag>)}
                    {asTextList(currentDraft.readability_gate.fix_strategy).map((item, i) => <Tag key={`fix-${i}`} color="green" style={{ marginBottom: 6 }}>{item}</Tag>)}
                  </DraftSection>
                )}
                {asTextList(currentDraft.boundary_locks).length > 0 && (
                  <DraftSection title="边界锁定">
                    {renderWrappedTextList(currentDraft.boundary_locks || [], 'orange')}
                  </DraftSection>
                )}
                {currentDraft.long_term_plan?.endgame && (
                  <DraftSection title="终局指向">
                    <Paragraph style={{ whiteSpace: 'pre-wrap', marginBottom: 0 }}>{currentDraft.long_term_plan.endgame}</Paragraph>
                  </DraftSection>
                )}
                {Array.isArray(currentDraft.long_term_plan?.stage_plan) && currentDraft.long_term_plan.stage_plan.length > 0 && (
                  <DraftSection title="长线阶段">
                    <List
                      size="small"
                      dataSource={currentDraft.long_term_plan.stage_plan}
                      renderItem={renderStagePlanItem}
                    />
                  </DraftSection>
                )}
                {asTextList(currentDraft.long_term_plan?.foreshadowing_payoffs).length > 0 && (
                  <DraftSection title="伏笔回收">
                    {renderWrappedTextList(currentDraft.long_term_plan?.foreshadowing_payoffs || [], 'purple')}
                  </DraftSection>
                )}
                {currentDraft.open_questions?.length > 0 && (
                  <>
                    <Divider style={{ margin: '12px 0' }} />
                    <Text strong>还需要确认：</Text>
                    <div style={{ marginTop: 8 }}>
                      {currentDraft.open_questions.map((q: string, i: number) => <Tag key={i} style={{ marginBottom: 6 }}>{q}</Tag>)}
                    </div>
                  </>
                )}
                <Button type="primary" icon={<CheckOutlined />} block style={{ marginTop: 16 }} onClick={() => confirmSuggestion(currentDraft)}>
                  确认当前方案，创建项目并进入向导
                </Button>
              </>
            ) : (
              <Alert message="草案会在第一次对话后生成" type="info" showIcon />
            )}
          </Card>

          {suggestions.length > 0 && (
            <Card title={`可选方向（${suggestions.length}个）`} style={{ borderRadius: 'var(--radius-lg)' }}>
              <Space wrap style={{ marginBottom: 12 }}>
                {suggestions.map((s, i) => (
                  <Tag key={`${s.title || '方案'}-${i}`}
                    color={i === selectedSuggestionIndex ? 'blue' : 'default'}
                    style={{ cursor: 'pointer', userSelect: 'none', padding: '4px 12px' }}
                    onClick={() => previewSuggestion(i)}>
                    方案 {i + 1}
                  </Tag>
                ))}
              </Space>
              <List
                dataSource={suggestions}
                renderItem={(s, i) => (
                  <List.Item>
                    <Card size="small" hoverable
                      style={{ width: '100%', borderRadius: 8, borderColor: i === selectedSuggestionIndex ? '#1677ff' : undefined, cursor: 'pointer' }}
                      onClick={() => previewSuggestion(i)}>
                      <Space wrap style={{ marginBottom: 8 }}>
                        <Tag color={i === selectedSuggestionIndex ? 'blue' : 'default'}>{i === selectedSuggestionIndex ? '当前预览' : `方案 ${i + 1}`}</Tag>
                        <Text strong>{s.title || `未命名方案`}</Text>
                        {s.genre && <Tag color="blue">{s.genre}</Tag>}
                        {s.length_type && <Tag color="purple">{s.length_type}</Tag>}
                        {s.tone_profile?.tone_label && <Tag color="geekblue">{s.tone_profile.tone_label}</Tag>}
                      </Space>
                      {s.core_engine && <Paragraph ellipsis={{ rows: 2 }} style={{ marginBottom: 8 }}><Text strong>引擎：</Text>{s.core_engine}</Paragraph>}
                      {s.reader_promise && <Paragraph ellipsis={{ rows: 2 }} style={{ marginBottom: 8 }}><Text strong>追读：</Text>{s.reader_promise}</Paragraph>}
                      <Paragraph ellipsis={{ rows: 4 }} style={{ marginBottom: 8 }}>{s.brief}</Paragraph>
                      <div>{(s.tags || []).map((t: string) => <Tag key={t}>{t}</Tag>)}</div>
                    </Card>
                  </List.Item>
                )}
              />
            </Card>
          )}
        </Col>
      </Row>
    </div>
  );
}
