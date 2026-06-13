import { useEffect, useMemo, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Alert, Button, Drawer, Empty, Input, Popconfirm, Segmented, Space, Spin, Tabs, Tag, Typography, message } from 'antd';
import { ApartmentOutlined, DeleteOutlined, LeftOutlined, PlusOutlined, SearchOutlined, TeamOutlined, UserAddOutlined } from '@ant-design/icons';
import { characterApi, factionApi } from '@/services/projectApi';
import './CharactersPage.css';
import './FactionsPage.css';

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

const LEGACY_FACTION_LABELS: Record<string, string> = {
  sect: '门派', family: '家族', empire: '帝国', guild: '商会', merchant_guild: '商会',
  dark_org: '暗组织', race: '种族', tribe: '部落', alliance: '联盟', temple: '神殿', academy: '学院', court: '朝廷',
};

const TYPE_COLORS: Record<string, string> = {
  门派: 'blue',
  宗门: 'blue',
  家族: 'purple',
  帝国: 'volcano',
  商会: 'gold',
  暗组织: 'red',
  联盟: 'cyan',
  学院: 'geekblue',
  朝廷: 'magenta',
};

function roleLabel(role: string) {
  return LEGACY_ROLE_LABELS[role] || role || '配角';
}

function typeLabel(type: string) {
  return LEGACY_FACTION_LABELS[type] || type || '组织';
}

function textList(value: any) {
  if (!value) return '';
  if (Array.isArray(value)) return value.map((item) => typeof item === 'string' ? item : JSON.stringify(item)).join('；');
  return String(value);
}

function compactTagText(value: any, max = 12) {
  const text = textList(value).trim();
  if (!text) return '';
  return text.length > max ? `${text.slice(0, max)}...` : text;
}

function compactState(state: any) {
  if (!state || typeof state !== 'object' || !Object.keys(state).length) return '暂无状态';
  return Object.entries(state).slice(0, 3).map(([k, v]) => `${k}：${typeof v === 'string' ? v : JSON.stringify(v)}`).join('；');
}

function profileScore(char: any) {
  const fields = ['personality', 'background', 'motivation', 'behavior_pattern', 'language_style', 'appearance', 'growth_arc', 'inner_conflict'];
  return fields.filter((key) => String(char?.[key] || '').trim()).length;
}

function factionCompleteness(faction: any) {
  const fields = ['description', 'headquarters', 'territory', 'core_creed', 'core_conflict_of_interest', 'internal_faction_cracks', 'reputation_and_reality'];
  return fields.filter((key) => String(faction?.[key] || '').trim()).length;
}

