import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Card, Typography, Table, Tag, Spin } from 'antd';
import { relationshipApi } from '@/services/projectApi';

const { Title } = Typography;

export default function RelationshipPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!projectId) return;
    relationshipApi.list(projectId).then(setEvents).finally(() => setLoading(false));
  }, [projectId]);

  if (loading) return <div style={{ textAlign: 'center', padding: 48 }}><Spin /></div>;

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto', padding: 24 }}>
      <Title level={3}>关系追踪</Title>
      {events.length === 0 ? (
        <Card style={{ textAlign: 'center', padding: 48 }}>
          <p>还没有关系事件。写作时 AI 会自动检测角色关系变化。</p>
        </Card>
      ) : (
        <Table
          dataSource={events}
          rowKey="id"
          pagination={false}
          columns={[
            { title: '角色A', dataIndex: 'character_a_id' },
            { title: '角色B', dataIndex: 'character_b_id' },
            { title: '变化前', dataIndex: 'old_relation' },
            { title: '变化后', dataIndex: 'new_relation', render: (t: string) => <Tag color="blue">{t}</Tag> },
            { title: '触发事件', dataIndex: 'trigger_event', ellipsis: true },
            { title: '章节', dataIndex: 'chapter_number' },
            { title: '强度', dataIndex: 'intensity', render: (v: number) => `${v}/10` },
          ]}
        />
      )}
    </div>
  );
}
