import { useState, useRef, useEffect } from "react";
import { useParams } from "react-router-dom";
import {
  Tabs,
  Input,
  Button,
  Tag,
  Typography,
  message,
  Card,
} from "antd";
import { SendOutlined, RobotOutlined, UserOutlined } from "@ant-design/icons";
import StageIndicator from "@/components/generation/StageIndicator";
import ProgressBar from "@/components/generation/ProgressBar";
import { useGenerationStore } from "@/stores/useGenerationStore";
import { sendChatMessage } from "@/services/generationApi";

const { Text, Paragraph } = Typography;

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

const PRESET_QUESTIONS = [
  "给我一些情节建议",
  "这个角色可以怎样发展",
  "如何让这段对话更生动",
  "帮我分析一下这段文字的文风",
];

const STAGE_LABELS: Record<string, string> = {
  world_building: "世界观扩写",
  character_deepening: "角色深化",
  outline_gen: "大纲生成",
  chapter_split: "章节拆分",
  writing: "逐章写作",
  coherence_check: "连贯性审查",
  polish: "全局润色",
};

export default function AISidebar() {
  const { projectId } = useParams<{ projectId: string }>();
  const isGenerating = useGenerationStore((s) => s.isGenerating);
  const currentTask = useGenerationStore((s) => s.currentTask);
  const currentStage = useGenerationStore((s) => s.currentStage);
  // Chat state
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll chat to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSendMessage = async (text?: string) => {
    const content = (text ?? inputValue).trim();
    if (!content || !projectId) return;

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputValue("");
    setChatLoading(true);

    try {
      const res = await sendChatMessage(projectId, {
        project_id: projectId,
        message: content,
      });
      const aiMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: res.data?.reply ?? "抱歉，我暂时无法回答这个问题。",
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, aiMsg]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: "对话请求失败，请稍后重试。",
          timestamp: new Date().toISOString(),
        },
      ]);
      message.error("对话请求失败");
    } finally {
      setChatLoading(false);
    }
  };

  const stageLabel = currentStage ? STAGE_LABELS[currentStage] ?? currentStage : null;

  // Generation progress tab content
  const progressTab = (
    <div style={{ padding: "12px 8px" }}>
      {isGenerating || currentTask ? (
        <>
          <StageIndicator direction="vertical" />
          <ProgressBar showStageLabel />
          <Card size="small" style={{ marginTop: 12 }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <span>{stageLabel ? `当前阶段: ${stageLabel}` : "等待中"}</span>
              {currentTask && (
                <Tag color="blue">
                  第 {currentTask.completed_chapters}/{currentTask.total_chapters} 章
                </Tag>
              )}
            </div>
            {currentTask?.error_message && (
              <div style={{ marginTop: 8 }}>
                <Text type="danger">{currentTask.error_message}</Text>
              </div>
            )}
          </Card>
        </>
      ) : (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            height: 200,
            color: "#999",
          }}
        >
          暂无进行中的生成任务
        </div>
      )}
    </div>
  );

  // AI Q&A tab content
  const chatTab = (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Chat messages */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "8px 12px",
          minHeight: 300,
        }}
      >
        {messages.length === 0 ? (
          <div style={{ textAlign: "center", paddingTop: 40 }}>
            <RobotOutlined
              style={{ fontSize: 32, color: "#bbb", marginBottom: 8 }}
            />
            <Paragraph type="secondary">
              有什么写作相关的问题可以问我
            </Paragraph>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              style={{
                display: "flex",
                flexDirection: msg.role === "user" ? "row-reverse" : "row",
                marginBottom: 12,
                gap: 8,
              }}
            >
              <div
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: "50%",
                  background: msg.role === "user" ? "#1677ff" : "#52c41a",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#fff",
                  fontSize: 14,
                  flexShrink: 0,
                }}
              >
                {msg.role === "user" ? <UserOutlined /> : <RobotOutlined />}
              </div>
              <div
                style={{
                  maxWidth: "75%",
                  padding: "8px 12px",
                  borderRadius: 8,
                  background:
                    msg.role === "user" ? "#e6f4ff" : "#f6ffed",
                  fontSize: 13,
                  lineHeight: 1.6,
                  wordBreak: "break-word",
                }}
              >
                {msg.content}
              </div>
            </div>
          ))
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Preset questions */}
      <div style={{ padding: "4px 12px" }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          快捷提问:
        </Text>
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 4,
            marginTop: 4,
          }}
        >
          {PRESET_QUESTIONS.map((q) => (
            <Button
              key={q}
              size="small"
              type="dashed"
              onClick={() => handleSendMessage(q)}
              disabled={chatLoading}
            >
              {q}
            </Button>
          ))}
        </div>
      </div>

      {/* Input area */}
      <div
        style={{
          padding: "8px 12px",
          borderTop: "1px solid #f0f0f0",
          display: "flex",
          gap: 8,
        }}
      >
        <Input
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="输入问题..."
          onPressEnter={() => handleSendMessage()}
          disabled={chatLoading}
        />
        <Button
          type="primary"
          icon={<SendOutlined />}
          onClick={() => handleSendMessage()}
          loading={chatLoading}
          disabled={!inputValue.trim()}
        />
      </div>
    </div>
  );

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <Tabs
        defaultActiveKey="progress"
        size="small"
        tabBarStyle={{ margin: "0 8px" }}
        items={[
          {
            key: "progress",
            label: "生成进度",
            children: progressTab,
          },
          {
            key: "chat",
            label: "AI问答",
            children: chatTab,
            style: { flex: 1, display: "flex", flexDirection: "column" },
          },
        ]}
      />
    </div>
  );
}
