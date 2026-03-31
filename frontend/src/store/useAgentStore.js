import { create } from 'zustand';

export const useAgentStore = create((set, get) => ({
  nodesState: {
    manager: { status: 'idle', input: '', output: '', metadata: {}, error: '' },
    coder: { status: 'idle', input: '', output: '', metadata: {}, error: '' },
    analyst: { status: 'idle', input: '', output: '', metadata: {}, error: '' },
    critic: { status: 'idle', input: '', output: '', metadata: {}, error: '' },
    tool: { status: 'idle', input: '', output: '', metadata: {}, error: '' },
    executor: { status: 'idle', input: '', output: '', metadata: {}, error: '' },
  },
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
    nodesState: {
      manager: { status: 'idle', input: '', output: '', metadata: {}, error: '' },
      coder: { status: 'idle', input: '', output: '', metadata: {}, error: '' },
      analyst: { status: 'idle', input: '', output: '', metadata: {}, error: '' },
      critic: { status: 'idle', input: '', output: '', metadata: {}, error: '' },
      tool: { status: 'idle', input: '', output: '', metadata: {}, error: '' },
      executor: { status: 'idle', input: '', output: '', metadata: {}, error: '' },
    },
    activeRunId: null,
    executionLog: [],
  }),

  // Replay
  replayTimeline: async () => {
    const { executionLog } = get();
    if (!executionLog.length) return;

    set({
      nodesState: {
        manager: { status: 'idle', input: '', output: '', metadata: {}, error: '' },
        coder: { status: 'idle', input: '', output: '', metadata: {}, error: '' },
        analyst: { status: 'idle', input: '', output: '', metadata: {}, error: '' },
        critic: { status: 'idle', input: '', output: '', metadata: {}, error: '' },
        tool: { status: 'idle', input: '', output: '', metadata: {}, error: '' },
        executor: { status: 'idle', input: '', output: '', metadata: {}, error: '' },
      }
    });

    for (const ev of executionLog) {
      await new Promise(resolve => setTimeout(resolve, ev.type === 'start' ? 500 : ev.type === 'complete' ? 1000 : 70));
      const payload = {};
      if (ev.type === 'start') { payload.status = 'running'; payload.input = ev.input || ''; payload.output = ''; payload.error = ''; }
      else if (ev.type === 'update') { payload.output = ev.output; }
      else if (ev.type === 'complete') { payload.status = 'success'; payload.output = ev.output; payload.metadata = ev.metadata || {}; }
      else if (ev.type === 'error') { payload.status = 'error'; payload.error = ev.error; }

      set((state) => ({
        activeRunId: ev.run_id,
        nodesState: {
          ...state.nodesState,
          [ev.node_id]: { ...(state.nodesState[ev.node_id] || {}), ...payload }
        }
      }));
    }
  }
}));
