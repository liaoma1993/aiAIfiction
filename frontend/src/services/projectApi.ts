import api from './api';

export const authApi = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }).then((r) => r.data),
  register: (email: string, username: string, password: string) =>
    api.post('/auth/register', { email, username, password }).then((r) => r.data),
};

export const projectApi = {
  list: () => api.get('/projects').then((r) => r.data.projects),
  create: (data: any) => api.post('/projects', data).then((r) => r.data),
  get: (id: string) => api.get(`/projects/${id}`).then((r) => r.data.project),
  update: (id: string, data: any) => api.put(`/projects/${id}`, data).then((r) => r.data.project),
  delete: (id: string) => api.delete(`/projects/${id}`),
};

export const volumeApi = {
  list: (projectId: string) => api.get(`/projects/${projectId}/volumes`).then((r) => r.data.volumes),
  create: (projectId: string, data: any) => api.post(`/projects/${projectId}/volumes`, data).then((r) => r.data.volume),
  update: (projectId: string, volId: string, data: any) =>
    api.put(`/projects/${projectId}/volumes/${volId}`, data).then((r) => r.data.volume),
  remove: (projectId: string, volId: string) => api.delete(`/projects/${projectId}/volumes/${volId}`),
};

export const characterApi = {
  list: (projectId: string) => api.get(`/projects/${projectId}/characters`).then((r) => r.data.characters),
  create: (projectId: string, data: any) => api.post(`/projects/${projectId}/characters`, data).then((r) => r.data.character),
  update: (projectId: string, charId: string, data: any) =>
    api.put(`/projects/${projectId}/characters/${charId}`, data).then((r) => r.data.character),
};

export const factionApi = {
  list: (projectId: string) => api.get(`/projects/${projectId}/factions`).then((r) => r.data.factions),
  create: (projectId: string, data: any) => api.post(`/projects/${projectId}/factions`, data).then((r) => r.data.faction),
  update: (projectId: string, fId: string, data: any) =>
    api.put(`/projects/${projectId}/factions/${fId}`, data).then((r) => r.data.faction),
  remove: (projectId: string, fId: string) => api.delete(`/projects/${projectId}/factions/${fId}`),
};

export const outlineApi = {
  get: (projectId: string) => api.get(`/projects/${projectId}/outline`).then((r) => r.data),
  create: (projectId: string, nodes: any[]) => api.post(`/projects/${projectId}/outline`, { nodes }).then((r) => r.data),
  updateNode: (projectId: string, nodeId: string, data: any) =>
    api.put(`/projects/${projectId}/outline/nodes/${nodeId}`, data).then((r) => r.data.node),
};

export const chapterApi = {
  list: (projectId: string) => api.get(`/projects/${projectId}/chapters`).then((r) => r.data.chapters),
  get: (projectId: string, chId: string) => api.get(`/projects/${projectId}/chapters/${chId}`).then((r) => r.data.chapter),
  create: (projectId: string, data: any) => api.post(`/projects/${projectId}/chapters`, data).then((r) => r.data.chapter),
  update: (projectId: string, chId: string, data: any) =>
    api.put(`/projects/${projectId}/chapters/${chId}`, data).then((r) => r.data.chapter),
  versions: (projectId: string, chId: string) =>
    api.get(`/projects/${projectId}/chapters/${chId}/versions`).then((r) => r.data.versions),
  snapshot: (projectId: string, chId: string) =>
    api.post(`/projects/${projectId}/chapters/${chId}/versions`).then((r) => r.data.version),
  restoreVersion: (projectId: string, chId: string, versionId: string) =>
    api.post(`/projects/${projectId}/chapters/${chId}/versions/${versionId}/restore`).then((r) => r.data.chapter),
};

export const relationshipApi = {
  list: (projectId: string) => api.get(`/projects/${projectId}/relationships`).then((r) => r.data.events),
  create: (projectId: string, data: any) => api.post(`/projects/${projectId}/relationships`, data).then((r) => r.data.event),
};

export const worldSettingApi = {
  get: (projectId: string) => api.get(`/projects/${projectId}/world-setting`).then((r) => r.data.world_setting),
  update: (projectId: string, data: any) =>
    api.put(`/projects/${projectId}/world-setting`, data).then((r) => r.data.world_setting),
};

export const writingStyleSkillApi = {
  list: () => api.get('/writing-style-skills').then((r) => r.data.skills),
  analyze: (data: any) => api.post('/writing-style-skills/analyze', data).then((r) => r.data.skill),
  analyzeUpload: (data: FormData) =>
    api.post('/writing-style-skills/analyze-upload', data, {
      headers: { 'Content-Type': undefined as any },
      timeout: 120000,
    }).then((r) => r.data),
  task: (taskId: string) => api.get(`/writing-style-skills/task/${taskId}`).then((r) => r.data.task),
  tasks: () => api.get('/writing-style-skills/tasks').then((r) => r.data.tasks),
  update: (id: string, data: any) => api.put(`/writing-style-skills/${id}`, data).then((r) => r.data.skill),
  remove: (id: string) => api.delete(`/writing-style-skills/${id}`),
  setActive: (projectId: string, skillId: string | null) =>
    api.put(`/projects/${projectId}/active-writing-style-skill`, { skill_id: skillId }).then((r) => r.data.project),
};

export const wizardApi = {
  generateStoryBible: (projectId: string) => api.post(`/projects/${projectId}/wizard/generate-story-bible`).then((r) => r.data),
  reviewProjectStructure: (projectId: string) => api.post(`/projects/${projectId}/wizard/review-project-structure`).then((r) => r.data),
};

export const providerApi = {
  list: () => api.get('/providers').then((r) => r.data.providers),
  create: (data: any) => api.post('/providers', data).then((r) => r.data.provider),
  update: (id: string, data: any) => api.put(`/providers/${id}`, data).then((r) => r.data.provider),
  remove: (id: string) => api.delete(`/providers/${id}`),
  test: (id: string) => api.post(`/providers/${id}/test`).then((r) => r.data),
};

export const storyApi = {
  elements: (projectId: string) => api.get(`/projects/${projectId}/story/elements`).then((r) => r.data),
  memoryCenter: (projectId: string) => api.get(`/projects/${projectId}/story/memory-center`).then((r) => r.data),
  graph: (projectId: string) => api.get(`/projects/${projectId}/story/graph`).then((r) => r.data),
  landscape: (projectId: string) => api.get(`/projects/${projectId}/story/landscape`).then((r) => r.data),
  qualityDashboard: (projectId: string) => api.get(`/projects/${projectId}/story/quality-dashboard`).then((r) => r.data),
  addForeshadowing: (projectId: string, data: any) => api.post(`/projects/${projectId}/story/foreshadowing`, data).then((r) => r.data.foreshadowing),
  removeForeshadowing: (projectId: string, id: string) => api.delete(`/projects/${projectId}/story/foreshadowing/${id}`),
  addEvent: (projectId: string, data: any) => api.post(`/projects/${projectId}/story/events`, data).then((r) => r.data.event),
  removeEvent: (projectId: string, id: string) => api.delete(`/projects/${projectId}/story/events/${id}`),
};

export const auditApi = {
  chapter: (projectId: string, chapterId: string) =>
    api.post(`/projects/${projectId}/wizard/audit-chapter/${chapterId}`).then((r) => r.data),
};
