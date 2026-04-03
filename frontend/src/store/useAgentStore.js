import { create } from 'zustand';

const INITIAL_NODES_STATE = {
  manager: { status: 'idle', input: '', output: '', metadata: {}, error: '' },
  coder: { status: 'idle', input: '', output: '', metadata: {}, error: '' },
  analyst: { status: 'idle', input: '', output: '', metadata: {}, error: '' },
  critic: { status: 'idle', input: '', output: '', metadata: {}, error: '' },
  tool: { status: 'idle', input: '', output: '', metadata: {}, error: '' },
  executor: { status: 'idle', input: '', output: '', metadata: {}, error: '' },
};

export const useAgentStore = create((set) => ({
  nodesState: { ...INITIAL_NODES_STATE },
  executionLog: [],
  activeRunId: null,
  selectedNodeId: null,
  availableModels: [],
  configuredModels: {},
  setAvailableModels: (models) => set({ availableModels: models }),
  setConfiguredModels: (models) => set({ configuredModels: models }),

  // Workspace
  projects: [],
  selectedProject: null,
  selectedFile: null,
  fileContent: '',
  isEditing: false,
  editContent: '',

  setSelectedNode: (id) => set({ selectedNodeId: id }),
  setProjects: (projects) => set({ projects }),
  setSelectedProject: (p) => set({ selectedProject: p, selectedFile: null, fileContent: '' }),
  setSelectedFile: (f) => set({ selectedFile: f }),
  setFileContent: (c) => set({ fileContent: c }),
  setIsEditing: (v) => set({ isEditing: v }),
  setEditContent: (c) => set({ editContent: c }),

  updateNode: (runId, nodeId, payload) => set((state) => ({
    activeRunId: runId,
    nodesState: {
      ...state.nodesState,
      [nodeId]: { ...(state.nodesState[nodeId] || { status: 'idle', input: '', output: '', metadata: {}, error: '' }), ...payload }
    }
  })),

  addTimelineEvent: (event) => set((state) => ({
    executionLog: [...state.executionLog, event]
  })),

  resetAll: () => set({
    nodesState: { ...INITIAL_NODES_STATE },
    activeRunId: null,
    executionLog: [],
  }),
}));
