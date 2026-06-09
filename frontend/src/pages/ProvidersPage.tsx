import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Alert, Card, Typography, Table, Button, Modal, Form, Input, Select, Switch, Tag, Space, message, Popconfirm, InputNumber, Empty } from 'antd';
import { PlusOutlined, ThunderboltOutlined, EditOutlined, DeleteOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import { providerApi } from '@/services/projectApi';

const { Title, Text } = Typography;

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

const DEFAULT_MODELS: Record<string, string> = {
  openai: 'gpt-4o',
  deepseek: 'deepseek-chat',
  claude: 'claude-sonnet-4-20250514',
  gemini: 'gemini-2.5-flash',
};

export default function ProvidersPage() {
  const navigate = useNavigate();
  const [providers, setProviders] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [testing, setTesting] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [form] = Form.useForm();

  const fetchProviders = async () => {
    setLoading(true);
    try { setProviders(await providerApi.list()); } catch { message.error('加载失败'); }
    setLoading(false);
  };

  useEffect(() => { fetchProviders(); }, []);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({
      provider_type: 'openai',
      model: DEFAULT_MODELS.openai,
      base_url: DEFAULT_BASE_URLS.openai,
      is_active: false,
      sort_order: providers.length,
    });
    setModalOpen(true);
  };
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

  const updateProvider = async (id: string, patch: any, successText = '已更新') => {
    setSavingId(id);
    try {
      await providerApi.update(id, patch);
      message.success(successText);
      await fetchProviders();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '更新失败');
    }
    setSavingId(null);
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

  const activeProviders = providers.filter((p) => p.is_active);
  const defaultProvider = activeProviders[0];

  return (
    <div style={{ maxWidth: 1120, margin: '0 auto', padding: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16, marginBottom: 16 }}>
        <Space align="center">
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/dashboard')}>返回项目列表</Button>
          <div>
            <Title level={3} style={{ margin: 0 }}>模型管理</Title>
            <Text type="secondary">启用的供应商按排序从小到大选择，排序最小的是默认写作模型。</Text>
          </div>
        </Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>添加供应商</Button>
      </div>

      <Alert
        type={defaultProvider ? 'success' : 'warning'}
        showIcon
        style={{ marginBottom: 16 }}
        message={defaultProvider ? `当前默认：${defaultProvider.name || '未命名'} · ${defaultProvider.model}` : '当前没有启用的模型'}
        description={defaultProvider ? '生成任务会优先使用启用列表中排序最小的供应商；如果要切换默认模型，调整排序或关闭其他供应商。' : '请至少启用一个供应商，否则 AI 生成任务会报“没有可用的 LLM 配置”。'}
      />

      <Card>
        <Table
          dataSource={providers}
          rowKey="id"
          loading={loading}
          pagination={false}
          locale={{ emptyText: <Empty description="还没有模型供应商" /> }}
          columns={[
            { title: '名称', dataIndex: 'name', width: 180, render: (t: string, record: any) => (
              <Space direction="vertical" size={0}>
                <Text strong>{t || '未命名'}</Text>
                {record.id === defaultProvider?.id && <Tag color="blue">默认</Tag>}
              </Space>
            ) },
            { title: '类型', dataIndex: 'provider_type', width: 100, render: (t: string) => <Tag>{PROVIDER_TYPES[t] || t}</Tag> },
            { title: '模型', dataIndex: 'model', ellipsis: true },
            { title: 'API地址', dataIndex: 'base_url', ellipsis: true, render: (t: string, record: any) => t || (record.provider_type === 'claude' ? 'Claude 官方地址' : '默认') },
            {
              title: '排序',
              dataIndex: 'sort_order',
              width: 100,
              render: (v: number, record: any) => (
                <InputNumber
                  size="small"
                  min={0}
                  value={v ?? 0}
                  style={{ width: 72 }}
                  disabled={savingId === record.id}
                  onBlur={(e) => updateProvider(record.id, { sort_order: Number(e.target.value || 0) }, '排序已更新')}
                  onPressEnter={(e: any) => e.currentTarget.blur()}
                />
              ),
            },
            {
              title: '启用',
              dataIndex: 'is_active',
              width: 96,
              render: (v: boolean, record: any) => (
                <Switch
                  checked={v}
                  loading={savingId === record.id}
                  onChange={(checked) => updateProvider(record.id, { is_active: checked }, checked ? '已启用' : '已停用')}
                />
              ),
            },
            {
              title: '操作', width: 220,
              render: (_: any, record: any) => (
                <Space>
                  <Button size="small" icon={<ThunderboltOutlined />} loading={testing === record.id}
                    onClick={() => handleTest(record.id)}>测试</Button>
                  <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>编辑</Button>
                  <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)}>
                    <Button size="small" danger icon={<DeleteOutlined />} aria-label="删除供应商" />
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Modal title={editing ? '编辑供应商' : '添加供应商'} open={modalOpen}
        onOk={handleSave} onCancel={() => setModalOpen(false)} width={520} destroyOnClose>
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input placeholder="如：我的 DeepSeek" />
          </Form.Item>
          <Form.Item name="provider_type" label="类型" rules={[{ required: true }]}>
            <Select options={Object.entries(PROVIDER_TYPES).map(([k, v]) => ({ label: v, value: k }))}
              onChange={(v) => {
                form.setFieldValue('base_url', DEFAULT_BASE_URLS[v] || '');
                form.setFieldValue('model', DEFAULT_MODELS[v] || '');
              }} />
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
          <Form.Item name="sort_order" label="排序">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
