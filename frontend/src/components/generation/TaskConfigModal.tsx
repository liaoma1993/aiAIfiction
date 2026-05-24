import { useState } from "react";
import {
  Modal,
  Form,
  Select,
  InputNumber,
  Progress,
  Typography,
  Space,
  Alert,
} from "antd";
import {
  RobotOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";

const { Text } = Typography;

export type RangeType = "all" | "from_chapter";

export interface TaskConfig {
  range: RangeType;
  startChapter?: number;
  model?: string;
}

interface TaskConfigModalProps {
  open: boolean;
  loading: boolean;
  progress?: number;
  progressMessage?: string;
  totalChapters?: number;
  onCancel: () => void;
  onSubmit: (config: TaskConfig) => void;
}

const MODEL_OPTIONS = [
  { value: "claude-opus-4", label: "Claude Opus 4 (文学性最佳)" },
  { value: "gpt-4o", label: "GPT-4o (综合优秀)" },
  { value: "deepseek-v3", label: "DeepSeek V3 (性价比高)" },
  { value: "gemini-2.5-pro", label: "Gemini 2.5 Pro (长文本)" },
];

export default function TaskConfigModal({
  open,
  loading,
  progress,
  progressMessage,
  totalChapters = 0,
  onCancel,
  onSubmit,
}: TaskConfigModalProps) {
  const [range, setRange] = useState<RangeType>("all");
  const [startChapter, setStartChapter] = useState<number | undefined>(undefined);
  const [model, setModel] = useState<string>("deepseek-v3");

  const handleSubmit = () => {
    onSubmit({
      range,
      startChapter: range === "from_chapter" ? startChapter : undefined,
      model,
    });
  };

  const handleCancel = () => {
    setRange("all");
    setStartChapter(undefined);
    setModel("deepseek-v3");
    onCancel();
  };

  const isRunning = progress !== undefined;

  return (
    <Modal
      title={
        <Space>
          <RobotOutlined />
          <span>AI 生成大纲</span>
        </Space>
      }
      open={open}
      onCancel={handleCancel}
      onOk={handleSubmit}
      okText={isRunning ? "生成中..." : "开始生成"}
      cancelText="取消"
      okButtonProps={{
        loading: loading,
        disabled: isRunning,
        icon: <ThunderboltOutlined />,
      }}
      maskClosable={!isRunning}
      closable={!isRunning}
      destroyOnClose
      width={520}
    >
      {isRunning ? (
        <div style={{ padding: "16px 0" }}>
          <Alert
            type="info"
            message="正在生成大纲"
            description={progressMessage ?? "AI 正在分析项目设定，生成故事大纲..."}
            showIcon
            style={{ marginBottom: 16 }}
          />
          <Progress
            percent={Math.min(progress ?? 0, 100)}
            status="active"
            strokeColor={{
              from: "#108ee9",
              to: "#87d068",
            }}
          />
          <Text
            type="secondary"
            style={{ display: "block", textAlign: "center", marginTop: 8 }}
          >
            {progressMessage ?? "请稍候，大纲生成中..."}
          </Text>
        </div>
      ) : (
        <Form layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item label="生成范围" required>
            <Select
              value={range}
              onChange={(value: RangeType) => setRange(value)}
              options={[
                { value: "all", label: "全部大纲" },
                { value: "from_chapter", label: "从指定章节开始" },
              ]}
            />
          </Form.Item>

          {range === "from_chapter" && (
            <Form.Item label="起始章节">
              <InputNumber
                min={1}
                max={totalChapters || 999}
                value={startChapter}
                onChange={(value) => setStartChapter(value ?? undefined)}
                placeholder={`当前共 ${totalChapters} 章`}
                style={{ width: "100%" }}
              />
            </Form.Item>
          )}

          <Form.Item label="模型选择" required>
            <Select
              value={model}
              onChange={(value: string) => setModel(value)}
              options={MODEL_OPTIONS}
            />
          </Form.Item>
        </Form>
      )}
    </Modal>
  );
}
