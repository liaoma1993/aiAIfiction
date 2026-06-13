import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Button, Drawer, Empty, Input, Segmented, Space, Spin, Tabs, Tag, Typography } from 'antd';
import {
  ApartmentOutlined,
  BranchesOutlined,
  EnvironmentOutlined,
  LeftOutlined,
  NodeIndexOutlined,
  SearchOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { storyApi } from '@/services/projectApi';
import LandscapePage from './LandscapePage';
import './StoryGraphPage.css';

const { Title, Text, Paragraph } = Typography;

const TYPE_META: Record<string, { color: string; icon: any }> = {
  全部: { color: 'default', icon: NodeIndexOutlined },
  角色: { color: 'blue', icon: TeamOutlined },
  组织: { color: 'purple', icon: ApartmentOutlined },
  伏笔: { color: 'orange', icon: BranchesOutlined },
};

function edgeLabel(edge: any) {
  return `${edge.source_label || edge.source} -> ${edge.target_label || edge.target}`;
}

export default function StoryGraphPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [typeFilter, setTypeFilter] = useState('全部');
  const [query, setQuery] = useState('');
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [selectedEdge, setSelectedEdge] = useState<any>(null);

  useEffect(() => {
    if (!projectId) return;
    storyApi.graph(projectId).then(setData).finally(() => setLoading(false));
  }, [projectId]);

  const nodes = data?.nodes || [];
  const edges = data?.edges || [];
  const filteredNodes = useMemo(() => {
    const q = query.trim().toLowerCase();
    return nodes.filter((node: any) => {
      const typeOk = typeFilter === '全部' || node.type === typeFilter;
      const text = `${node.label || ''} ${node.subtype || ''} ${node.summary || ''}`.toLowerCase();
      return typeOk && (!q || text.includes(q));
    });
  }, [nodes, query, typeFilter]);

  const relatedEdges = useMemo(() => {
    if (!selectedNode) return [];
    return edges.filter((edge: any) => edge.source === selectedNode.id || edge.target === selectedNode.id || edge.source_label === selectedNode.label || edge.target_label === selectedNode.label);
  }, [edges, selectedNode]);

  const counts = useMemo(() => {
    const result: Record<string, number> = { 全部: nodes.length, 角色: 0, 组织: 0, 伏笔: 0 };
    nodes.forEach((node: any) => { result[node.type] = (result[node.type] || 0) + 1; });
    return result;
  }, [nodes]);

  if (!projectId) return null;
  if (loading) return <div className="story-graph-loading"><Spin size="large" /></div>;

  return (
    <div className="story-graph-page">
      <header className="story-graph-header">
        <Link to={`/projects/${projectId}`}><Button icon={<LeftOutlined />}>返回工作台</Button></Link>
        <div className="story-graph-titleblock">
          <Title level={3}>叙事图谱</Title>
          <Text type="secondary">统一查看关系网络、世界设定、卷章地图和事件线。</Text>
        </div>
      </header>

      <Tabs
        className="story-graph-tabs"
        defaultActiveKey="graph"
        items={[
          {
            key: 'graph',
            label: <span><NodeIndexOutlined /> 关系图谱</span>,
            children: (
              <>

      <section className="story-graph-stats">
        {(['全部', '角色', '组织', '伏笔'] as const).map((name) => {
          const Icon = TYPE_META[name].icon;
          return (
            <button key={name} className={typeFilter === name ? 'active' : ''} onClick={() => setTypeFilter(name)}>
              <Icon />
              <span>{name}</span>
              <strong>{counts[name] || 0}</strong>
            </button>
          );
        })}
      </section>

      <section className="story-graph-toolbar">
        <Segmented
          value={typeFilter}
          onChange={(value) => setTypeFilter(String(value))}
          options={['全部', '角色', '组织', '伏笔'].map((item) => ({ label: item, value: item }))}
        />
        <Input
          allowClear
          prefix={<SearchOutlined />}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="搜索节点、类型或摘要"
        />
      </section>

      <section className="story-graph-main">
        <div className="story-graph-node-panel">
          <div className="story-graph-section-head">
            <div>
              <Title level={4}>节点地图</Title>
              <Text type="secondary">点击节点查看相关关系。</Text>
            </div>
            <Tag>{filteredNodes.length} 个</Tag>
          </div>
          {!filteredNodes.length ? <Empty description="暂无节点" /> : (
            <div className="story-node-grid">
              {filteredNodes.map((node: any) => {
                const meta = TYPE_META[node.type] || TYPE_META.全部;
                const Icon = meta.icon;
                return (
                  <button key={node.id} className={`story-node-card ${selectedNode?.id === node.id ? 'selected' : ''}`} onClick={() => setSelectedNode(node)}>
                    <span className="story-node-icon"><Icon /></span>
                    <span className="story-node-body">
                      <span className="story-node-title">{node.label}</span>
                      <span className="story-node-meta">
                        <Tag color={meta.color}>{node.type}</Tag>
                        {node.subtype && <Tag>{node.subtype}</Tag>}
                      </span>
                      {node.summary && <span className="story-node-summary">{node.summary}</span>}
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        <aside className="story-graph-side">
          <div className="story-graph-section-head">
            <div>
              <Title level={4}>关系概览</Title>
              <Text type="secondary">按关系类型统计。</Text>
            </div>
          </div>
          <div className="story-edge-types">
            {Object.entries(edges.reduce((acc: Record<string, number>, edge: any) => {
              acc[edge.type || '关系'] = (acc[edge.type || '关系'] || 0) + 1;
              return acc;
            }, {})).map(([name, count]) => (
              <div key={name}>
                <Text>{name}</Text>
                <strong>{count as number}</strong>
              </div>
            ))}
            {!edges.length && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无关系" />}
          </div>
        </aside>
      </section>

      <section className="story-graph-table">
        <div className="story-graph-section-head">
          <div>
            <Title level={4}>关系边与因果连接</Title>
            <Text type="secondary">长关系说明默认收起，点详情查看完整内容。</Text>
          </div>
        </div>
        {!edges.length ? (
          <Empty description="暂无关系边。可以先补角色关系、组织关系或让章节写作自动沉淀关系事件。" />
        ) : (
          <div className="story-edge-list">
            {edges.slice(0, 120).map((edge: any, index: number) => (
              <article key={`${edge.source}-${edge.target}-${edge.type}-${edge.chapter_number || ''}-${edge.relation}-${index}`} className="story-edge-card">
                <div className="story-edge-main">
                  <Text strong className="story-edge-connection">{edgeLabel(edge)}</Text>
                  <div className="story-edge-tags">
                    <Tag>{edge.type || '关系'}</Tag>
                    {edge.chapter_number && <Tag>第{edge.chapter_number}章</Tag>}
                  </div>
                </div>
                <Text className="story-edge-relation">{edge.relation || edge.description || '未填写关系说明'}</Text>
                <Button size="small" type="link" onClick={() => setSelectedEdge(edge)}>详情</Button>
              </article>
            ))}
          </div>
        )}
      </section>

      <Drawer title="节点详情" open={!!selectedNode} onClose={() => setSelectedNode(null)} width={420}>
        {selectedNode && (
          <div className="story-node-detail">
            <Space wrap>
              <Tag color={(TYPE_META[selectedNode.type] || TYPE_META.全部).color}>{selectedNode.type}</Tag>
              {selectedNode.subtype && <Tag>{selectedNode.subtype}</Tag>}
            </Space>
            <Title level={4}>{selectedNode.label}</Title>
            <Paragraph>{selectedNode.summary || '暂无摘要'}</Paragraph>
            <Title level={5}>相关关系</Title>
            {!relatedEdges.length ? <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无相关关系" /> : relatedEdges.map((edge: any) => (
              <div key={`${edge.source}-${edge.target}-${edge.type}-${edge.relation}`} className="story-related-edge">
                <Text strong>{edgeLabel(edge)}</Text>
                <div>
                  <Tag>{edge.type || '关系'}</Tag>
                  {edge.chapter_number && <Tag>第{edge.chapter_number}章</Tag>}
                </div>
                <Paragraph>{edge.relation || edge.description || '未填写说明'}</Paragraph>
              </div>
            ))}
          </div>
        )}
      </Drawer>

      <Drawer title="关系详情" open={!!selectedEdge} onClose={() => setSelectedEdge(null)} width={460}>
        {selectedEdge && (
          <div className="story-edge-detail">
            <Space wrap>
              <Tag>{selectedEdge.type || '关系'}</Tag>
              {selectedEdge.chapter_number && <Tag>第{selectedEdge.chapter_number}章</Tag>}
            </Space>
            <Title level={4}>{edgeLabel(selectedEdge)}</Title>
            <div className="story-detail-block">
              <Text strong>关系</Text>
              <Paragraph>{selectedEdge.relation || '未填写'}</Paragraph>
            </div>
            <div className="story-detail-block">
              <Text strong>说明</Text>
              <Paragraph>{selectedEdge.description || '未填写'}</Paragraph>
            </div>
            {Array.isArray(selectedEdge.changes) && selectedEdge.changes.length > 0 && (
              <div className="story-detail-block">
                <Text strong>变化记录</Text>
                {selectedEdge.changes.map((item: any, idx: number) => (
                  <Paragraph key={idx}>{typeof item === 'string' ? item : JSON.stringify(item)}</Paragraph>
                ))}
              </div>
            )}
          </div>
        )}
      </Drawer>
              </>
            ),
          },
          {
            key: 'landscape',
            label: <span><EnvironmentOutlined /> 小说景观</span>,
            children: <LandscapePage embedded />,
          },
        ]}
      />
    </div>
  );
}
