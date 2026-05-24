import { useState, useCallback } from "react";
import {
  Input,
  Button,
  Collapse,
  Row,
  Col,
  Typography,
  Empty,
  Popconfirm,
} from "antd";
import {
  PlusOutlined,
  DeleteOutlined,
} from "@ant-design/icons";
import type {
  StructuredWorldData,
  ForceItem,
  RuleItem,
  TimelineEvent,
  LocationItem,
} from "@/types/world";

const { TextArea } = Input;
const { Text } = Typography;

interface WorldSettingFormProps {
  originalContent: string;
  structuredData: StructuredWorldData;
  onContentChange: (value: string) => void;
  onStructuredDataChange: (data: StructuredWorldData) => void;
}

function WorldSettingForm({
  originalContent,
  structuredData,
  onContentChange,
  onStructuredDataChange,
}: WorldSettingFormProps) {
  const [activeKeys, setActiveKeys] = useState<string[]>([
    "forces",
    "rules",
    "timeline",
    "locations",
  ]);

  const safeData: StructuredWorldData = {
    forces: structuredData?.forces ?? [],
    rules: structuredData?.rules ?? [],
    timeline: structuredData?.timeline ?? [],
    locations: structuredData?.locations ?? [],
  };

  const emit = useCallback(
    (patch: Partial<StructuredWorldData>) => {
      onStructuredDataChange({ ...safeData, ...patch });
    },
    [safeData, onStructuredDataChange],
  );

  // =================== Forces ===================

  const updateForce = useCallback(
    (index: number, field: keyof ForceItem, value: string) => {
      const forces = safeData.forces.map((f, i) =>
        i === index ? { ...f, [field]: value } : f,
      );
      emit({ forces });
    },
    [safeData.forces, emit],
  );

  const addForce = useCallback(() => {
    emit({
      forces: [
        ...safeData.forces,
        { name: "", description: "" },
      ],
    });
  }, [safeData.forces, emit]);

  const removeForce = useCallback(
    (index: number) => {
      emit({ forces: safeData.forces.filter((_, i) => i !== index) });
    },
    [safeData.forces, emit],
  );

  // =================== Rules ===================

  const updateRule = useCallback(
    (index: number, field: keyof RuleItem, value: string) => {
      const rules = safeData.rules.map((r, i) =>
        i === index ? { ...r, [field]: value } : r,
      );
      emit({ rules });
    },
    [safeData.rules, emit],
  );

  const addRule = useCallback(() => {
    emit({ rules: [...safeData.rules, { name: "", description: "" }] });
  }, [safeData.rules, emit]);

  const removeRule = useCallback(
    (index: number) => {
      emit({ rules: safeData.rules.filter((_, i) => i !== index) });
    },
    [safeData.rules, emit],
  );

  // =================== Timeline ===================

  const updateTimeline = useCallback(
    (index: number, field: keyof TimelineEvent, value: string) => {
      const timeline = safeData.timeline.map((t, i) =>
        i === index ? { ...t, [field]: value } : t,
      );
      emit({ timeline });
    },
    [safeData.timeline, emit],
  );

  const addTimeline = useCallback(() => {
    emit({
      timeline: [
        ...safeData.timeline,
        { event: "", time: "", description: "" },
      ],
    });
  }, [safeData.timeline, emit]);

  const removeTimeline = useCallback(
    (index: number) => {
      emit({ timeline: safeData.timeline.filter((_, i) => i !== index) });
    },
    [safeData.timeline, emit],
  );

  // =================== Locations ===================

  const updateLocation = useCallback(
    (index: number, field: keyof LocationItem, value: string) => {
      const locations = safeData.locations.map((l, i) =>
        i === index ? { ...l, [field]: value } : l,
      );
      emit({ locations });
    },
    [safeData.locations, emit],
  );

  const addLocation = useCallback(() => {
    emit({
      locations: [
        ...safeData.locations,
        { name: "", type: "", description: "" },
      ],
    });
  }, [safeData.locations, emit]);

  const removeLocation = useCallback(
    (index: number) => {
      emit({ locations: safeData.locations.filter((_, i) => i !== index) });
    },
    [safeData.locations, emit],
  );

  // =================== Collapse items ===================

  const collapseItems = [
    {
      key: "forces",
      label: `势力分布（${safeData.forces.length}）`,
      children: (
        <div>
          {safeData.forces.length === 0 && (
            <Empty description="暂无势力" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
          {safeData.forces.map((force, index) => (
            <div
              key={index}
              style={{
                marginBottom: 12,
                padding: 12,
                border: "1px solid #f0f0f0",
                borderRadius: 6,
              }}
            >
              <Row gutter={[12, 8]}>
                <Col xs={24} sm={8}>
                  <Input
                    placeholder="势力名称"
                    value={force.name}
                    onChange={(e) => updateForce(index, "name", e.target.value)}
                  />
                </Col>
                <Col xs={22} sm={14}>
                  <Input
                    placeholder="势力描述"
                    value={force.description}
                    onChange={(e) =>
                      updateForce(index, "description", e.target.value)
                    }
                  />
                </Col>
                <Col xs={2} sm={2} style={{ textAlign: "right" }}>
                  <Popconfirm
                    title="确定删除此势力？"
                    onConfirm={() => removeForce(index)}
                    okText="确定"
                    cancelText="取消"
                  >
                    <Button
                      type="text"
                      danger
                      icon={<DeleteOutlined />}
                      size="small"
                    />
                  </Popconfirm>
                </Col>
              </Row>
            </div>
          ))}
          <Button
            type="dashed"
            onClick={addForce}
            icon={<PlusOutlined />}
            block
          >
            添加势力
          </Button>
        </div>
      ),
    },
    {
      key: "rules",
      label: `世界规则（${safeData.rules.length}）`,
      children: (
        <div>
          {safeData.rules.length === 0 && (
            <Empty description="暂无规则" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
          {safeData.rules.map((rule, index) => (
            <div
              key={index}
              style={{
                marginBottom: 12,
                padding: 12,
                border: "1px solid #f0f0f0",
                borderRadius: 6,
              }}
            >
              <Row gutter={[12, 8]}>
                <Col xs={24} sm={8}>
                  <Input
                    placeholder="规则名称"
                    value={rule.name}
                    onChange={(e) => updateRule(index, "name", e.target.value)}
                  />
                </Col>
                <Col xs={22} sm={14}>
                  <Input
                    placeholder="规则描述"
                    value={rule.description}
                    onChange={(e) =>
                      updateRule(index, "description", e.target.value)
                    }
                  />
                </Col>
                <Col xs={2} sm={2} style={{ textAlign: "right" }}>
                  <Popconfirm
                    title="确定删除此规则？"
                    onConfirm={() => removeRule(index)}
                    okText="确定"
                    cancelText="取消"
                  >
                    <Button
                      type="text"
                      danger
                      icon={<DeleteOutlined />}
                      size="small"
                    />
                  </Popconfirm>
                </Col>
              </Row>
            </div>
          ))}
          <Button
            type="dashed"
            onClick={addRule}
            icon={<PlusOutlined />}
            block
          >
            添加规则
          </Button>
        </div>
      ),
    },
    {
      key: "timeline",
      label: `时间线（${safeData.timeline.length}）`,
      children: (
        <div>
          {safeData.timeline.length === 0 && (
            <Empty
              description="暂无时间线事件"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          )}
          {safeData.timeline.map((event, index) => (
            <div
              key={index}
              style={{
                marginBottom: 12,
                padding: 12,
                border: "1px solid #f0f0f0",
                borderRadius: 6,
              }}
            >
              <Row gutter={[12, 8]}>
                <Col xs={24} sm={6}>
                  <Input
                    placeholder="事件名称"
                    value={event.event}
                    onChange={(e) =>
                      updateTimeline(index, "event", e.target.value)
                    }
                  />
                </Col>
                <Col xs={24} sm={5}>
                  <Input
                    placeholder="时间（如：公元前300年）"
                    value={event.time}
                    onChange={(e) =>
                      updateTimeline(index, "time", e.target.value)
                    }
                  />
                </Col>
                <Col xs={22} sm={11}>
                  <Input
                    placeholder="事件描述"
                    value={event.description}
                    onChange={(e) =>
                      updateTimeline(index, "description", e.target.value)
                    }
                  />
                </Col>
                <Col xs={2} sm={2} style={{ textAlign: "right" }}>
                  <Popconfirm
                    title="确定删除此事件？"
                    onConfirm={() => removeTimeline(index)}
                    okText="确定"
                    cancelText="取消"
                  >
                    <Button
                      type="text"
                      danger
                      icon={<DeleteOutlined />}
                      size="small"
                    />
                  </Popconfirm>
                </Col>
              </Row>
            </div>
          ))}
          <Button
            type="dashed"
            onClick={addTimeline}
            icon={<PlusOutlined />}
            block
          >
            添加事件
          </Button>
        </div>
      ),
    },
    {
      key: "locations",
      label: `重要地点（${safeData.locations.length}）`,
      children: (
        <div>
          {safeData.locations.length === 0 && (
            <Empty description="暂无地点" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
          {safeData.locations.map((location, index) => (
            <div
              key={index}
              style={{
                marginBottom: 12,
                padding: 12,
                border: "1px solid #f0f0f0",
                borderRadius: 6,
              }}
            >
              <Row gutter={[12, 8]}>
                <Col xs={24} sm={7}>
                  <Input
                    placeholder="地点名称"
                    value={location.name}
                    onChange={(e) =>
                      updateLocation(index, "name", e.target.value)
                    }
                  />
                </Col>
                <Col xs={24} sm={5}>
                  <Input
                    placeholder="地点类型（如：城市、秘境）"
                    value={location.type}
                    onChange={(e) =>
                      updateLocation(index, "type", e.target.value)
                    }
                  />
                </Col>
                <Col xs={22} sm={10}>
                  <Input
                    placeholder="地点描述"
                    value={location.description}
                    onChange={(e) =>
                      updateLocation(index, "description", e.target.value)
                    }
                  />
                </Col>
                <Col xs={2} sm={2} style={{ textAlign: "right" }}>
                  <Popconfirm
                    title="确定删除此地？"
                    onConfirm={() => removeLocation(index)}
                    okText="确定"
                    cancelText="取消"
                  >
                    <Button
                      type="text"
                      danger
                      icon={<DeleteOutlined />}
                      size="small"
                    />
                  </Popconfirm>
                </Col>
              </Row>
            </div>
          ))}
          <Button
            type="dashed"
            onClick={addLocation}
            icon={<PlusOutlined />}
            block
          >
            添加地点
          </Button>
        </div>
      ),
    },
  ];

  // =================== Layout ===================

  return (
    <Row gutter={[24, 24]}>
      {/* 左侧：自由文本编辑区 */}
      <Col xs={24} lg={12}>
        <div style={{ marginBottom: 8 }}>
          <Text strong>自由文本描述</Text>
        </div>
        <TextArea
          rows={18}
          placeholder="描述你的故事世界...包括时代背景、地理环境、势力分布、特殊规则等"
          value={originalContent}
          onChange={(e) => onContentChange(e.target.value)}
          maxLength={5000}
          showCount
          style={{ fontFamily: "inherit" }}
        />
      </Col>

      {/* 右侧：结构化数据编辑区 */}
      <Col xs={24} lg={12}>
        <div style={{ marginBottom: 8 }}>
          <Text strong>结构化设定</Text>
        </div>
        <Collapse
          activeKey={activeKeys}
          onChange={(keys) => setActiveKeys(keys as string[])}
          items={collapseItems}
        />
      </Col>
    </Row>
  );
}

export default WorldSettingForm;
