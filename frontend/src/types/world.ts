/** 势力项 */
export interface ForceItem {
  name: string;
  description: string;
}

/** 世界规则项 */
export interface RuleItem {
  name: string;
  description: string;
}

/** 时间线事件 */
export interface TimelineEvent {
  event: string;
  time: string;
  description: string;
}

/** 重要地点 */
export interface LocationItem {
  name: string;
  type: string;
  description: string;
}

/** 结构化世界观数据 */
export interface StructuredWorldData {
  forces: ForceItem[];
  rules: RuleItem[];
  timeline: TimelineEvent[];
  locations: LocationItem[];
}

/** 默认空结构化数据 */
export const EMPTY_STRUCTURED_DATA: StructuredWorldData = {
  forces: [],
  rules: [],
  timeline: [],
  locations: [],
};

/** 世界观设定 */
export interface WorldSetting {
  id: string;
  project_id: string;
  original_content?: string;
  expanded_content?: string;
  structured_data: StructuredWorldData;
  is_expanded: boolean;
}

/** 世界观设定保存请求 */
export interface WorldSettingSaveData {
  original_content?: string;
  expanded_content?: string;
  structured_data?: StructuredWorldData;
}
