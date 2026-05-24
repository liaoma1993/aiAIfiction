import {
  Form,
  Input,
  Select,
  Radio,
  Tag,
  Descriptions,
  type FormInstance,
} from "antd";
import type { Genre, TargetLength, Project } from "@/types/project";
import { GENRE_LABELS } from "@/types/project";

// ── 写作风格标签 ──────────────────────────────────────────────
export const WRITING_STYLE_TAGS = [
  "轻松幽默",
  "文艺抒情",
  "黑暗沉重",
  "热血战斗",
  "悬疑推理",
  "古风典雅",
  "现代简约",
  "细腻写实",
  "浪漫唯美",
  "冷酷犀利",
];

// ── 目标篇幅选项 ─────────────────────────────────────────────
export const TARGET_LENGTH_OPTIONS: {
  label: string;
  value: TargetLength;
}[] = [
  { label: "短篇(1-3万字)", value: "short" },
  { label: "中篇(3-10万字)", value: "medium" },
  { label: "长篇(10万+字)", value: "long" },
];

// ── 生成模式选项 ─────────────────────────────────────────────
export const GENERATION_MODE_OPTIONS = [
  { label: "快速生成", value: "fast", description: "一次性生成全部内容" },
  { label: "交互模式", value: "interactive", description: "逐章确认后继续" },
];

// ── Props ────────────────────────────────────────────────────

interface ProjectSettingsFormProps {
  form: FormInstance;
  initialValues?: Partial<Project>;
  readOnly?: boolean;
}

interface ProjectSettingsDisplayProps {
  project: Project;
}

// ── 表单版（创建/编辑场景） ──────────────────────────────────

export function ProjectSettingsForm({
  form,
  readOnly = false,
}: ProjectSettingsFormProps) {
  return (
    <Form form={form} layout="vertical" disabled={readOnly}>
      <Form.Item
        name="title"
        label="项目标题"
        rules={[
          { required: true, message: "请输入项目标题" },
          { max: 100, message: "标题不能超过100字" },
        ]}
      >
        <Input placeholder="给你的故事取个名字" showCount maxLength={100} />
      </Form.Item>

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

      <Form.Item label="写作风格">
        <Form.Item
          name={["writing_style", "tags"]}
          style={{ marginBottom: 12 }}
        >
          <Select
            mode="tags"
            placeholder="选择或输入风格标签"
            tokenSeparators={[","]}
          >
            {WRITING_STYLE_TAGS.map((tag) => (
              <Select.Option key={tag} value={tag}>
                {tag}
              </Select.Option>
            ))}
          </Select>
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
          placeholder="简单描述你的故事，包括主要情节、核心冲突、故事背景等。AI将以此为基础展开创作。"
          showCount
          maxLength={1000}
        />
      </Form.Item>

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
    </Form>
  );
}

// ── 只读展示版 ──────────────────────────────────────────────

export function ProjectSettingsDisplay({ project }: ProjectSettingsDisplayProps) {
  const writingStyle = project.writing_style as {
    tags?: string[];
    description?: string;
  };

  return (
    <Descriptions column={1} bordered size="small">
      <Descriptions.Item label="标题">{project.title}</Descriptions.Item>
      <Descriptions.Item label="题材">
        {GENRE_LABELS[project.genre]}
      </Descriptions.Item>
      <Descriptions.Item label="目标篇幅">
        {TARGET_LENGTH_OPTIONS.find(
          (o) => o.value === project.target_length,
        )?.label ?? project.target_length}
      </Descriptions.Item>
      <Descriptions.Item label="风格标签">
        {writingStyle?.tags?.length ? (
          writingStyle.tags.map((t) => (
            <Tag key={t} color="blue">
              {t}
            </Tag>
          ))
        ) : (
          <span style={{ color: "#999" }}>未设置</span>
        )}
      </Descriptions.Item>
      <Descriptions.Item label="风格描述">
        {writingStyle?.description ? (
          <div style={{ whiteSpace: "pre-wrap" }}>
            {writingStyle.description}
          </div>
        ) : (
          <span style={{ color: "#999" }}>未设置</span>
        )}
      </Descriptions.Item>
      <Descriptions.Item label="故事梗概">
        {project.story_brief ? (
          <div style={{ whiteSpace: "pre-wrap" }}>{project.story_brief}</div>
        ) : (
          <span style={{ color: "#999" }}>未设置</span>
        )}
      </Descriptions.Item>
      <Descriptions.Item label="生成模式">
        {project.generation_mode === "fast" ? "快速生成" : "交互模式"}
      </Descriptions.Item>
    </Descriptions>
  );
}

export default ProjectSettingsForm;
