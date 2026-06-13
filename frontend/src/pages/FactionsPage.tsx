import { useEffect, useMemo, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Button, Drawer, Empty, Input, Popconfirm, Segmented, Space, Spin, Tag, Typography, message } from 'antd';
import { ApartmentOutlined, DeleteOutlined, LeftOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons';
import { factionApi } from '@/services/projectApi';
import './FactionsPage.css';

const { Title, Text, Paragraph } = Typography;

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

function completeness(faction: any) {
  const fields = ['description', 'headquarters', 'territory', 'core_creed', 'core_conflict_of_interest', 'internal_faction_cracks', 'reputation_and_reality'];
  return fields.filter((key) => String(faction?.[key] || '').trim()).length;
}

export default function FactionsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [factions, setFactions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState('');
  const [factionType, setFactionType] = useState('组织');
  const [query, setQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('全部');
  const [selectedFaction, setSelectedFaction] = useState<any>(null);

  useEffect(() => {
    if (!projectId) return;
    factionApi.list(projectId).then((fs) => { setFactions(fs); setLoading(false); });
  }, [projectId]);

  const types = useMemo(() => {
    const values = Array.from(new Set(factions.map((f) => typeLabel(f.faction_type)).filter(Boolean)));
    return ['全部', ...values];
  }, [factions]);

  const filteredFactions = useMemo(() => {
    const q = query.trim().toLowerCase();
    return factions.filter((faction) => {
      const type = typeLabel(faction.faction_type);
      const typeOk = typeFilter === '全部' || type === typeFilter;
      const text = `${faction.name || ''} ${type} ${faction.description || ''} ${faction.core_creed || ''} ${faction.headquarters || ''} ${faction.territory || ''}`.toLowerCase();
      return typeOk && (!q || text.includes(q));
    });
  }, [factions, query, typeFilter]);

  const addFaction = async () => {
    if (!name.trim() || !projectId) return;
    const f = await factionApi.create(projectId, { name: name.trim(), faction_type: factionType.trim() || '组织' });
    setFactions([...factions, f]);
    setName('');
    message.success('势力已添加');
  };

  const removeFaction = async (faction: any) => {
    if (!projectId) return;
    await factionApi.remove(projectId, faction.id);
    setFactions(factions.filter((item) => item.id !== faction.id));
    if (selectedFaction?.id === faction.id) setSelectedFaction(null);
    message.success('势力已删除');
  };

  if (loading) return <div className="factions-loading"><Spin /></div>;

  return (
    <div className="factions-page">
      <header className="factions-header">
        <Link to={`/projects/${projectId}`}><Button icon={<LeftOutlined />} size="small">返回工作台</Button></Link>
        <div className="factions-titleblock">
          <Title level={3}>势力管理</Title>
          <Text type="secondary">维护组织、阵营、公司、门派等势力档案，帮助生成稳定的冲突格局。</Text>
        </div>
      </header>

      <section className="factions-stats">
        <div><Text type="secondary">势力总数</Text><strong>{factions.length}</strong></div>
        <div><Text type="secondary">类型数</Text><strong>{types.length - 1}</strong></div>
        <div><Text type="secondary">有信条</Text><strong>{factions.filter((f) => f.core_creed).length}</strong></div>
        <div><Text type="secondary">有总部</Text><strong>{factions.filter((f) => f.headquarters).length}</strong></div>
      </section>

      <section className="factions-toolbar">
        <div className="factions-addbar">
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="势力名" />
          <Input value={factionType} onChange={(e) => setFactionType(e.target.value)} placeholder="类型，如 公司/门派/高维组织" />
          <Button type="primary" icon={<PlusOutlined />} onClick={addFaction}>添加</Button>
        </div>
        <div className="factions-filterbar">
          <Segmented value={typeFilter} onChange={(v) => setTypeFilter(String(v))} options={types.map((t) => ({ label: t, value: t }))} />
          <Input allowClear prefix={<SearchOutlined />} value={query} onChange={(e) => setQuery(e.target.value)} placeholder="搜索势力、信条、总部、地盘" />
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
                    <span>档案 {completeness(faction)}/7</span>
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
