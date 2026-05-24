import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  Button,
  Modal,
  InputNumber,
  Checkbox,
  Space,
  Input,
  message,
  Progress,
  Space as AntSpace,
} from "antd";
import {
  RobotOutlined,
  FormatPainterOutlined,
  EditOutlined,
  SaveOutlined,
} from "@ant-design/icons";
import {
  startChapterGeneration,
  startPolish,
  startModify,
} from "@/services/generationApi";
import { useGenerationStore } from "@/stores/useGenerationStore";

const { TextArea } = Input;

const POLISH_TYPE_OPTIONS = [
  { label: "语言流畅度", value: "fluency" },
  { label: "文笔提升", value: "prose" },
  { label: "错别字修正", value: "typo" },
  { label: "对话优化", value: "dialogue" },
];

interface QuickActionsProps {
  chapterId?: string;
  selectedText?: string;
  onSave?: () => void;
}

export default function QuickActions({
  chapterId,
  selectedText,
  onSave,
}: QuickActionsProps) {
  const { projectId } = useParams<{ projectId: string }>();
  const setTask = useGenerationStore((s) => s.setTask);
  const isGenerating = useGenerationStore((s) => s.isGenerating);
  const progress = useGenerationStore((s) => s.progress);

  // AI续写 modal state
  const [continueOpen, setContinueOpen] = useState(false);
  const [wordCount, setWordCount] = useState(2000);
  const [basedOnSelection, setBasedOnSelection] = useState(false);
  const [continueLoading, setContinueLoading] = useState(false);

  // AI润色 modal state
  const [polishOpen, setPolishOpen] = useState(false);
  const [polishTypes, setPolishTypes] = useState<string[]>([]);
  const [polishLoading, setPolishLoading] = useState(false);

  // AI修改 modal state
  const [modifyOpen, setModifyOpen] = useState(false);
  const [modifyInstruction, setModifyInstruction] = useState("");
  const [modifyLoading, setModifyLoading] = useState(false);

  const handleContinue = async () => {
    if (!projectId) return;
    setContinueLoading(true);
    try {
      const res = await startChapterGeneration(projectId, {
        chapter_id: chapterId,
        target_word_count: wordCount,
        based_on_selection: basedOnSelection,
        selected_text: basedOnSelection ? selectedText : undefined,
      });
      if (res.data) {
        setTask(res.data);
      }
      message.success("续写任务已启动");
      setContinueOpen(false);
    } catch {
      message.error("续写任务启动失败");
    } finally {
      setContinueLoading(false);
    }
  };

  const handlePolish = async () => {
    if (!projectId) return;
    if (polishTypes.length === 0) {
      message.warning("请至少选择一种润色类型");
      return;
    }
    setPolishLoading(true);
    try {
      const res = await startPolish(projectId, {
        chapter_id: chapterId,
        polish_types: polishTypes,
        target_content: selectedText,
      });
      if (res.data) {
        setTask(res.data);
      }
      message.success("润色任务已启动");
      setPolishOpen(false);
    } catch {
      message.error("润色任务启动失败");
    } finally {
      setPolishLoading(false);
    }
  };

  const handleModify = async () => {
    if (!projectId) return;
    if (!modifyInstruction.trim()) {
      message.warning("请填写修改指令");
      return;
    }
    setModifyLoading(true);
    try {
      const res = await startModify(projectId, {
        chapter_id: chapterId,
        instruction: modifyInstruction.trim(),
        target_content: selectedText,
      });
      if (res.data) {
        setTask(res.data);
      }
      message.success("修改任务已启动");
      setModifyOpen(false);
      setModifyInstruction("");
    } catch {
      message.error("修改任务启动失败");
    } finally {
      setModifyLoading(false);
    }
  };

  return (
    <div style={{ padding: "8px 16px", borderTop: "1px solid #f0f0f0", background: "#fff" }}>
      {isGenerating && (
        <div style={{ marginBottom: 8 }}>
          <Progress percent={progress} size="small" status="active" />
        </div>
      )}
      <Space>
        <Button
          type="primary"
          icon={<RobotOutlined />}
          onClick={() => setContinueOpen(true)}
          disabled={isGenerating}
        >
          AI续写
        </Button>
        <Button
          icon={<FormatPainterOutlined />}
          onClick={() => setPolishOpen(true)}
          disabled={isGenerating}
        >
          AI润色
        </Button>
        <Button
          icon={<EditOutlined />}
          onClick={() => setModifyOpen(true)}
          disabled={isGenerating}
        >
          AI修改
        </Button>
        <Button icon={<SaveOutlined />} onClick={onSave}>
          保存
        </Button>
      </Space>

      {/* AI续写 Modal */}
      <Modal
        title="AI续写配置"
        open={continueOpen}
        onOk={handleContinue}
        onCancel={() => setContinueOpen(false)}
        confirmLoading={continueLoading}
        destroyOnClose
      >
        <AntSpace direction="vertical" style={{ width: "100%" }} size="middle">
          <div>
            <label style={{ display: "block", marginBottom: 8 }}>续写字数</label>
            <InputNumber
              min={500}
              max={5000}
              step={500}
              value={wordCount}
              onChange={(v) => setWordCount(v ?? 2000)}
              style={{ width: "100%" }}
              addonAfter="字"
            />
          </div>
          {selectedText && (
            <Checkbox
              checked={basedOnSelection}
              onChange={(e) => setBasedOnSelection(e.target.checked)}
            >
              基于当前选中文本续写
            </Checkbox>
          )}
        </AntSpace>
      </Modal>

      {/* AI润色 Modal */}
      <Modal
        title="AI润色配置"
        open={polishOpen}
        onOk={handlePolish}
        onCancel={() => {
          setPolishOpen(false);
          setPolishTypes([]);
        }}
        confirmLoading={polishLoading}
        destroyOnClose
      >
        <div>
          <label style={{ display: "block", marginBottom: 8 }}>润色类型（可多选）</label>
          <Checkbox.Group
            options={POLISH_TYPE_OPTIONS}
            value={polishTypes}
            onChange={(v) => setPolishTypes(v as string[])}
          />
        </div>
      </Modal>

      {/* AI修改 Modal */}
      <Modal
        title="AI修改"
        open={modifyOpen}
        onOk={handleModify}
        onCancel={() => {
          setModifyOpen(false);
          setModifyInstruction("");
        }}
        confirmLoading={modifyLoading}
        destroyOnClose
      >
        <div>
          <label style={{ display: "block", marginBottom: 8 }}>修改指令</label>
          <TextArea
            value={modifyInstruction}
            onChange={(e) => setModifyInstruction(e.target.value)}
            placeholder="请描述你想要的修改..."
            rows={4}
            required
          />
        </div>
      </Modal>
    </div>
  );
}
