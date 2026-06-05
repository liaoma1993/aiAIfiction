import { useEffect, useMemo, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Alert, Button, Drawer, Empty, Input, Segmented, Space, Spin, Tag, Typography, message } from 'antd';
import { LeftOutlined, SearchOutlined, TeamOutlined, UserAddOutlined } from '@ant-design/icons';
import { characterApi } from '@/services/projectApi';
import './CharactersPage.css';

const { Title, Text, Paragraph } = Typography;

const LEGACY_ROLE_LABELS: Record<string, string> = {
  protagonist: '主角', antagonist: '反派', supporting: '配角', mentor: '导师',
  love_interest: '恋人', hero: '主角', villain: '反派', sidekick: '配角', master: '导师', other: '其他',
};

const ROLE_COLORS: Record<string, string> = {
  主角: 'blue',
  反派: 'red',
  配角: 'default',
  导师: 'purple',
  恋人: 'pink',
  搞笑担当: 'gold',
};

function roleLabel(role: string) {
  return LEGACY_ROLE_LABELS[role] || role || '配角';
}

function compactState(state: any) {
  if (!state || typeof state !== 'object' || !Object.keys(state).length) return '暂无状态';
  return Object.entries(state).slice(0, 3).map(([k, v]) => `${k}：${typeof v === 'string' ? v : JSON.stringify(v)}`).join('；');
}

function profileScore(char: any) {
  const fields = ['personality', 'background', 'motivation', 'behavior_pattern', 'language_style', 'appearance', 'growth_arc', 'inner_conflict'];
  return fields.filter((key) => String(char?.[key] || '').trim()).length;
}

