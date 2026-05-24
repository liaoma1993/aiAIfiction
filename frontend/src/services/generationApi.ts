import api from "./api";
import type { ApiResponse } from "@/types";
import type {
  GenerationTask,
  TaskLog,
  GenerationConfig,
} from "@/types/generation";

export function startGeneration(
  projectId: string,
  config: GenerationConfig,
): Promise<ApiResponse<GenerationTask>> {
  return api
    .post(`/projects/${projectId}/generate`, config)
    .then((res) => res.data);
}

export function cancelGeneration(
  projectId: string,
  taskId: string,
): Promise<ApiResponse<null>> {
  return api
    .post(`/projects/${projectId}/generate/${taskId}/cancel`)
    .then((res) => res.data);
}

export function getGenerationTasks(
  projectId: string,
): Promise<ApiResponse<GenerationTask[]>> {
  return api
    .get(`/projects/${projectId}/generate/tasks`)
    .then((res) => res.data);
}

export function getTaskLogs(
  projectId: string,
  taskId: string,
  stage?: string,
): Promise<ApiResponse<TaskLog[]>> {
  return api
    .get(`/projects/${projectId}/generate/${taskId}/logs`, {
      params: stage ? { stage } : undefined,
    })
    .then((res) => res.data);
}

export interface PolishRequest {
  chapter_id?: string;
  polish_types: string[];
  target_content?: string;
}

export function startPolish(
  projectId: string,
  data: PolishRequest,
): Promise<ApiResponse<GenerationTask>> {
  return api
    .post(`/projects/${projectId}/generate/polish`, data)
    .then((res) => res.data);
}

export interface ModifyRequest {
  chapter_id?: string;
  instruction: string;
  target_content?: string;
}

export function startModify(
  projectId: string,
  data: ModifyRequest,
): Promise<ApiResponse<GenerationTask>> {
  return api
    .post(`/projects/${projectId}/generate/modify`, data)
    .then((res) => res.data);
}

export interface ChapterContinueRequest {
  chapter_id?: string;
  target_word_count: number;
  based_on_selection?: boolean;
  selected_text?: string;
}

export function startChapterGeneration(
  projectId: string,
  data: ChapterContinueRequest,
): Promise<ApiResponse<GenerationTask>> {
  return api
    .post(`/projects/${projectId}/generate/chapter`, data)
    .then((res) => res.data);
}

export interface ChatRequest {
  project_id: string;
  message: string;
  context?: string;
}

export interface ChatResponse {
  reply: string;
}

export function sendChatMessage(
  projectId: string,
  data: ChatRequest,
): Promise<ApiResponse<ChatResponse>> {
  return api
    .post(`/projects/${projectId}/chat`, data)
    .then((res) => res.data);
}
