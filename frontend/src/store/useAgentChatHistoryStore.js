import { create } from 'zustand';

const STORAGE_KEY = 'agentChatHistory';

function loadFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {}
  return [];
}

function saveToStorage(sessions) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
  } catch {}
}

export const useAgentChatHistoryStore = create((set, get) => ({
  sessions: loadFromStorage(),
  activeSessionId: null,

  createSession: (agent, model) => {
    const session = {
      id: `agent_${Date.now()}`,
      title: 'New Chat',
      agent: agent ? { id: agent.id, label: agent.label, color: agent.color } : null,
      model: model || '',
      messages: [],
      createdAt: Date.now(),
    };
    const sessions = [session, ...get().sessions];
    saveToStorage(sessions);
    set({ sessions, activeSessionId: session.id });
    return session;
  },

  setActiveSession: (id) => set({ activeSessionId: id }),

  addMessage: (message) => {
    const sessions = get().sessions.map(s => {
      if (s.id !== get().activeSessionId) return s;
      const updated = { ...s, messages: [...s.messages, message] };
      if (s.title === 'New Chat' && message.role === 'user') {
        updated.title = message.content.slice(0, 50) + (message.content.length > 50 ? '...' : '');
      }
      return updated;
    });
    saveToStorage(sessions);
    set({ sessions });
  },

  updateLastMessage: (updater) => {
    const sessions = get().sessions.map(s => {
      if (s.id !== get().activeSessionId || s.messages.length === 0) return s;
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      msgs[msgs.length - 1] = typeof updater === 'function' ? updater(last) : updater;
      return { ...s, messages: msgs };
    });
    saveToStorage(sessions);
    set({ sessions });
  },

  deleteSession: (id) => {
    const sessions = get().sessions.filter(s => s.id !== id);
    saveToStorage(sessions);
    set({
      sessions,
      activeSessionId: get().activeSessionId === id ? null : get().activeSessionId,
    });
  },

  setSessionMessages: (messages) => {
    const sessions = get().sessions.map(s => {
      if (s.id !== get().activeSessionId) return s;
      return { ...s, messages };
    });
    saveToStorage(sessions);
    set({ sessions });
  },

  updateSessionMeta: (meta) => {
    const sessions = get().sessions.map(s => {
      if (s.id !== get().activeSessionId) return s;
      return { ...s, ...meta };
    });
    saveToStorage(sessions);
    set({ sessions });
  },

  clearAll: () => {
    saveToStorage([]);
    set({ sessions: [], activeSessionId: null });
  },
}));