export default function CharactersPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [characters, setCharacters] = useState<any[]>([]);
  const [factions, setFactions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState('');
  const [roleType, setRoleType] = useState('配角');
  const [factionName, setFactionName] = useState('');
  const [factionType, setFactionType] = useState('组织');
  const [selectedChar, setSelectedChar] = useState<any>(null);
  const [selectedFaction, setSelectedFaction] = useState<any>(null);
  const [stateText, setStateText] = useState('');
  const [query, setQuery] = useState('');
  const [factionQuery, setFactionQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState('全部');
  const [typeFilter, setTypeFilter] = useState('全部');
  const [savingState, setSavingState] = useState(false);

  useEffect(() => {
    if (!projectId) return;
    Promise.all([
      characterApi.list(projectId),
      factionApi.list(projectId),
    ]).then(([chs, fs]) => {
      setCharacters(chs);
      setFactions(fs);
      setLoading(false);
    });
  }, [projectId]);

  const roles = useMemo(() => {
    const values = Array.from(new Set(characters.map((c) => roleLabel(c.role_type)).filter(Boolean)));
    return ['全部', ...values];
  }, [characters]);

  const factionTypes = useMemo(() => {
    const values = Array.from(new Set(factions.map((f) => typeLabel(f.faction_type)).filter(Boolean)));
    return ['全部', ...values];
  }, [factions]);

  const filteredCharacters = useMemo(() => {
    const q = query.trim().toLowerCase();
    return characters.filter((char) => {
      const role = roleLabel(char.role_type);
      const roleOk = roleFilter === '全部' || role === roleFilter;
      const text = `${char.name || ''} ${role} ${char.personality || ''} ${char.background || ''} ${char.motivation || ''}`.toLowerCase();
      return roleOk && (!q || text.includes(q));
    });
  }, [characters, query, roleFilter]);

  const filteredFactions = useMemo(() => {
    const q = factionQuery.trim().toLowerCase();
    return factions.filter((faction) => {
      const type = typeLabel(faction.faction_type);
      const typeOk = typeFilter === '全部' || type === typeFilter;
      const text = `${faction.name || ''} ${type} ${faction.description || ''} ${faction.core_creed || ''} ${faction.headquarters || ''} ${faction.territory || ''}`.toLowerCase();
      return typeOk && (!q || text.includes(q));
    });
  }, [factions, factionQuery, typeFilter]);

  const addChar = async () => {
    if (!name.trim() || !projectId) return;
    const c = await characterApi.create(projectId, { name: name.trim(), role_type: roleType.trim() || '配角' });
    setCharacters([...characters, c]);
    setName('');
    message.success('角色已添加');
  };

  const addFaction = async () => {
    if (!factionName.trim() || !projectId) return;
    const f = await factionApi.create(projectId, { name: factionName.trim(), faction_type: factionType.trim() || '组织' });
    setFactions([...factions, f]);
    setFactionName('');
    message.success('势力已添加');
  };

  const removeFaction = async (faction: any) => {
    if (!projectId) return;
    await factionApi.remove(projectId, faction.id);
    setFactions(factions.filter((item) => item.id !== faction.id));
    if (selectedFaction?.id === faction.id) setSelectedFaction(null);
    message.success('势力已删除');
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
          <Title level={3}>角色势力管理</Title>
          <Text type="secondary">统一维护角色档案、当前状态和势力格局，后续章节会读取这些信息保证连续性。</Text>
        </div>
      </header>

      <section className="characters-stats">
        <div><Text type="secondary">角色总数</Text><strong>{characters.length}</strong></div>
        <div><Text type="secondary">主角</Text><strong>{characters.filter((c) => roleLabel(c.role_type) === '主角').length}</strong></div>
        <div><Text type="secondary">势力总数</Text><strong>{factions.length}</strong></div>
        <div><Text type="secondary">有状态角色</Text><strong>{characters.filter((c) => c.current_state && Object.keys(c.current_state).length).length}</strong></div>
      </section>

      <Tabs
        className="characters-factions-tabs"
        defaultActiveKey="characters"
        items={[
          {
            key: 'characters',
            label: <span><TeamOutlined /> 角色</span>,
            children: (
              <>
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
              </>
            ),
          },
          {
            key: 'factions',
            label: <span><ApartmentOutlined /> 势力</span>,
            children: (
              <>
                <section className="factions-toolbar">
                  <div className="factions-addbar">
                    <Input value={factionName} onChange={(e) => setFactionName(e.target.value)} placeholder="势力名" />
                    <Input value={factionType} onChange={(e) => setFactionType(e.target.value)} placeholder="类型，如 公司/门派/高维组织" />
                    <Button type="primary" icon={<PlusOutlined />} onClick={addFaction}>添加</Button>
                  </div>
                  <div className="factions-filterbar">
                    <Segmented value={typeFilter} onChange={(v) => setTypeFilter(String(v))} options={factionTypes.map((t) => ({ label: t, value: t }))} />
                    <Input allowClear prefix={<SearchOutlined />} value={factionQuery} onChange={(e) => setFactionQuery(e.target.value)} placeholder="搜索势力、信条、总部、地盘" />
                  </div>
                </section>

                {!filteredFactions.length ? <Empty description="暂无势力" /> : (
                  <section className="factions-grid">
                    {filteredFactions.map((faction) => {
                      const label = typeLabel(faction.faction_type);
                      return (
                        <article key={faction.id} className="faction-card">
                          <button className="faction-card-body" onClick={() => setSelectedFaction(faction)}>
                            <span className="faction-icon"><ApartmentOutlined /></span>
                            <span className="faction-main">
                              <Text strong className="faction-name">{faction.name}</Text>
                              <span>
                                <Tag color={TYPE_COLORS[label] || 'default'}>{label}</Tag>
                                {compactTagText(faction.headquarters) && <Tag title={textList(faction.headquarters)}>{compactTagText(faction.headquarters)}</Tag>}
                              </span>
                            </span>
                            <Paragraph className="faction-summary">{faction.core_creed || faction.description || faction.core_conflict_of_interest || '暂无势力描述'}</Paragraph>
                            <div className="faction-meta">
                              <span>档案 {factionCompleteness(faction)}/7</span>
                              {faction.territory && <span>{faction.territory}</span>}
                            </div>
                          </button>
                          <Popconfirm title="删除这个势力？" onConfirm={() => removeFaction(faction)}>
                            <Button className="faction-delete" size="small" type="text" danger icon={<DeleteOutlined />} />
                          </Popconfirm>
                        </article>
                      );
                    })}
                  </section>
                )}
              </>
            ),
          },
        ]}
      />

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

      <Drawer title={selectedFaction ? `${selectedFaction.name} · 势力详情` : '势力详情'} open={!!selectedFaction} onClose={() => setSelectedFaction(null)} width={520}>
        {selectedFaction && (
          <div className="faction-drawer">
            <Space wrap>
              <Tag color={TYPE_COLORS[typeLabel(selectedFaction.faction_type)] || 'default'}>{typeLabel(selectedFaction.faction_type)}</Tag>
            </Space>
            <Title level={4}>{selectedFaction.name}</Title>
            <div className="faction-detail-list">
              {[
                ['描述', selectedFaction.description],
                ['核心信条', selectedFaction.core_creed],
                ['总部', selectedFaction.headquarters],
                ['地盘', selectedFaction.territory],
                ['利益冲突', selectedFaction.core_conflict_of_interest],
                ['内部裂缝', selectedFaction.internal_faction_cracks],
                ['名声与真实', selectedFaction.reputation_and_reality],
                ['层级结构', textList(selectedFaction.hierarchy)],
                ['重要成员', textList(selectedFaction.notable_members)],
              ].map(([label, value]) => (
                <div key={label}>
                  <Text strong>{label}</Text>
                  <Paragraph>{value || '未填写'}</Paragraph>
                </div>
              ))}
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
}
