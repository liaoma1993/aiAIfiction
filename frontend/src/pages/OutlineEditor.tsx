import { useState, useEffect, useRef, useCallback } from "react";
import { useParams } from "react-router-dom";
import {
  Button,
  Badge,
  Input,
  Tag,
  Popconfirm,
  Typography,
  Spin,
  Empty,
  Tooltip,
  Space,
  Card,
  message,
} from "antd";
import {
  PlusOutlined,
  RobotOutlined,
  CheckOutlined,
  DeleteOutlined,
  UpOutlined,
  DownOutlined,
  HolderOutlined,
  InfoCircleOutlined,
  EditOutlined,
  CloseOutlined,
} from "@ant-design/icons";
import { useOutlineStore } from "@/stores/useOutlineStore";
import TaskConfigModal from "@/components/generation/TaskConfigModal";
import type { TaskConfig } from "@/components/generation/TaskConfigModal";
import type { OutlineNode, OutlineNodeUpdate } from "@/types/outline";

const { Text, Title, Paragraph } = Typography;
const { TextArea } = Input;

function OutlineEditor() {
  const { projectId } = useParams<{ projectId: string }>();
  const {
    outline,
    loading,
    saving,
    selectedNodeId,
    fetchOutline,
    confirmOutline,
    setSelectedNodeId,
    addNode,
    editNode,
    removeNode,
    moveNode,
    getSortedNodes,
    getSelectedNode,
  } = useOutlineStore();

  const [generating, setGenerating] = useState(false);
  const [generationProgress, setGenerationProgress] = useState<number>();
  const [progressMessage, setProgressMessage] = useState<string>();
  const [taskModalOpen, setTaskModalOpen] = useState(false);

  // 展开的节点 ID 集合
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  // 内联编辑状态
  const [editingField, setEditingField] = useState<{
    nodeId: string;
    field: "title" | "summary";
  } | null>(null);
  const [editValue, setEditValue] = useState("");
  // 拖拽索引
  const dragIndexRef = useRef<number>(-1);
  const overIndexRef = useRef<number>(-1);

  useEffect(() => {
    if (projectId) {
      fetchOutline(projectId);
    }
  }, [projectId, fetchOutline]);

  // 打开内联编辑
  const startEdit = (nodeId: string, field: "title" | "summary", value: string) => {
    setEditingField({ nodeId, field });
    setEditValue(value);
  };

  // 取消内联编辑
  const cancelEdit = () => {
    setEditingField(null);
    setEditValue("");
  };

  // 保存内联编辑
  const saveEdit = useCallback(() => {
    if (!editingField || !projectId) return;
    const data: OutlineNodeUpdate = {};
    if (editingField.field === "title") {
      data.title = editValue;
    } else {
      data.summary = editValue;
    }
    editNode(projectId, editingField.nodeId, data);
    setEditingField(null);
    setEditValue("");
  }, [editingField, editValue, projectId, editNode]);

  // 展开/收起节点
  const toggleExpand = (nodeId: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  };

  // 选中节点
  const handleSelectNode = (nodeId: string) => {
    setSelectedNodeId(selectedNodeId === nodeId ? null : nodeId);
  };

  // 新增章节
  const handleAddNode = () => {
    if (!projectId) return;
    const sortedNodes = getSortedNodes();
    const nextNumber =
      sortedNodes.length > 0
        ? sortedNodes[sortedNodes.length - 1].chapter_number + 1
        : 1;
    addNode(projectId, {
      chapter_number: nextNumber,
      summary: "新章节概要",
      title: `第${nextNumber}章`,
      sort_order: sortedNodes.length,
    });
  };

  // 删除节点
  const handleDeleteNode = (nodeId: string) => {
    if (!projectId) return;
    removeNode(projectId, nodeId);
  };

  // 移动节点（上移/下移）
  const handleMoveNode = (nodeId: string, direction: "up" | "down") => {
    if (!projectId) return;
    const sortedNodes = getSortedNodes();
    const idx = sortedNodes.findIndex((n) => n.id === nodeId);
    if (idx < 0) return;
    const targetIdx = direction === "up" ? idx - 1 : idx + 1;
    if (targetIdx < 0 || targetIdx >= sortedNodes.length) return;
    moveNode(projectId, idx, targetIdx);
  };

  // 更新节点关键事件
  const handleKeyEventsChange = (nodeId: string, events: string[]) => {
    if (!projectId) return;
    editNode(projectId, nodeId, { key_events: events });
  };

  // 更新节点情绪弧线
  const handleEmotionalArcChange = (nodeId: string, value: string) => {
    if (!projectId) return;
    editNode(projectId, nodeId, { emotional_arc: value });
  };

  // 更新节点伏笔
  const handleForeshadowingChange = (
    nodeId: string,
    items: string[],
    resolved: string[],
  ) => {
    if (!projectId) return;
    editNode(projectId, nodeId, {
      foreshadowing_items: items,
      foreshadowing_resolved: resolved,
    });
  };

  // 更新写作指南
  const handleWritingGuideChange = (nodeId: string, value: string) => {
    if (!projectId) return;
    editNode(projectId, nodeId, { writing_guide: value });
  };

  // AI 生成大纲
  const handleGenerateOutline = (_config: TaskConfig) => {
    if (!projectId) return;
    setGenerating(true);
    setGenerationProgress(0);
    setProgressMessage("正在连接 AI 服务...");
    // 模拟进度（实际应通过 WebSocket 或轮询获取进度）
    let progress = 0;
    const interval = setInterval(() => {
      progress += Math.random() * 15;
      if (progress >= 100) {
        progress = 100;
        clearInterval(interval);
        setGenerating(false);
        setGenerationProgress(undefined);
        setProgressMessage(undefined);
        setTaskModalOpen(false);
        message.success("大纲生成完成！");
        fetchOutline(projectId);
        return;
      }
      setGenerationProgress(Math.floor(progress));
      if (progress < 30) {
        setProgressMessage("正在分析项目设定...");
      } else if (progress < 60) {
        setProgressMessage("正在生成章节大纲...");
      } else if (progress < 90) {
        setProgressMessage("正在优化章节衔接...");
      } else {
        setProgressMessage("即将完成...");
      }
    }, 800);

    // TODO: 实际对接后端 API
  };

  // 确认大纲
  const handleConfirmOutline = () => {
    if (!projectId) return;
    confirmOutline(projectId);
  };

  const sortedNodes = getSortedNodes();
  const selectedNode = getSelectedNode();
  const isConfirmed = outline?.is_confirmed ?? false;

  // HTML5 拖拽处理
  const handleDragStart = (index: number) => {
    dragIndexRef.current = index;
  };

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    overIndexRef.current = index;
  };

  const handleDrop = () => {
    const dragIndex = dragIndexRef.current;
    const overIndex = overIndexRef.current;
    if (
      dragIndex >= 0 &&
      overIndex >= 0 &&
      dragIndex !== overIndex &&
      projectId
    ) {
      moveNode(projectId, dragIndex, overIndex);
    }
    dragIndexRef.current = -1;
    overIndexRef.current = -1;
  };

  const handleDragEnd = () => {
    dragIndexRef.current = -1;
    overIndexRef.current = -1;
  };

  // Tags 编辑组件
  const TagsEditor = ({
    tags,
    onChange,
    placeholder,
  }: {
    tags: string[];
    onChange: (tags: string[]) => void;
    placeholder: string;
  }) => {
    const [inputVisible, setInputVisible] = useState(false);
    const [inputValue, setInputValue] = useState("");

    const handleClose = (removedTag: string) => {
      onChange(tags.filter((tag) => tag !== removedTag));
    };

    const handleInputConfirm = () => {
      if (inputValue && !tags.includes(inputValue)) {
        onChange([...tags, inputValue]);
      }
      setInputVisible(false);
      setInputValue("");
    };

    return (
      <div>
        {tags.map((tag) => (
          <Tag
            key={tag}
            closable
            onClose={() => handleClose(tag)}
            style={{ marginBottom: 4 }}
          >
            {tag}
          </Tag>
        ))}
        {inputVisible ? (
          <Input
            size="small"
            style={{ width: 120 }}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onBlur={handleInputConfirm}
            onPressEnter={handleInputConfirm}
            autoFocus
          />
        ) : (
          <Tag
            style={{ borderStyle: "dashed", cursor: "pointer" }}
            onClick={() => setInputVisible(true)}
          >
            + {placeholder}
          </Tag>
        )}
      </div>
    );
  };

  // 节点卡片的展开内容
  const renderExpandedContent = (node: OutlineNode) => {
    return (
      <div
        style={{
          padding: "12px 0 0",
          borderTop: "1px solid #f0f0f0",
        }}
      >
        {/* 关键事件 */}
        <div style={{ marginBottom: 12 }}>
          <Text strong style={{ fontSize: 13 }}>
            关键事件
          </Text>
          <TagsEditor
            tags={node.key_events}
            onChange={(events) => handleKeyEventsChange(node.id, events)}
            placeholder="添加事件"
          />
        </div>

        {/* 情绪弧线 */}
        <div style={{ marginBottom: 12 }}>
          <Text strong style={{ fontSize: 13 }}>
            情绪弧线
          </Text>
          <TextArea
            rows={2}
            value={node.emotional_arc ?? ""}
            onChange={(e) => handleEmotionalArcChange(node.id, e.target.value)}
            placeholder="描述本章角色情绪变化..."
            size="small"
            style={{ marginTop: 4 }}
          />
        </div>

        {/* 伏笔 */}
        <div style={{ marginBottom: 12 }}>
          <Text strong style={{ fontSize: 13 }}>
            新增伏笔
          </Text>
          <TagsEditor
            tags={node.foreshadowing_items}
            onChange={(items) =>
              handleForeshadowingChange(
                node.id,
                items,
                node.foreshadowing_resolved,
              )
            }
            placeholder="添加伏笔"
          />
        </div>

        <div style={{ marginBottom: 12 }}>
          <Text strong style={{ fontSize: 13 }}>
            回收伏笔
          </Text>
          <TagsEditor
            tags={node.foreshadowing_resolved}
            onChange={(resolved) =>
              handleForeshadowingChange(
                node.id,
                node.foreshadowing_items,
                resolved,
              )
            }
            placeholder="添加回收项"
          />
        </div>

        {/* 写作指南 */}
        <div>
          <Text strong style={{ fontSize: 13 }}>
            写作指南
          </Text>
          <TextArea
            rows={4}
            value={node.writing_guide ?? ""}
            onChange={(e) => handleWritingGuideChange(node.id, e.target.value)}
            placeholder="AI 生成的写作指南将显示在此处..."
            size="small"
            style={{ marginTop: 4 }}
          />
        </div>
      </div>
    );
  };

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      {/* 顶部操作栏 */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "12px 16px",
          borderBottom: "1px solid #f0f0f0",
          background: "#fff",
          flexShrink: 0,
        }}
      >
        <Space size={12}>
          <Title level={4} style={{ margin: 0 }}>
            故事大纲
          </Title>
          {outline && (
            <Badge
              status={isConfirmed ? "success" : "default"}
              text={isConfirmed ? "已确认" : "未确认"}
            />
          )}
          {outline && (
            <Text type="secondary" style={{ fontSize: 13 }}>
              v{outline.version} · {sortedNodes.length} 章
            </Text>
          )}
        </Space>

        <Space>
          <Button
            type="primary"
            icon={<RobotOutlined />}
            onClick={() => setTaskModalOpen(true)}
            disabled={generating}
          >
            AI 生成大纲
          </Button>
          <Button
            icon={<CheckOutlined />}
            onClick={handleConfirmOutline}
            loading={saving}
            disabled={!outline}
            type={isConfirmed ? "default" : "primary"}
          >
            {isConfirmed ? "取消确认" : "确认大纲"}
          </Button>
          <Button icon={<PlusOutlined />} onClick={handleAddNode} loading={saving}>
            新增章节
          </Button>
        </Space>
      </div>

      {/* 主内容区 */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        {/* 左侧：节点列表 */}
        <div
          style={{
            flex: 1,
            overflow: "auto",
            padding: 16,
            minWidth: 0,
          }}
        >
          <Spin spinning={loading}>
            {sortedNodes.length > 0 ? (
              sortedNodes.map((node, index) => {
                const isExpanded = expandedIds.has(node.id);
                const isSelected = selectedNodeId === node.id;
                const firstIdx = index === 0;
                const lastIdx = index === sortedNodes.length - 1;

                return (
                  <Card
                    key={node.id}
                    size="small"
                    draggable
                    onDragStart={() => handleDragStart(index)}
                    onDragOver={(e) => handleDragOver(e, index)}
                    onDrop={handleDrop}
                    onDragEnd={handleDragEnd}
                    onClick={() => handleSelectNode(node.id)}
                    style={{
                      marginBottom: 8,
                      cursor: "grab",
                      border: isSelected
                        ? "1px solid #1677ff"
                        : "1px solid #f0f0f0",
                      opacity: 1,
                    }}
                    styles={{
                      body: { padding: 12 },
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "flex-start",
                        gap: 8,
                      }}
                    >
                      {/* 拖拽手柄 */}
                      <div
                        style={{
                          paddingTop: 4,
                          cursor: "grab",
                          color: "#999",
                        }}
                      >
                        <HolderOutlined />
                      </div>

                      {/* 章节序号 */}
                      <Badge
                        count={node.chapter_number}
                        style={{
                          backgroundColor: isSelected ? "#1677ff" : "#999",
                          flexShrink: 0,
                        }}
                      />

                      {/* 内容区 */}
                      <div style={{ flex: 1, minWidth: 0 }}>
                        {/* 标题 */}
                        <div style={{ marginBottom: 6 }}>
                          {editingField?.nodeId === node.id &&
                          editingField?.field === "title" ? (
                            <Space.Compact style={{ width: "100%" }}>
                              <Input
                                size="small"
                                value={editValue}
                                onChange={(e) => setEditValue(e.target.value)}
                                onPressEnter={saveEdit}
                                autoFocus
                              />
                              <Button
                                size="small"
                                icon={<CheckOutlined />}
                                onClick={saveEdit}
                              />
                              <Button
                                size="small"
                                icon={<CloseOutlined />}
                                onClick={cancelEdit}
                              />
                            </Space.Compact>
                          ) : (
                            <div
                              style={{
                                display: "flex",
                                alignItems: "center",
                                gap: 4,
                              }}
                            >
                              <Text strong style={{ fontSize: 14 }}>
                                {node.title || `第${node.chapter_number}章`}
                              </Text>
                              <EditOutlined
                                style={{
                                  fontSize: 11,
                                  color: "#bbb",
                                  cursor: "pointer",
                                }}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  startEdit(node.id, "title", node.title ?? "");
                                }}
                              />
                            </div>
                          )}
                        </div>

                        {/* 概要 */}
                        <div>
                          {editingField?.nodeId === node.id &&
                          editingField?.field === "summary" ? (
                            <Space.Compact
                              style={{ width: "100%" }}
                              direction="vertical"
                            >
                              <TextArea
                                size="small"
                                rows={2}
                                value={editValue}
                                onChange={(e) => setEditValue(e.target.value)}
                                autoFocus
                              />
                              <div style={{ marginTop: 4 }}>
                                <Button
                                  size="small"
                                  type="primary"
                                  icon={<CheckOutlined />}
                                  onClick={saveEdit}
                                >
                                  保存
                                </Button>
                                <Button
                                  size="small"
                                  icon={<CloseOutlined />}
                                  onClick={cancelEdit}
                                  style={{ marginLeft: 4 }}
                                >
                                  取消
                                </Button>
                              </div>
                            </Space.Compact>
                          ) : (
                            <div
                              style={{
                                display: "flex",
                                alignItems: "flex-start",
                                gap: 4,
                              }}
                            >
                              <Paragraph
                                ellipsis={{ rows: 2 }}
                                style={{
                                  margin: 0,
                                  fontSize: 13,
                                  color: "#666",
                                  flex: 1,
                                }}
                              >
                                {node.summary}
                              </Paragraph>
                              <EditOutlined
                                style={{
                                  fontSize: 11,
                                  color: "#bbb",
                                  cursor: "pointer",
                                  marginTop: 2,
                                  flexShrink: 0,
                                }}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  startEdit(node.id, "summary", node.summary ?? "");
                                }}
                              />
                            </div>
                          )}
                        </div>

                        {/* 标签信息 */}
                        <div style={{ marginTop: 8 }}>
                          <Space size={4} wrap>
                            {node.key_events.length > 0 && (
                              <Tooltip title="关键事件">
                                <Tag color="blue" style={{ fontSize: 11 }}>
                                  事件: {node.key_events.length}
                                </Tag>
                              </Tooltip>
                            )}
                            {node.foreshadowing_items.length > 0 && (
                              <Tooltip title="新增伏笔">
                                <Tag color="orange" style={{ fontSize: 11 }}>
                                  伏笔: {node.foreshadowing_items.length}
                                </Tag>
                              </Tooltip>
                            )}
                            {node.foreshadowing_resolved.length > 0 && (
                              <Tooltip title="回收伏笔">
                                <Tag color="green" style={{ fontSize: 11 }}>
                                  回收: {node.foreshadowing_resolved.length}
                                </Tag>
                              </Tooltip>
                            )}
                            {node.writing_guide && (
                              <Tag
                                icon={<InfoCircleOutlined />}
                                color="purple"
                                style={{ fontSize: 11 }}
                              >
                                有指南
                              </Tag>
                            )}
                          </Space>
                        </div>

                        {/* 展开/收起 + 操作按钮 */}
                        <div
                          style={{
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                            marginTop: 8,
                          }}
                        >
                          <Button
                            type="link"
                            size="small"
                            onClick={(e) => {
                              e.stopPropagation();
                              toggleExpand(node.id);
                            }}
                          >
                            {isExpanded ? "收起详情" : "展开详情"}
                          </Button>

                          <Space size={2}>
                            <Tooltip title="上移">
                              <Button
                                size="small"
                                type="text"
                                icon={<UpOutlined />}
                                disabled={firstIdx}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleMoveNode(node.id, "up");
                                }}
                              />
                            </Tooltip>
                            <Tooltip title="下移">
                              <Button
                                size="small"
                                type="text"
                                icon={<DownOutlined />}
                                disabled={lastIdx}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleMoveNode(node.id, "down");
                                }}
                              />
                            </Tooltip>
                            <Popconfirm
                              title="确定删除此章节？"
                              onConfirm={(e) => {
                                e?.stopPropagation();
                                handleDeleteNode(node.id);
                              }}
                              onCancel={(e) => e?.stopPropagation()}
                              okText="删除"
                              cancelText="取消"
                            >
                              <Tooltip title="删除">
                                <Button
                                  size="small"
                                  type="text"
                                  danger
                                  icon={<DeleteOutlined />}
                                  onClick={(e) => e.stopPropagation()}
                                />
                              </Tooltip>
                            </Popconfirm>
                          </Space>
                        </div>

                        {/* 展开的详细内容 */}
                        {isExpanded && renderExpandedContent(node)}
                      </div>
                    </div>
                  </Card>
                );
              })
            ) : (
              !loading && (
                <Empty
                  description={'暂无大纲节点，点击「AI 生成大纲」或「新增章节」开始'}
                  style={{ marginTop: 80 }}
                >
                  <Button
                    type="primary"
                    icon={<RobotOutlined />}
                    onClick={() => setTaskModalOpen(true)}
                  >
                    AI 生成大纲
                  </Button>
                </Empty>
              )
            )}
          </Spin>
        </div>

        {/* 右侧面板：写作指南预览 */}
        <div
          style={{
            width: 320,
            borderLeft: "1px solid #f0f0f0",
            padding: 16,
            overflow: "auto",
            background: "#fafafa",
            flexShrink: 0,
          }}
        >
          <Title level={5} style={{ marginBottom: 16 }}>
            AI 写作指南
          </Title>

          {selectedNode ? (
            <div>
              <Text strong style={{ fontSize: 14 }}>
                {selectedNode.title || `第${selectedNode.chapter_number}章`}
              </Text>
              <Paragraph type="secondary" style={{ marginTop: 4, fontSize: 13 }}>
                {selectedNode.summary}
              </Paragraph>

              <div style={{ marginTop: 16 }}>
                <Text strong style={{ fontSize: 13 }}>
                  写作指南
                </Text>
                {selectedNode.writing_guide ? (
                  <div
                    style={{
                      marginTop: 8,
                      padding: 12,
                      background: "#fff",
                      borderRadius: 6,
                      border: "1px solid #e8e8e8",
                      fontSize: 13,
                      lineHeight: 1.8,
                      whiteSpace: "pre-wrap",
                    }}
                  >
                    {selectedNode.writing_guide}
                  </div>
                ) : (
                  <div
                    style={{
                      marginTop: 8,
                      padding: 12,
                      background: "#fff",
                      borderRadius: 6,
                      border: "1px dashed #e8e8e8",
                      textAlign: "center",
                      color: "#bbb",
                      fontSize: 13,
                    }}
                  >
                    暂无写作指南
                    <br />
                    点击"AI 生成大纲"自动生成
                  </div>
                )}
              </div>

              {selectedNode.emotional_arc && (
                <div style={{ marginTop: 16 }}>
                  <Text strong style={{ fontSize: 13 }}>
                    情绪弧线
                  </Text>
                  <Paragraph
                    style={{
                      marginTop: 4,
                      fontSize: 13,
                      padding: 8,
                      background: "#fff",
                      borderRadius: 6,
                      border: "1px solid #e8e8e8",
                    }}
                  >
                    {selectedNode.emotional_arc}
                  </Paragraph>
                </div>
              )}
            </div>
          ) : (
            <Empty
              description="点击左侧章节查看写作指南"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          )}
        </div>
      </div>

      {/* AI 生成配置弹窗 */}
      <TaskConfigModal
        open={taskModalOpen}
        loading={generating}
        progress={generationProgress}
        progressMessage={progressMessage}
        totalChapters={sortedNodes.length}
        onCancel={() => {
          if (!generating) {
            setTaskModalOpen(false);
          }
        }}
        onSubmit={handleGenerateOutline}
      />
    </div>
  );
}

export default OutlineEditor;
