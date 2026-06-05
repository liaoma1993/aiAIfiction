import { create } from 'zustand';
import { projectApi } from '@/services/projectApi';

interface Project {
  id: string; title: string; genre: string; target_total_words: number;
  story_brief: string; wizard_step: number; status: string;
  core_theme: string; secondary_themes: string[]; motifs: any[];
  narrative_lines: any[]; writing_style: any;
  created_at: string; updated_at: string;
}

interface ProjectState {
  projects: Project[];
  current: Project | null;
  loading: boolean;
  fetchProjects: () => Promise<void>;
  fetchProject: (id: string) => Promise<void>;
  createProject: (data: any) => Promise<string>;
  updateProject: (id: string, data: any) => Promise<void>;
  deleteProject: (id: string) => Promise<void>;
  setCurrent: (p: Project | null) => void;
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  projects: [],
  current: null,
  loading: false,

  fetchProjects: async () => {
    set({ loading: true });
    const projects = await projectApi.list();
    set({ projects, loading: false });
  },

  fetchProject: async (id) => {
    set({ loading: true });
    const project = await projectApi.get(id);
    set({ current: project, loading: false });
  },

  createProject: async (data) => {
    const result = await projectApi.create(data);
    return result.project_id;
  },

  updateProject: async (id, data) => {
    const updated = await projectApi.update(id, data);
    set({ current: updated });
  },

  deleteProject: async (id) => {
    await projectApi.delete(id);
    set({ projects: get().projects.filter((p) => p.id !== id) });
  },

  setCurrent: (p) => set({ current: p }),
}));
