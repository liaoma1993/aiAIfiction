export interface Outline {
  id: string;
  project_id: string;
  is_confirmed: boolean;
  version: number;
  nodes: OutlineNode[];
  created_at: string;
  updated_at: string;
}

export interface OutlineNode {
  id: string;
  outline_id: string;
  chapter_number: number;
  title?: string;
  summary: string;
  key_events: string[];
  emotional_arc?: string;
  writing_guide?: string;
  foreshadowing_items: string[];
  foreshadowing_resolved: string[];
  sort_order: number;
}

export interface OutlineUpdateData {
  is_confirmed?: boolean;
}

export interface OutlineNodeCreate {
  chapter_number: number;
  title?: string;
  summary: string;
  key_events?: string[];
  emotional_arc?: string;
  writing_guide?: string;
  foreshadowing_items?: string[];
  foreshadowing_resolved?: string[];
  sort_order?: number;
}

export interface OutlineNodeUpdate {
  title?: string;
  summary?: string;
  key_events?: string[];
  emotional_arc?: string;
  writing_guide?: string;
  foreshadowing_items?: string[];
  foreshadowing_resolved?: string[];
  chapter_number?: number;
}

export type OutlineNodeReorderRequest = string[];

export interface GenerateOutlineRequest {
  project_id: string;
  start_chapter?: number;
  model?: string;
}
