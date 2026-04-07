import { Cpu, Terminal, BarChart3, ShieldCheck } from 'lucide-react';

export const API = "";
export const CHAT_API = "/persona";

const AGENT_META = [
  { id: "manager", label: "Manager AI", icon: Cpu, color: "#06b6d4", desc: "System Planning" },
  { id: "coder", label: "Coder", icon: Terminal, color: "#a855f7", desc: "Software Engineer" },
  { id: "analyst", label: "Analyst", icon: BarChart3, color: "#22c55e", desc: "Data & Reasoning" },
  { id: "critic", label: "Critic", icon: ShieldCheck, color: "#f59e0b", desc: "Review & Ethics" },
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
