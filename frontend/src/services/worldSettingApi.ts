import api from "./api";
import type { ApiResponse } from "@/types";
import type {
  WorldSetting,
  WorldSettingSaveData,
} from "@/types/world";

/** 获取项目世界观设定 */
export function getWorldSetting(
  projectId: string,
): Promise<ApiResponse<WorldSetting>> {
  return api
    .get(`/projects/${projectId}/world-setting`)
    .then((res) => res.data);
}

/** 保存或更新项目世界观设定 */
export function saveWorldSetting(
  projectId: string,
  data: WorldSettingSaveData,
): Promise<ApiResponse<WorldSetting>> {
  return api
    .put(`/projects/${projectId}/world-setting`, data)
    .then((res) => res.data);
}
