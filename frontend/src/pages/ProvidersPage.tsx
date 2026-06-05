import { useEffect, useState } from 'react';
import { Card, Typography, Table, Button, Modal, Form, Input, Select, Switch, Tag, Space, message, Popconfirm } from 'antd';
import { PlusOutlined, ThunderboltOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { providerApi } from '@/services/projectApi';

const { Title } = Typography;

const PROVIDER_TYPES: Record<string, string> = {
  openai: 'OpenAI',
  claude: 'Claude',
  deepseek: 'DeepSeek',
  gemini: 'Gemini',
  custom: '自定义',
};

const DEFAULT_BASE_URLS: Record<string, string> = {
  openai: 'https://api.openai.com/v1',
  deepseek: 'https://api.deepseek.com/v1',
  gemini: 'https://generativelanguage.googleapis.com/v1beta',
};

export default function ProvidersPage() {
  const [providers, setProviders] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [testing, setTesting] = useState<string | null>(null);
  const [form] = Form.useForm();

  const fetchProviders = async () => {
    setLoading(true);
    try { setProviders(await providerApi.list()); } catch { message.error('加载失败'); }
    setLoading(false);
  };

  useEffect(() => { fetchProviders(); }, []);

  const openCreate = () => { setEditing(null); form.resetFields(); form.setFieldsValue({ provider_type: 'openai', is_active: false }); setModalOpen(true); };
  const openEdit = (p: any) => { setEditing(p); form.setFieldsValue(p); setModalOpen(true); };

  const handleSave = async () => {
    const values = await form.validateFields();
    try {
      if (editing) {
        await providerApi.update(editing.id, values);
        message.success('已更新');
      } else {
        await providerApi.create(values);
        message.success('已添加');
      }
      setModalOpen(false);
      fetchProviders();
    } catch (e: any) { message.error('保存失败'); }
  };

  const handleDelete = async (id: string) => {
    try { await providerApi.remove(id); message.success('已删除'); fetchProviders(); } catch { message.error('删除失败'); }
  };

  const handleTest = async (id: string) => {
    setTesting(id);
    try {
      const result = await providerApi.test(id);
      if (result.success) {
        message.success(`连接成功！模型: ${result.model}`);
      } else {
        message.error(`连接失败: ${result.error}`);
      }
    } catch { message.error('测试失败'); }
    setTesting(null);
  };

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto', padding: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={3} style={{ margin: 0 }}>模型管理</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>添加供应商</Button>
      </div>

      <Table
        dataSource={providers}
        rowKey="id"
        loading={loading}
        pagination={false}
        columns={[
          { title: '名称', dataIndex: 'name', render: (t: string) => t || '未命名' },
          { title: '类型', dataIndex: 'provider_type', width: 80, render: (t: string) => <Tag>{PROVIDER_TYPES[t] || t}</Tag> },
          { title: '模型', dataIndex: 'model', ellipsis: true },
          { title: 'API地址', dataIndex: 'base_url', ellipsis: true, render: (t: string) => t || '默认' },
          {
            title: '状态', dataIndex: 'is_active', width: 80,
            render: (v: boolean) => v ? <Tag color="green">启用</Tag> : <Tag color="default">停用</Tag>,
          },
          {
            title: '操作', width: 200,
            render: (_: any, record: any) => (
              <Space>
                <Button size="small" icon={<ThunderboltOutlined />} loading={testing === record.id}
                  onClick={() => handleTest(record.id)}>测试</Button>
                <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>编辑</Button>
                <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)}>
                  <Button size="small" danger icon={<DeleteOutlined />} />
                </Popconfirm>
              </Space>
            ),
          },
        ]}
      />

      <Modal title={editing ? '编辑供应商' : '添加供应商'} open={modalOpen}
        onOk={handleSave} onCancel={() => setModalOpen(false)} width={520} destroyOnClose>
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input placeholder="如：我的 DeepSeek" />
          </Form.Item>
          <Form.Item name="provider_type" label="类型" rules={[{ required: true }]}>
            <Select options={Object.entries(PROVIDER_TYPES).map(([k, v]) => ({ label: v, value: k }))}
              onChange={(v) => { form.setFieldValue('base_url', DEFAULT_BASE_URLS[v] || ''); }} />
          </Form.Item>
          <Form.Item name="model" label="模型名" rules={[{ required: true }]}>
            <Input placeholder="如：gpt-4o / deepseek-chat / claude-sonnet-4-20250514" />
          </Form.Item>
          <Form.Item name="api_key" label="API Key" rules={[{ required: true }]}>
            <Input.Password placeholder="sk-xxx" />
          </Form.Item>
          <Form.Item name="base_url" label="API 地址">
            <Input placeholder="默认使用官方地址" />
          </Form.Item>
          <Form.Item name="is_active" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
