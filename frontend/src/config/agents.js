import { Cpu, Terminal, BarChart3, ShieldCheck } from 'lucide-react';

export const API = "";
export const CHAT_API = "/persona";

const AGENT_META = [
  { id: "manager", label: "Orchestrator", icon: Cpu, color: "#06b6d4", desc: "llama3.1:8b (Planning)" },
  { id: "writer", label: "Senior Coder", icon: Terminal, color: "#a855f7", desc: "qwen2.5-coder:14b (Drafting)" },
  { id: "editor", label: "Code Editor", icon: Terminal, color: "#db2777", desc: "qwen2.5-coder:14b (Fixes)" },
  { id: "tester", label: "QA Tester", icon: ShieldCheck, color: "#f59e0b", desc: "deepseek-r1:8b (Review)" },
  { id: "researcher", label: "Researcher", icon: BarChart3, color: "#22c55e", desc: "qwen2.5:14b (Data)" },
  { id: "heavy", label: "System Architect", icon: Cpu, color: "#6366f1", desc: "phi4:latest (Heavy Logic)" },
  { id: "context_manager", label: "Context Manager", icon: BarChart3, color: "#14b8a6", desc: "llama3.1:8b (Resident)" },
];

let _prompts = {};
let _loaded = false;

export async function loadAgentPrompts() {
  if (_loaded) return _prompts;
  try {
    const res = await fetch(`${API}/prompts`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    _prompts = data;
    _loaded = true;
    return data;
  } catch (e) {
    console.warn("Failed to load prompts from API, using fallback:", e);
    return {};
  }
}

export function getAgentPrompt(agentId, type = "chat") {
  return _prompts[agentId]?.[type] || "";
}

export function getAgents() {
  return AGENT_META;
}

export function getAgentById(id) {
  return AGENT_META.find(a => a.id === id);
}
