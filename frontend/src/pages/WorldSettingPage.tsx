import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Steps, Card, Button, Spin, message } from "antd";
import {
  ArrowLeftOutlined,
  ArrowRightOutlined,
} from "@ant-design/icons";
import WorldSettingForm from "@/components/project/WorldSettingForm";
import {
  getWorldSetting,
  saveWorldSetting,
} from "@/services/worldSettingApi";
import type { StructuredWorldData } from "@/types/world";
import { EMPTY_STRUCTURED_DATA } from "@/types/world";

const STEPS = [
  { title: "项目信息" },
  { title: "角色设定" },
  { title: "世界观设定" },
  { title: "大纲生成" },
];

function WorldSettingPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [originalContent, setOriginalContent] = useState("");
  const [structuredData, setStructuredData] = useState<StructuredWorldData>(
    EMPTY_STRUCTURED_DATA,
  );

  // 加载已有数据
  useEffect(() => {
    if (!projectId) return;
    setLoading(true);
    getWorldSetting(projectId)
      .then((res) => {
        const ws = res.data;
        setOriginalContent(ws.original_content ?? "");
        setStructuredData(ws.structured_data ?? EMPTY_STRUCTURED_DATA);
      })
      .catch(() => {
        // 世界观设定可能尚未创建，不提示错误
        setOriginalContent("");
        setStructuredData({ ...EMPTY_STRUCTURED_DATA });
      })
      .finally(() => setLoading(false));
  }, [projectId]);

  // 上一步
  const handlePrev = useCallback(() => {
    navigate(`/projects/${projectId}/outline`);
  }, [navigate, projectId]);

  // 保存并继续
  const handleSaveAndContinue = useCallback(async () => {
    if (!projectId) return;
    setSaving(true);
    try {
      await saveWorldSetting(projectId, {
        original_content: originalContent,
        structured_data: structuredData,
      });
      message.success("世界观设定保存成功");
      navigate(`/projects/${projectId}/outline`);
    } catch {
      message.error("保存失败，请稍后重试");
    } finally {
      setSaving(false);
    }
  }, [projectId, originalContent, structuredData, navigate]);

  return (
    <Spin spinning={loading}>
      <div style={{ maxWidth: 1200, margin: "0 auto", padding: 24 }}>
        {/* 步骤条 */}
        <Card
          style={{ marginBottom: 24, background: "#fafafa" }}
          bodyStyle={{ padding: 16 }}
        >
          <Steps current={2} size="small" items={STEPS} />
        </Card>

        {/* 主内容区 */}
        <Card title="世界观设定" bodyStyle={{ padding: 24 }}>
          <WorldSettingForm
            originalContent={originalContent}
            structuredData={structuredData}
            onContentChange={setOriginalContent}
            onStructuredDataChange={setStructuredData}
          />
        </Card>

        {/* 底部按钮 */}
        <div
          style={{
            marginTop: 24,
            display: "flex",
            justifyContent: "space-between",
          }}
        >
          <Button
            size="large"
            icon={<ArrowLeftOutlined />}
            onClick={handlePrev}
          >
            上一步
          </Button>
          <Button
            type="primary"
            size="large"
            icon={<ArrowRightOutlined />}
            onClick={handleSaveAndContinue}
            loading={saving}
          >
            保存并继续
          </Button>
        </div>
      </div>
    </Spin>
  );
}

export default WorldSettingPage;