export default function CharactersPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [characters, setCharacters] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState('');
  const [roleType, setRoleType] = useState('配角');
  const [selectedChar, setSelectedChar] = useState<any>(null);
  const [stateText, setStateText] = useState('');
  const [query, setQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState('全部');
  const [savingState, setSavingState] = useState(false);

  useEffect(() => {
    if (!projectId) return;
    characterApi.list(projectId).then((chs) => { setCharacters(chs); setLoading(false); });
  }, [projectId]);

  const roles = useMemo(() => {
    const values = Array.from(new Set(characters.map((c) => roleLabel(c.role_type)).filter(Boolean)));
    return ['全部', ...values];
  }, [characters]);

  const filteredCharacters = useMemo(() => {
    const q = query.trim().toLowerCase();
    return characters.filter((char) => {
      const role = roleLabel(char.role_type);
      const roleOk = roleFilter === '全部' || role === roleFilter;
      const text = `${char.name || ''} ${role} ${char.personality || ''} ${char.background || ''} ${char.motivation || ''}`.toLowerCase();
      return roleOk && (!q || text.includes(q));
    });
  }, [characters, query, roleFilter]);

  const addChar = async () => {
    if (!name.trim() || !projectId) return;
    const c = await characterApi.create(projectId, { name: name.trim(), role_type: roleType.trim() || '配角' });
    setCharacters([...characters, c]);
    setName('');
    message.success('角色已添加');
  };

  const openDrawer = (char: any) => {
    setSelectedChar(char);
    setStateText(JSON.stringify(char.current_state || {}, null, 2));
  };

  const saveState = async () => {
    if (!projectId || !selectedChar) return;
    setSavingState(true);
    try {
      const parsed = stateText.trim() ? JSON.parse(stateText) : {};
      const updated = await characterApi.update(projectId, selectedChar.id, { current_state: parsed });
      setCharacters(characters.map((c) => c.id === updated.id ? updated : c));
      setSelectedChar(updated);
      message.success('状态已保存');
    } catch {
      message.error('JSON 格式不正确');
    }
    setSavingState(false);
  };

  if (loading) return <div className="characters-loading"><Spin /></div>;

  return (
    <div className="characters-page">
      <header className="characters-header">
        <Link to={`/projects/${projectId}`}><Button icon={<LeftOutlined />} size="small">返回工作台</Button></Link>
        <div className="characters-titleblock">
          <Title level={3}>角色管理</Title>
          <Text type="secondary">维护角色档案和当前状态，后续章节会读取这些信息保证连续性。</Text>
        </div>
      </header>

      <section className="characters-stats">
        <div><Text type="secondary">角色总数</Text><strong>{characters.length}</strong></div>
        <div><Text type="secondary">主角</Text><strong>{characters.filter((c) => roleLabel(c.role_type) === '主角').length}</strong></div>
        <div><Text type="secondary">反派</Text><strong>{characters.filter((c) => roleLabel(c.role_type) === '反派').length}</strong></div>
        <div><Text type="secondary">有状态</Text><strong>{characters.filter((c) => c.current_state && Object.keys(c.current_state).length).length}</strong></div>
      </section>

      <section className="characters-toolbar">
        <div className="characters-addbar">
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="角色名" />
          <Input value={roleType} onChange={(e) => setRoleType(e.target.value)} placeholder="类型，如 主角/反派/吐槽担当" />
          <Button type="primary" icon={<UserAddOutlined />} onClick={addChar}>添加</Button>
        </div>
        <div className="characters-filterbar">
          <Segmented value={roleFilter} onChange={(v) => setRoleFilter(String(v))} options={roles.map((r) => ({ label: r, value: r }))} />
          <Input allowClear prefix={<SearchOutlined />} value={query} onChange={(e) => setQuery(e.target.value)} placeholder="搜索角色、性格、动机" />
        </div>
      </section>

      <Alert className="characters-alert" type="info" showIcon message="角色当前状态会进入故事上下文，影响后续章节生成和连续性审计。" />

      {!filteredCharacters.length ? <Empty description="暂无角色" /> : (
        <section className="characters-grid">
          {filteredCharacters.map((char) => {
            const role = roleLabel(char.role_type);
            return (
              <button key={char.id} className="character-card" onClick={() => openDrawer(char)}>
                <div className="character-card-head">
                  <span className="character-avatar"><TeamOutlined /></span>
                  <span className="character-main">
                    <Text strong className="character-name">{char.name}</Text>
                    <span>
                      <Tag color={ROLE_COLORS[role] || 'default'}>{role}</Tag>
                      {char.character_class === 'one_off' && <Tag>路人</Tag>}
                    </span>
                  </span>
                </div>
                <Paragraph className="character-summary">{char.personality || char.motivation || char.background || '暂无角色描述'}</Paragraph>
                <div className="character-meta">
                  <span>档案 {profileScore(char)}/8</span>
                  {char.faction_rank && <span>{char.faction_rank}</span>}
                </div>
                <div className="character-state">{compactState(char.current_state)}</div>
              </button>
            );
          })}
        </section>
      )}

      <Drawer title={selectedChar ? `${selectedChar.name} · 角色详情` : '角色详情'} open={!!selectedChar} onClose={() => setSelectedChar(null)} width={520}>
        {selectedChar && (
          <div className="character-drawer">
            <Space wrap>
              <Tag color={ROLE_COLORS[roleLabel(selectedChar.role_type)] || 'default'}>{roleLabel(selectedChar.role_type)}</Tag>
              {selectedChar.faction_rank && <Tag>{selectedChar.faction_rank}</Tag>}
            </Space>
            <Title level={4}>{selectedChar.name}</Title>
            <div className="character-detail-list">
              {[
                ['性格', selectedChar.personality],
                ['背景', selectedChar.background],
                ['动机', selectedChar.motivation],
                ['行为模式', selectedChar.behavior_pattern],
                ['语言风格', selectedChar.language_style],
                ['成长弧', selectedChar.growth_arc],
                ['内在矛盾', selectedChar.inner_conflict],
              ].map(([label, value]) => (
                <div key={label}>
                  <Text strong>{label}</Text>
                  <Paragraph>{value || '未填写'}</Paragraph>
                </div>
              ))}
            </div>
            <Title level={5}>当前状态</Title>
            <Alert type="info" showIcon message="请用 JSON 形式编辑，例如修为、情绪、关系、已知信息。" />
            <Input.TextArea className="character-state-editor" value={stateText} onChange={(e) => setStateText(e.target.value)} autoSize={{ minRows: 12, maxRows: 24 }} />
            <Button type="primary" loading={savingState} onClick={saveState}>保存状态</Button>
          </div>
        )}
      </Drawer>
    </div>
  );
}
