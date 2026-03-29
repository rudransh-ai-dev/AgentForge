import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Terminal, Activity, Sparkles, Search, Cpu, Zap, BrainCircuit, Network,
  Play, StopCircle, FolderTree, Clock, HardDrive, Wifi, MessageSquare,
  LayoutDashboard, ChevronRight, Square
} from 'lucide-react';
import AgentCanvas from './components/AgentCanvas';
import WorkspaceExplorer from './components/WorkspaceExplorer';
import AgentChat from './components/AgentChat';
import { useAgentStore } from './store/useAgentStore';

const API = "http://127.0.0.1:8888";

export default function Dashboard() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [query, setQuery] = useState('');
  const [currentTime, setCurrentTime] = useState(new Date().toLocaleTimeString());
  const [activeTab, setActiveTab] = useState('chat');

  const { nodesState, executionLog, projects } = useAgentStore();
  const isSystemActive = Object.values(nodesState).some(n => n?.status === 'running');

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date().toLocaleTimeString()), 1000);
    return () => clearInterval(timer);
  }, []);

  const [sysStats, setSysStats] = useState({ total_runs: 0, success_rate: 0, fix_rate: 0 });
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch(`${API}/memory/stats`);
        setSysStats(await res.json());
      } catch(e) {}
    };
    fetchStats();
    const interval = setInterval(fetchStats, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleQuery = async (e) => {
    if (e.key === 'Enter' && query.trim() !== '') {
      const prompt = query;
      setQuery('');
      setIsProcessing(true);
      try {
        await fetch(`${API}/run`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt })
        });
      } catch (err) {
        console.error("Connection error!");
      } finally {
        setIsProcessing(false);
      }
    }
  };

  const handleStop = async () => {
    try {
      await fetch(`${API}/stop`, { method: "POST" });
      useAgentStore.getState().resetAll();
    } catch(e) {}
  };

  const TABS = [
    { id: 'chat',      icon: <MessageSquare className="w-4 h-4" />, label: 'Agent Chat' },
    { id: 'canvas',    icon: <Network className="w-4 h-4" />,       label: 'Canvas' },
    { id: 'workspace', icon: <FolderTree className="w-4 h-4" />,    label: 'Files', badge: projects.length || null },
  ];

  const AGENTS_LIST = [
    { name: "Manager AI",   model: "Llama-3-8B",    color: "cyan" },
    { name: "Coder Agent",  model: "DeepSeek-6.7B",  color: "purple" },
    { name: "Analyst",      model: "Phi-3-Mini",      color: "green" },
    { name: "Critic",       model: "Llama-3",         color: "amber" },
    { name: "Tool Agent",   model: "Filesystem",      color: "pink" },
    { name: "Executor",     model: "subprocess",      color: "blue" },
  ];

  return (
    <div className="flex h-screen bg-[#050505] text-white relative overflow-hidden font-sans">

      {/* Background */}
      <div className="fixed inset-0 -z-10 pointer-events-none bg-[#050505]">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(0,240,255,0.04)_0,rgba(5,5,5,1)_100%)]" />
      </div>

      {/* ── SIDEBAR ── */}
      <div className="w-64 border-r border-white/[0.06] flex flex-col bg-[#080810]">

        {/* Logo */}
        <div className="flex items-center gap-3 px-5 py-6 border-b border-white/[0.06]">
          <div className="p-2 rounded-xl bg-gradient-to-br from-cyan-500/20 to-purple-500/20 border border-white/10">
            <BrainCircuit className="text-cyan-400 w-5 h-5" />
          </div>
          <h1 className="text-lg font-bold tracking-tight">
            Local<span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-purple-500">AI</span>
          </h1>
        </div>

        {/* Navigation */}
        <div className="flex-1 flex flex-col px-3 py-4 overflow-y-auto custom-scrollbar">
          <div className="space-y-1 mb-6">
            {TABS.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-[13px] font-medium transition-all relative ${
                  activeTab === tab.id
                    ? 'bg-white/[0.06] text-white'
                    : 'text-gray-500 hover:text-gray-300 hover:bg-white/[0.03]'
                }`}
              >
                {activeTab === tab.id && (
                  <motion.div layoutId="tab-indicator" className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 bg-cyan-400 rounded-full" />
                )}
                <span className={activeTab === tab.id ? 'text-cyan-400' : ''}>{tab.icon}</span>
                {tab.label}
                {tab.badge && (
                  <span className="ml-auto bg-white/[0.06] text-cyan-400 text-[10px] px-1.5 py-0.5 rounded font-mono">
                    {tab.badge}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Agents List */}
          <div className="border-t border-white/[0.06] pt-4">
            <div className="text-[10px] font-bold text-gray-600 uppercase tracking-widest px-3 mb-3">Local Agents</div>
            <div className="space-y-0.5">
              {AGENTS_LIST.map(agent => (
                <div key={agent.name} className="flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-white/[0.03] cursor-pointer transition-colors group">
                  <div className={`w-1.5 h-1.5 rounded-full bg-${agent.color}-400`} style={{ boxShadow: `0 0 6px var(--tw-shadow-color, rgba(100,200,255,0.3))` }} />
                  <div className="flex-1 min-w-0">
                    <p className="text-[12px] text-gray-400 group-hover:text-gray-200 transition-colors truncate">{agent.name}</p>
                  </div>
                  <span className="text-[9px] text-gray-600 font-mono">{agent.model}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Bottom stats */}
        <div className="border-t border-white/[0.06] px-4 py-3">
          <div className="flex items-center justify-between text-[10px] font-mono text-gray-600">
            <span>{sysStats.total_runs} runs</span>
            <span className="text-green-500">{sysStats.success_rate}% ok</span>
          </div>
        </div>
      </div>

      {/* ── MAIN AREA ── */}
      <div className="flex-1 flex flex-col min-w-0">

        {/* Top Bar */}
        <div className="h-14 border-b border-white/[0.06] flex items-center gap-4 px-6 bg-[#080810]/50 backdrop-blur-sm shrink-0">

          {/* Prompt input */}
          <div className="flex-1 max-w-xl relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-600" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleQuery}
              disabled={isProcessing || isSystemActive}
              placeholder={isSystemActive ? "Processing..." : "Run a task across agents..."}
              className="w-full bg-white/[0.03] border border-white/[0.06] rounded-lg py-2 pl-9 pr-4 text-[13px] text-gray-300 placeholder-gray-600 focus:outline-none focus:border-cyan-500/30 disabled:opacity-40 transition-colors"
            />
          </div>

          {/* Right controls */}
          <div className="flex items-center gap-3">
            <span className="text-[11px] text-gray-600 font-mono">{currentTime}</span>

            <div className="flex items-center gap-2 bg-white/[0.03] border border-white/[0.06] px-3 py-1.5 rounded-lg text-[10px] font-mono">
              <span className="text-pink-400">{sysStats.total_runs} runs</span>
              <span className="text-white/10">|</span>
              <span className="text-green-400">{sysStats.success_rate}%</span>
            </div>

            {/* Stop button */}
            {isSystemActive ? (
              <button
                onClick={handleStop}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 rounded-lg text-red-400 text-[11px] font-bold transition-all animate-pulse"
              >
                <Square className="w-3 h-3 fill-red-400" /> Stop
              </button>
            ) : (
              <div className="flex items-center gap-1.5 px-3 py-1.5 bg-white/[0.03] border border-white/[0.06] rounded-lg text-[11px] text-gray-500">
                <div className="w-1.5 h-1.5 rounded-full bg-green-400" /> Ready
              </div>
            )}
          </div>
        </div>

        {/* Content area */}
        <div className="flex-1 flex overflow-hidden">
          <AnimatePresence mode="wait">
            {activeTab === 'chat' && (
              <motion.div key="chat" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 flex">
                <AgentChat />
              </motion.div>
            )}
            {activeTab === 'canvas' && (
              <motion.div key="canvas" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 flex p-4 gap-4">
                <AgentCanvas />
                <TimelinePanel executionLog={executionLog} />
              </motion.div>
            )}
            {activeTab === 'workspace' && (
              <motion.div key="workspace" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 flex">
                <WorkspaceExplorer />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

// ── Timeline Panel (Canvas tab only) ──

function TimelinePanel({ executionLog }) {
  return (
    <div className="w-[380px] flex flex-col gap-4 shrink-0">
      <div className="flex-1 glass-panel rounded-2xl flex flex-col overflow-hidden bg-gradient-to-b from-black/40 to-black/80 border border-white/5">
        <div className="p-4 border-b border-white/[0.06] flex items-center gap-2">
          <Zap className="w-4 h-4 text-purple-400" />
          <span className="font-bold text-gray-200 text-xs uppercase tracking-wider">Timeline</span>
          <span className="ml-auto text-[10px] text-gray-600 font-mono">{executionLog.length} events</span>
        </div>
        <div className="flex-1 p-3 overflow-y-auto space-y-2 font-mono text-[10px] custom-scrollbar">
          <AnimatePresence>
            {[...executionLog].reverse().map((log) => (
              <motion.div
                key={log.event_id}
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                className="bg-[#0a0a0f] border border-white/5 rounded-lg p-2.5"
              >
                <div className="flex items-center justify-between mb-1 opacity-60">
                  <span className="text-gray-500 text-[9px]">{new Date(log.timestamp).toLocaleTimeString()}</span>
                  <span className={`uppercase font-bold tracking-widest text-[8px] px-1.5 py-0.5 rounded ${
                    log.type === 'start' ? 'text-amber-400 bg-amber-400/10' :
                    log.type === 'complete' ? 'text-green-400 bg-green-400/10' :
                    log.type === 'error' ? 'text-red-400 bg-red-400/10' : 'text-blue-400 bg-blue-400/10'
                  }`}>
                    {log.node_id} · {log.type}
                  </span>
                </div>
                <div className="text-gray-400 leading-relaxed break-words whitespace-pre-wrap truncate max-h-12">
                  {log.output ? String(log.output).slice(0, 150) : String(log.input).slice(0, 150)}
                </div>
              </motion.div>
            )).slice(0, 50)}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
