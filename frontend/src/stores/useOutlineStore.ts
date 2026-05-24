import { create } from "zustand";
import type { Outline, OutlineNode, OutlineNodeUpdate, OutlineNodeCreate } from "@/types/outline";
import {
  getOutline,
  updateOutline,
  confirmOutline as confirmOutlineApi,
  batchCreateNodes,
  updateNode,
  deleteNode,
  reorderNodes,
} from "@/services/outlineApi";
import { message } from "antd";

interface OutlineStore {
  outline: Outline | null;
  loading: boolean;
  saving: boolean;
  selectedNodeId: string | null;

  fetchOutline: (projectId: string) => Promise<void>;
  confirmOutline: (projectId: string) => Promise<void>;
  setSelectedNodeId: (nodeId: string | null) => void;

  addNode: (projectId: string, data: OutlineNodeCreate) => Promise<void>;
  editNode: (projectId: string, nodeId: string, data: OutlineNodeUpdate) => Promise<void>;
  removeNode: (projectId: string, nodeId: string) => Promise<void>;
  moveNode: (projectId: string, dragIndex: number, hoverIndex: number) => Promise<void>;

  getSortedNodes: () => OutlineNode[];
  getSelectedNode: () => OutlineNode | null;
}

export const useOutlineStore = create<OutlineStore>((set, get) => ({
  outline: null,
  loading: false,
  saving: false,
  selectedNodeId: null,

  fetchOutline: async (projectId: string) => {
    set({ loading: true });
    try {
      const res = await getOutline(projectId);
      set({ outline: res.data });
    } catch {
      set({ outline: null });
    } finally {
      set({ loading: false });
    }
  },

  confirmOutline: async (projectId: string) => {
    const { outline } = get();
    if (!outline) return;
    set({ saving: true });
    try {
      const isConfirmed = !outline.is_confirmed;
      if (isConfirmed) {
        await confirmOutlineApi(projectId);
      } else {
        await updateOutline(projectId, { is_confirmed: false });
      }
      set({
        outline: { ...outline, is_confirmed: !outline.is_confirmed },
      });
      message.success(isConfirmed ? "大纲已确认" : "大纲已取消确认");
    } catch {
      message.error("操作失败");
    } finally {
      set({ saving: false });
    }
  },

  setSelectedNodeId: (nodeId: string | null) => {
    set({ selectedNodeId: nodeId });
  },

  addNode: async (projectId: string, data: OutlineNodeCreate) => {
    const { outline } = get();
    if (!outline) return;
    set({ saving: true });
    try {
      const res = await batchCreateNodes(projectId, [data]);
      const newNodes = res.data;
      set({
        outline: {
          ...outline,
          nodes: [...outline.nodes, ...newNodes].sort(
            (a, b) => a.sort_order - b.sort_order,
          ),
        },
      });
      message.success("章节已添加");
    } catch {
      message.error("添加章节失败");
    } finally {
      set({ saving: false });
    }
  },

  editNode: async (projectId: string, nodeId: string, data: OutlineNodeUpdate) => {
    const { outline } = get();
    if (!outline) return;
    set({ saving: true });
    try {
      const res = await updateNode(projectId, nodeId, data);
      const updatedNode = res.data;
      set({
        outline: {
          ...outline,
          nodes: outline.nodes.map((n) =>
            n.id === nodeId ? { ...n, ...updatedNode } : n,
          ),
        },
      });
    } catch {
      message.error("更新章节失败");
    } finally {
      set({ saving: false });
    }
  },

  removeNode: async (projectId: string, nodeId: string) => {
    const { outline } = get();
    if (!outline) return;
    try {
      await deleteNode(projectId, nodeId);
      set({
        outline: {
          ...outline,
          nodes: outline.nodes.filter((n) => n.id !== nodeId),
        },
        selectedNodeId: get().selectedNodeId === nodeId ? null : get().selectedNodeId,
      });
      message.success("章节已删除");
    } catch {
      message.error("删除章节失败");
    }
  },

  moveNode: async (projectId: string, dragIndex: number, hoverIndex: number) => {
    const { outline } = get();
    if (!outline || dragIndex === hoverIndex) return;

    const sortedNodes = [...outline.nodes].sort(
      (a, b) => a.sort_order - b.sort_order,
    );
    const reordered = [...sortedNodes];
    const [moved] = reordered.splice(dragIndex, 1);
    reordered.splice(hoverIndex, 0, moved);

    // Optimistic update
    const newNodes = reordered.map((node, idx) => ({
      ...node,
      sort_order: idx,
    }));

    set({
      outline: { ...outline, nodes: newNodes },
    });

    try {
      await reorderNodes(
        projectId,
        reordered.map((n) => n.id),
      );
    } catch {
      message.error("排序失败，正在恢复");
      // Revert on failure
      set({
        outline: { ...outline, nodes: sortedNodes },
      });
    }
  },

  getSortedNodes: () => {
    const { outline } = get();
    if (!outline) return [];
    return [...outline.nodes].sort((a, b) => a.sort_order - b.sort_order);
  },

  getSelectedNode: () => {
    const { outline, selectedNodeId } = get();
    if (!outline || !selectedNodeId) return null;
    return outline.nodes.find((n) => n.id === selectedNodeId) ?? null;
  },
}));
