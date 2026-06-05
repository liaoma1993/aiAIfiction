import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Card, Typography, Input, Button, Row, Col, Spin, Tag, Alert } from 'antd';
import {
  BankOutlined,
  EnvironmentOutlined,
  ExperimentOutlined,
  HistoryOutlined,
  LeftOutlined,
  LockOutlined,
  SkinOutlined,
} from '@ant-design/icons';
import { worldSettingApi } from '@/services/projectApi';
import './WorldSettingPage.css';

const { Title, Text, Paragraph } = Typography;

const DIMS = [
  { key: 'geography', label: '地理环境', icon: EnvironmentOutlined },
  { key: 'social_structure', label: '社会结构', icon: BankOutlined },
  { key: 'power_system', label: '力量体系', icon: ExperimentOutlined },
  { key: 'history', label: '历史背景', icon: HistoryOutlined },
  { key: 'culture', label: '文化习俗', icon: SkinOutlined },
  { key: 'special_rules', label: '特殊规则', icon: LockOutlined },
];

export default function WorldSettingPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [ws, setWs] = useState<any>({});
  const [editing, setEditing] = useState<string | null>(null);
  const [editText, setEditText] = useState('');
  const [ruleText, setRuleText] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!projectId) return;
    worldSettingApi.get(projectId).then(setWs).finally(() => setLoading(false));
  }, [projectId]);

  const saveDim = async (key: string) => {
    if (!projectId) return;
    const updated = await worldSettingApi.update(projectId, { [key]: { content: editText } });
    setWs(updated);
    setEditing(null);
  };

  const addRule = async (key: 'hard_rules' | 'tone_rules' | 'constraints') => {
    if (!projectId || !ruleText.trim()) return;
    const next = [...(ws?.[key] || []), ruleText.trim()];
    const updated = await worldSettingApi.update(projectId, { [key]: next });
    setWs(updated);
    setRuleText('');
    setEditing(null);
  };

  const removeRule = async (key: 'hard_rules' | 'tone_rules' | 'constraints', idx: number) => {
    if (!projectId) return;
    const next = (ws?.[key] || []).filter((_: string, i: number) => i !== idx);
    const updated = await worldSettingApi.update(projectId, { [key]: next });
    setWs(updated);
  };

  if (loading) return <div className="world-setting-loading"><Spin /></div>;

  return (
    <div className="world-setting-page">
      <div className="world-setting-header">
        <Link to={`/projects/${projectId}`}><Button icon={<LeftOutlined />} size="small">返回工作台</Button></Link>
        <div className="world-setting-titleblock">
          <Title level={3}>世界观设定</Title>
          <Text type="secondary">维护章节生成会读取的世界规则、叙事边界和六维设定。</Text>
        </div>
      </div>
      <Alert className="world-setting-alert" type="info" showIcon
        message="硬约束会进入章节生成上下文，AI 写作和审计会优先遵守这些规则。" />
      <Row gutter={[12, 12]} className="world-rule-grid">
        {[
          { key: 'hard_rules', title: '硬约束', color: 'red', desc: '绝对不能违反的世界规则' },
          { key: 'tone_rules', title: '文风氛围', color: 'blue', desc: '用于保持世界质感和叙事风格' },
          { key: 'constraints', title: '生成限制', color: 'orange', desc: '写作时需要避开的内容或边界' },
        ].map((block: any) => (
          <Col xs={24} lg={8} key={block.key}>
            <Card title={block.title} size="small" className="world-rule-card">
              <Paragraph className="world-card-desc">{block.desc}</Paragraph>
              <div className="world-rule-tags">
                {(ws?.[block.key] || []).map((r: string, i: number) => (
                  <Tag className="world-rule-tag" key={`${r}-${i}`} color={block.color} closable onClose={(e) => { e.preventDefault(); removeRule(block.key, i); }}>{r}</Tag>
                ))}
                {!(ws?.[block.key] || []).length && <Text className="world-empty-text">暂无规则</Text>}
              </div>
              {editing === block.key ? (
                <div className="world-inline-editor">
                  <Input value={ruleText} onChange={(e) => setRuleText(e.target.value)} placeholder="新增规则" />
                  <Button type="primary" onClick={() => addRule(block.key)}>添加</Button>
                  <Button onClick={() => { setEditing(null); setRuleText(''); }}>取消</Button>
                </div>
              ) : (
                <Button size="small" onClick={() => { setEditing(block.key); setRuleText(''); }}>新增</Button>
              )}
            </Card>
          </Col>
        ))}
      </Row>
      <Row gutter={[12, 12]} className="world-dim-grid">
        {DIMS.map((d) => (
          <Col xs={24} md={12} xl={8} key={d.key}>
            <Card
              className="world-dim-card"
              title={<span className="world-dim-title"><d.icon />{d.label}</span>}
            >
              {editing === d.key ? (
                <div className="world-dim-editor">
                  <Input.TextArea value={editText} onChange={(e) => setEditText(e.target.value)} autoSize={{ minRows: 5, maxRows: 10 }} />
                  <div className="world-editor-actions">
                    <Button type="primary" size="small" onClick={() => saveDim(d.key)}>保存</Button>
                    <Button size="small" onClick={() => setEditing(null)}>取消</Button>
                  </div>
                </div>
              ) : (
                <div className="world-dim-content">
                  <Paragraph className="world-dim-text">
                    {ws?.[d.key]?.content || '点击编辑开始填写…'}
                  </Paragraph>
                  <Button size="small" onClick={() => { setEditing(d.key); setEditText(ws?.[d.key]?.content || ''); }}>编辑</Button>
                </div>
              )}
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  );
}
