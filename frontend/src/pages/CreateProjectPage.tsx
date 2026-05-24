import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Card,
  Steps,
  Form,
  Input,
  Select,
  Radio,
  Button,
  Typography,
  Space,
  message,
} from "antd";
import type { Genre } from "@/types/project";
import { GENRE_LABELS } from "@/types/project";
import { createProject } from "@/services/projectApi";
import {
  WRITING_STYLE_TAGS,
  TARGET_LENGTH_OPTIONS,
  GENERATION_MODE_OPTIONS,
} from "@/components/project/ProjectSettings";

const { Title, Text } = Typography;

// ── 步骤定义 ────────────────────────────────────────────────
const STEPS = [
  { title: "项目信息" },
  { title: "角色设定" },
  { title: "世界设定" },
  { title: "大纲生成" },
];

// ── 表单数据类型 ────────────────────────────────────────────
interface FormValues {
  title: string;
  genre: Genre;
  target_length: string;
  writing_style: {
    tags: string[];
    description: string;
  };
  story_brief: string;
  generation_mode: string;
}

// ── 初始值 ──────────────────────────────────────────────────
const INITIAL_VALUES: FormValues = {
  title: "",
  genre: undefined as unknown as Genre,
  target_length: undefined as unknown as string,
  writing_style: {
    tags: [],
    description: "",
  },
  story_brief: "",
  generation_mode: undefined as unknown as string,
};

// ── 组件 ────────────────────────────────────────────────────

function CreateProjectPage() {
  const navigate = useNavigate();
  const [form] = Form.useForm<FormValues>();
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (values: FormValues) => {
    setSubmitting(true);
    try {
      const response = await createProject({
        title: values.title,
        genre: values.genre,
        target_length: values.target_length,
        writing_style: values.writing_style as Record<string, unknown>,
        story_brief: values.story_brief || undefined,
        generation_mode: values.generation_mode,
      });

      const projectId = response.data.id;
      message.success("项目创建成功");
      navigate(`/projects/${projectId}?step=characters`);
    } catch {
      message.error("创建项目失败，请重试");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: 780, margin: "0 auto", padding: "24px 16px" }}>
      {/* ── 页面标题 ── */}
      <div style={{ marginBottom: 32 }}>
        <Title level={2} style={{ marginBottom: 8 }}>
          创建新项目
        </Title>
        <Text type="secondary">
          填写项目基本信息，AI 将根据你的设定创作专属故事。后续步骤将引导你设定角色和世界观。
        </Text>
      </div>

      {/* ── 步骤条 ── */}
      <Steps
        current={0}
        items={STEPS}
        size="small"
        style={{ marginBottom: 32 }}
      />

      {/* ── 表单卡片 ── */}
      <Card>
        <Form
          form={form}
          layout="vertical"
          initialValues={INITIAL_VALUES}
          onFinish={handleSubmit}
          scrollToFirstError
        >
          {/* 标题 */}
          <Form.Item
            name="title"
            label="项目标题"
            rules={[
              { required: true, message: "请输入项目标题" },
              { max: 100, message: "标题不能超过100字" },
            ]}
          >
            <Input
              placeholder="给你的故事取个名字"
              showCount
              maxLength={100}
            />
          </Form.Item>

          {/* 题材 */}
          <Form.Item
            name="genre"
            label="题材"
            rules={[{ required: true, message: "请选择题材" }]}
          >
            <Select placeholder="选择故事题材">
              {(Object.entries(GENRE_LABELS) as [Genre, string][]).map(
                ([value, label]) => (
                  <Select.Option key={value} value={value}>
                    {label}
                  </Select.Option>
                ),
              )}
            </Select>
          </Form.Item>

          {/* 目标篇幅 */}
          <Form.Item
            name="target_length"
            label="目标篇幅"
            rules={[{ required: true, message: "请选择目标篇幅" }]}
          >
            <Radio.Group>
              {TARGET_LENGTH_OPTIONS.map((opt) => (
                <Radio.Button key={opt.value} value={opt.value}>
                  {opt.label}
                </Radio.Button>
              ))}
            </Radio.Group>
          </Form.Item>

          {/* 写作风格 */}
          <Form.Item label="写作风格">
            <Form.Item
              name={["writing_style", "tags"]}
              style={{ marginBottom: 12 }}
            >
              <Select
                mode="tags"
                placeholder="选择或输入风格标签（支持自定义）"
                tokenSeparators={[","]}
                options={WRITING_STYLE_TAGS.map((tag) => ({
                  label: tag,
                  value: tag,
                }))}
              />
            </Form.Item>

            <Form.Item
              name={["writing_style", "description"]}
              style={{ marginBottom: 0 }}
            >
              <Input.TextArea
                rows={4}
                placeholder="描述更详细的写作风格偏好，如：多用短句、注重心理描写、避免冗长对话等"
                showCount
                maxLength={500}
              />
            </Form.Item>
          </Form.Item>

          {/* 故事梗概 */}
          <Form.Item
            name="story_brief"
            label="故事梗概"
            rules={[
              {
                max: 1000,
                message: "故事梗概不能超过1000字",
              },
            ]}
          >
            <Input.TextArea
              rows={6}
              placeholder="简单描述你的故事，包括主要情节、核心冲突、故事背景等。AI 将以此为基础展开创作。"
              showCount
              maxLength={1000}
            />
          </Form.Item>

          {/* 生成模式 */}
          <Form.Item
            name="generation_mode"
            label="生成模式"
            rules={[{ required: true, message: "请选择生成模式" }]}
          >
            <Radio.Group>
              {GENERATION_MODE_OPTIONS.map((opt) => (
                <Radio.Button key={opt.value} value={opt.value}>
                  {opt.label}
                </Radio.Button>
              ))}
            </Radio.Group>
          </Form.Item>

          {/* ── 底部按钮 ── */}
          <Form.Item style={{ marginBottom: 0, marginTop: 8 }}>
            <Space>
              <Button onClick={() => navigate("/dashboard")}>取消</Button>
              <Button type="primary" htmlType="submit" loading={submitting}>
                下一步：角色设定
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}

export default CreateProjectPage;
