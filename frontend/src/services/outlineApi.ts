import api from "./api";
import type { ApiResponse } from "@/types";
import type {
  Outline,
  OutlineNode,
  OutlineNodeCreate,
  OutlineNodeUpdate,
  OutlineNodeReorderRequest,
  OutlineUpdateData,
} from "@/types/outline";

export function getOutline(
  projectId: string,
): Promise<ApiResponse<Outline>> {
  return api.get(`/projects/${projectId}/outline`).then((res) => res.data);
}

export function updateOutline(
  projectId: string,
  data: OutlineUpdateData,
): Promise<ApiResponse<Outline>> {
  return api
    .put(`/projects/${projectId}/outline`, data)
    .then((res) => res.data);
}

export function confirmOutline(
  projectId: string,
): Promise<ApiResponse<Outline>> {
  return api
    .post(`/projects/${projectId}/outline/confirm`)
    .then((res) => res.data);
}

export function batchCreateNodes(
  projectId: string,
  nodes: OutlineNodeCreate[],
): Promise<ApiResponse<OutlineNode[]>> {
  return api
    .post(`/projects/${projectId}/outline/nodes/batch`, { nodes })
    .then((res) => res.data);
}

export function updateNode(
  projectId: string,
  nodeId: string,
  data: OutlineNodeUpdate,
): Promise<ApiResponse<OutlineNode>> {
  return api
    .put(`/projects/${projectId}/outline/nodes/${nodeId}`, data)
    .then((res) => res.data);
}

export function deleteNode(
  projectId: string,
  nodeId: string,
): Promise<ApiResponse<null>> {
  return api
    .delete(`/projects/${projectId}/outline/nodes/${nodeId}`)
    .then((res) => res.data);
}

export function reorderNodes(
  projectId: string,
  nodeIds: OutlineNodeReorderRequest,
): Promise<ApiResponse<null>> {
  return api
    .put(`/projects/${projectId}/outline/nodes/reorder`, { node_ids: nodeIds })
    .then((res) => res.data);
}
