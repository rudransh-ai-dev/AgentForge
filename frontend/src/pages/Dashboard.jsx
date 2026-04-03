import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Terminal, Activity, Search, Cpu, Zap, BrainCircuit, Network,
  FolderTree, Clock, Wifi, MessageSquare, MessageCircle, Square, WifiOff,
  AlertTriangle, CheckCircle2, Loader2, PanelLeftClose, PanelLeft
} from 'lucide-react';
import AgentCanvas from '../components/AgentCanvas';
import WorkspaceExplorer from '../components/WorkspaceExplorer';
import SimpleChat from '../components/SimpleChat';
import AgentChat from '../components/AgentChat';
import TimelinePanel from '../components/TimelinePanel';
import { useAgentStore } from '../store/useAgentStore';

const API = "http://127.0.0.1:8888";

// ── Page transition variants ──
const pageVariants = {
  initial: { opacity: 0, scale: 0.98, y: 8 },
  animate: { opacity: 1, scale: 1, y: 0 },
  exit: { opacity: 0, scale: 0.98, y: -8 },
};
const pageTransition = { duration: 0.25, ease: [0.4, 0, 0.2, 1] };

// ── Connection Status Component ──
function ConnectionStatus({ health }) {
  const [showModels, setShowModels] = useState(false);
  const popoverRef = React.useRef(null);

  useEffect(() => {
    const handleClickAway = (e) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target)) {
        setShowModels(false);
      }
    };
    if (showModels) document.addEventListener('mousedown', handleClickAway);
    return () => document.removeEventListener('mousedown', handleClickAway);
  }, [showModels]);

  const statusMap = {
    connected: { icon: <Wifi className="w-3 h-3" />, color: "text-green-400", bg: "bg-green-500/10", border: "border-green-500/20", label: "Ollama" },
    disconnected: { icon: <WifiOff className="w-3 h-3" />, color: "text-red-400", bg: "bg-red-500/10", border: "border-red-500/20", label: "Offline" },
    checking: { icon: <Loader2 className="w-3 h-3 animate-spin" />, color: "text-yellow-400", bg: "bg-yellow-500/10", border: "border-yellow-500/20", label: "Checking" },
  };
  const s = statusMap[health.ollama] || statusMap.checking;

  return (
    <div className="relative" ref={popoverRef}>
      <button 
        onClick={() => setShowModels(!showModels)}
        className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg ${s.bg} border ${s.border} text-[10px] font-mono ${s.color} transition-all duration-300 hover:brightness-125 cursor-pointer active:scale-95`}
      >
        {s.icon}
        <span className="hidden sm:inline">{s.label}</span>
        {health.models?.length > 0 && (
          <span className="text-gray-500 hidden md:inline">· {health.models.length} models</span>
        )}
      </button>

      <AnimatePresence>
        {showModels && (
          <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.98 }}
            transition={{ duration: 0.15 }}
            className="absolute top-full right-0 mt-3 w-80 bg-[#000000] border border-white/10 rounded-xl shadow-[0_30px_90px_rgba(0,0,0,1)] z-[100] overflow-hidden"
          >
            <div className="p-4 border-b border-white/[0.1] bg-[#050505]">
              <span className="text-[11px] font-bold text-gray-300 uppercase tracking-[0.2em] flex items-center gap-2.5">
                <div className="p-1 rounded-md bg-cyan-500/10 border border-cyan-500/20">
                  <Cpu className="w-3.5 h-3.5 text-cyan-400" />
                </div>
                Available Models
              </span>
            </div>
            
            <div className="p-1.5 max-h-[350px] overflow-y-auto custom-scrollbar bg-black">
              {health.models?.length > 0 ? (
                health.models.map((model, idx) => (
                  <div 
                    key={idx} 
                    className="flex items-center gap-4 px-3.5 py-3 rounded-lg hover:bg-white/[0.06] transition-all group cursor-default mb-1 last:mb-0"
                    title={model}
                  >
                    <div className="w-8 h-8 rounded-lg bg-[#0a0a0f] border border-white/[0.08] flex items-center justify-center text-[11px] text-cyan-500 font-bold group-hover:border-cyan-500/40 group-hover:bg-cyan-500/10 transition-all shrink-0">
                      {idx + 1}
                    </div>
                    
                    <div className="flex flex-col min-w-0 flex-1">
                      <span className="text-[13px] font-semibold text-gray-200 truncate group-hover:text-white transition-colors">
                        {model}
                      </span>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[9px] text-gray-600 font-mono tracking-wider uppercase">manifest</span>
                        <div className="w-1 h-1 rounded-full bg-gray-700" />
                        <span className="text-[9px] text-gray-600 font-mono tracking-wider uppercase">local</span>
                      </div>
                    </div>
                    
                    <div className="shrink-0">
                       <div className="w-2 h-2 rounded-full bg-cyan-500/50 shadow-[0_0_10px_rgba(6,182,212,0.6)] group-hover:bg-cyan-400 group-hover:shadow-[0_0_15px_rgba(6,182,212,0.8)] transition-all" />
                    </div>
                  </div>
                ))
              ) : (
                <div className="py-10 text-center">
                  <span className="text-[12px] text-gray-600 italic">Finding models...</span>
                </div>
              )}
            </div>
            
            <div className="p-3 border-t border-white/[0.1] bg-[#050505] flex items-center justify-between px-4">
              <span className="text-[10px] text-gray-600 font-mono">{health.models?.length} total units</span>
              <span className="text-[10px] text-cyan-500/50 font-mono tracking-tighter">OLLAMA_SYSTEM::LIVE</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function Dashboard() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [query, setQuery] = useState('');
  const [currentTime, setCurrentTime] = useState(new Date().toLocaleTimeString());
  const [activeTab, setActiveTab] = useState('chat');
  const [sidebarExpanded, setSidebarExpanded] = useState(false);
  const [sidebarPinned, setSidebarPinned] = useState(false);
  const [execMode, setExecMode] = useState('auto');
  const [allowHeavy, setAllowHeavy] = useState(false);
  const searchInputRef = React.useRef(null);

  const { nodesState, executionLog, projects } = useAgentStore();
  const isSystemActive = Object.values(nodesState).some(n => n?.status === 'running');

  // ── Global WebSocket (persists across tab switches) ──
  const wsRef = useRef(null);
  const [wsStatus, setWsStatus] = useState('disconnected');
  const storeRef = useRef({ updateNode: null, addTimelineEvent: null });
  storeRef.current.updateNode = useAgentStore.getState().updateNode;
  storeRef.current.addTimelineEvent = useAgentStore.getState().addTimelineEvent;

  useEffect(() => {
    let ws;
    let reconnectTimer;
    let pingTimer;

    const connect = () => {
      setWsStatus('connecting');
      ws = new WebSocket('ws://127.0.0.1:8888/ws/agent-stream');
      wsRef.current = ws;

      ws.onopen = () => {
        setWsStatus('connected');
        pingTimer = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, 15000);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          storeRef.current.addTimelineEvent(data);
          const { run_id, node_id, type, input, output, metadata, error } = data;
          if (type === 'start') {
            storeRef.current.updateNode(run_id, node_id, { status: 'running', input: input || '', output: '', error: '' });
          } else if (type === 'update') {
            storeRef.current.updateNode(run_id, node_id, { output });
          } else if (type === 'complete') {
            storeRef.current.updateNode(run_id, node_id, { status: 'success', output, metadata: metadata || {} });
          } else if (type === 'error') {
            storeRef.current.updateNode(run_id, node_id, { status: 'error', error });
          }
        } catch (e) {
          console.warn('WS parse error:', e);
        }
      };

      ws.onclose = () => {
        clearInterval(pingTimer);
        setWsStatus('disconnected');
        reconnectTimer = setTimeout(connect, 2000);
      };

      ws.onerror = () => {
        setWsStatus('error');
        ws.close();
      };
    };

    connect();

    return () => {
      clearTimeout(reconnectTimer);
      clearInterval(pingTimer);
      if (ws && ws.readyState !== WebSocket.CLOSED && ws.readyState !== WebSocket.CLOSING) {
        ws.onclose = null;
        ws.close();
      }
    };
  }, []);

  // ── Health check polling ──
  const [health, setHealth] = useState({ ollama: 'checking', models: [], backend: 'checking' });
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch(`${API}/health`);
        const data = await res.json();
        setHealth(data);
        if (data.models && data.configured) {
          const BLOCKED = ["uncensored", "abliterated", "gurubot"];
          const safe = data.models.filter(m => !BLOCKED.some(kw => m.toLowerCase().includes(kw)));
          useAgentStore.getState().setAvailableModels(safe);
          useAgentStore.getState().setConfiguredModels(data.configured);
        }
      } catch {
        setHealth({ ollama: 'disconnected', models: [], backend: 'disconnected' });
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  // ── Clock ──
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date().toLocaleTimeString()), 1000);
    return () => clearInterval(timer);
  }, []);

  // ── Ctrl+K ──
  useEffect(() => {
    const down = (e) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
    };
    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, []);

  // ── Stats ──
  const [sysStats, setSysStats] = useState({ total_runs: 0, success_rate: 0, fix_rate: 0 });
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch(`${API}/memory/stats`);
        setSysStats(await res.json());
      } catch (e) { }
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
          body: JSON.stringify({ prompt, mode: execMode, allow_heavy: allowHeavy })
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
    } catch (e) { }
  };

  const handleClearLogs = async () => {
    useAgentStore.getState().resetAll();
  };

  const TABS = useMemo(() => [
    { id: 'chat', icon: <MessageSquare className="w-[18px] h-[18px]" />, label: 'Agent Chat' },
    { id: 'simple-chat', icon: <MessageCircle className="w-[18px] h-[18px]" />, label: 'Chat' },
    { id: 'canvas', icon: <Network className="w-[18px] h-[18px]" />, label: 'Canvas' },
    { id: 'workspace', icon: <FolderTree className="w-[18px] h-[18px]" />, label: 'Files', badge: projects.length || null },
  ], [projects.length]);

  const isSidebarVisible = sidebarExpanded || sidebarPinned;

  return (
    <div className="flex h-screen bg-[#050505] text-white relative overflow-hidden font-sans">

      {/* ── Animated Background ── */}
      <div className="fixed inset-0 -z-10 pointer-events-none">
        <div className="absolute inset-0 bg-[#050505]" />
        <motion.div 
          animate={{ opacity: [0.04, 0.06, 0.04] }}
          transition={{ duration: 8, repeat: Infinity }}
          className="absolute inset-0 bg-[radial-gradient(ellipse_at_20%_50%,rgba(0,240,255,0.06)_0,transparent_60%)]" 
        />
        <motion.div 
          animate={{ opacity: [0.03, 0.05, 0.03] }}
          transition={{ duration: 10, repeat: Infinity }}
          className="absolute inset-0 bg-[radial-gradient(ellipse_at_80%_20%,rgba(168,85,247,0.05)_0,transparent_60%)]" 
        />
        <motion.div 
          animate={{ opacity: [0.02, 0.04, 0.02] }}
          transition={{ duration: 12, repeat: Infinity }}
          className="absolute inset-0 bg-[radial-gradient(ellipse_at_50%_80%,rgba(236,72,153,0.04)_0,transparent_60%)]" 
        />
        {/* Subtle animated noise overlay */}
        <div className="absolute inset-0 opacity-[0.015]" style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
        }} />
        {/* Floating particles */}
        <div className="absolute inset-0 overflow-hidden">
          {[...Array(15)].map((_, i) => (
            <motion.div
              key={i}
              className="absolute w-0.5 h-0.5 rounded-full bg-cyan-400/20"
              style={{
                left: `${Math.random() * 100}%`,
                top: `${Math.random() * 100}%`,
              }}
              animate={{
                y: [0, -20, 0],
                x: [0, Math.random() * 10 - 5, 0],
                opacity: [0.1, 0.4, 0.1],
              }}
              transition={{
                duration: 3 + Math.random() * 3,
                repeat: Infinity,
                delay: Math.random() * 2,
              }}
            />
          ))}
        </div>
      </div>

      {/* ── SIDEBAR ── */}
      <motion.div
        className="flex flex-col bg-[#080810]/90 backdrop-blur-sm border-r border-white/[0.06] relative z-30 shrink-0"
        animate={{ width: isSidebarVisible ? 240 : 60 }}
        transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
        onMouseEnter={() => !sidebarPinned && setSidebarExpanded(true)}
        onMouseLeave={() => !sidebarPinned && setSidebarExpanded(false)}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 py-5 border-b border-white/[0.06] min-h-[68px]">
          <motion.div 
            whileHover={{ rotate: 360 }}
            transition={{ duration: 0.5 }}
            className="p-2 rounded-xl bg-gradient-to-br from-cyan-500/20 to-purple-500/20 border border-white/10 shrink-0 animate-neon-pulse"
          >
            <BrainCircuit className="text-cyan-400 w-5 h-5" />
          </motion.div>
          <AnimatePresence>
            {isSidebarVisible && (
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                transition={{ duration: 0.2 }}
                className="flex items-center gap-2 overflow-hidden"
              >
                <h1 className="text-lg font-bold tracking-tight whitespace-nowrap">
                  Local<span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-purple-500 to-pink-500 animate-gradient-shift bg-[length:200%_200%]">AI</span>
                </h1>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Navigation */}
        <div className="flex-1 flex flex-col px-2 py-3 overflow-y-auto custom-scrollbar">
          <div className="space-y-1 mb-4">
            {TABS.map((tab, idx) => (
              <motion.div
                key={tab.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.05 }}
              >
                <button
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-[13px] font-medium transition-all relative group ${activeTab === tab.id
                      ? 'bg-white/[0.08] text-white shadow-[0_0_20px_rgba(0,240,255,0.05)]'
                      : 'text-gray-500 hover:text-gray-300 hover:bg-white/[0.04]'
                    }`}
                  title={!isSidebarVisible ? tab.label : undefined}
                >
                  {activeTab === tab.id && (
                    <motion.div
                      layoutId="tab-indicator"
                      className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 bg-cyan-400 rounded-full shadow-[0_0_8px_rgba(0,240,255,0.5)]"
                    />
                  )}
                  <span className={`shrink-0 transition-colors ${activeTab === tab.id ? 'text-cyan-400' : 'group-hover:text-cyan-400/60'}`}>
                    {tab.icon}
                  </span>
                  <AnimatePresence>
                    {isSidebarVisible && (
                      <motion.span
                        initial={{ opacity: 0, width: 0 }}
                        animate={{ opacity: 1, width: 'auto' }}
                        exit={{ opacity: 0, width: 0 }}
                        transition={{ duration: 0.2 }}
                        className="whitespace-nowrap overflow-hidden"
                      >
                        {tab.label}
                      </motion.span>
                    )}
                  </AnimatePresence>
                  {tab.badge && isSidebarVisible && (
                    <span className="ml-auto bg-white/[0.06] text-cyan-400 text-[10px] px-1.5 py-0.5 rounded font-mono">
                      {tab.badge}
                    </span>
                  )}
                </button>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Sidebar pin toggle */}
        <div className="p-2 border-t border-white/[0.04]">
          <button
            onClick={() => setSidebarPinned(!sidebarPinned)}
            className="w-full flex items-center justify-center gap-2 py-2 rounded-lg hover:bg-white/[0.04] text-gray-600 hover:text-gray-300 transition-colors"
            title={sidebarPinned ? "Unpin sidebar" : "Pin sidebar"}
          >
            {sidebarPinned ? <PanelLeftClose className="w-4 h-4" /> : <PanelLeft className="w-4 h-4" />}
            <AnimatePresence>
              {isSidebarVisible && (
                <motion.span
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="text-[11px] whitespace-nowrap"
                >
                  {sidebarPinned ? 'Unpin' : 'Pin'}
                </motion.span>
              )}
            </AnimatePresence>
          </button>
        </div>
      </motion.div>

      {/* ── MAIN AREA ── */}
      <div className="flex-1 flex flex-col min-w-0">

        {/* Top Bar */}
        <div className="h-14 border-b border-white/[0.06] flex items-center gap-3 px-5 bg-[#080810]/50 backdrop-blur-sm shrink-0">

          {/* Prompt input */}
          <div className="flex-1 max-w-3xl flex items-center gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-600" />
              <input
                ref={searchInputRef}
                name="command-input"
                id="command-input"
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleQuery}
                disabled={isProcessing || isSystemActive}
                placeholder={isSystemActive ? "Processing..." : "Command Center: run task... (Ctrl + K)"}
                className="w-full bg-white/[0.03] border border-white/[0.06] rounded-lg py-2 pl-10 pr-16 text-[13px] text-gray-300 placeholder-gray-600 focus:outline-none focus:border-cyan-500/30 disabled:opacity-40 transition-all duration-300 shadow-[inset_0_2px_10px_rgba(0,0,0,0.2)]"
              />
              <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none flex gap-1 items-center">
                 <span className="text-[9px] font-bold bg-[#111] border border-white/10 text-gray-400 px-1.5 py-0.5 rounded shadow-sm opacity-80 uppercase">Ctrl+K</span>
              </div>
            </div>

            {/* Execution Toggles */}
            <div className="flex items-center gap-1 shrink-0">
              <div className="flex items-center bg-white/[0.02] border border-white/[0.06] rounded-lg p-0.5 shrink-0">
                 {['auto', 'direct', 'agent'].map(mode => (
                   <button
                     key={mode}
                     onClick={() => setExecMode(mode)}
                     className={`px-2.5 py-1.5 text-[10px] font-bold tracking-wider uppercase rounded-md transition-all ${
                       execMode === mode 
                         ? 'bg-cyan-500/20 text-cyan-400 shadow-[0_0_10px_rgba(6,182,212,0.1)]' 
                         : 'text-gray-500 hover:text-gray-300 hover:bg-white/[0.05]'
                     }`}
                     title={`Run in ${mode} mode`}
                   >
                     {mode}
                   </button>
                 ))}
              </div>

              <button
                 onClick={() => setAllowHeavy(!allowHeavy)}
                 className={`flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-bold uppercase rounded-lg border transition-all shrink-0 ${
                   allowHeavy 
                     ? 'bg-purple-500/10 text-purple-400 border-purple-500/30 shadow-[0_0_10px_rgba(168,85,247,0.1)]' 
                     : 'bg-white/[0.02] text-gray-500 border-white/[0.06] hover:bg-white/[0.05]'
                 }`}
                 title="Allow Heavy Models (e.g. Qwen 35B) — Will unload other models"
              >
                 <BrainCircuit className="w-3.5 h-3.5" />
                 <span className="hidden xl:inline">{allowHeavy ? 'Deep Think' : 'Fast Mode'}</span>
              </button>
            </div>
          </div>

          {/* Right controls */}
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-gray-600 font-mono hidden sm:block">{currentTime}</span>

            {/* Connection Status */}
            <ConnectionStatus health={health} />
            <div className={`flex items-center gap-1.5 px-2 py-1 rounded-lg border text-[10px] font-mono transition-all ${
              wsStatus === 'connected' ? 'bg-green-500/10 border-green-500/20 text-green-400' :
              wsStatus === 'connecting' ? 'bg-yellow-500/10 border-yellow-500/20 text-yellow-400' :
              'bg-red-500/10 border-red-500/20 text-red-400'
            }`}>
              <div className={`w-1.5 h-1.5 rounded-full ${wsStatus === 'connected' ? 'bg-green-400' : wsStatus === 'connecting' ? 'bg-yellow-400' : 'bg-red-400'} animate-pulse`} />
              <span className="hidden sm:inline">WS {wsStatus}</span>
            </div>

            <div className="flex items-center gap-2 bg-white/[0.03] border border-white/[0.06] px-2.5 py-1 rounded-lg text-[10px] font-mono">
              <span className="text-pink-400">{sysStats.total_runs} runs</span>
              <span className="text-white/10">|</span>
              <span className="text-green-400">{sysStats.success_rate}%</span>
            </div>

            <button
               onClick={handleClearLogs}
               className="flex items-center gap-1.5 px-2.5 py-1.5 bg-white/[0.03] hover:bg-white/[0.08] border border-white/[0.06] rounded-lg text-gray-400 hover:text-white text-[11px] font-bold transition-all"
            >
               Clear Logs
            </button>

            {/* Stop All Agents button - always visible */}
            <button
              onClick={handleStop}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-[11px] font-bold transition-all ${
                isSystemActive
                  ? 'bg-red-500/10 hover:bg-red-500/20 border-red-500/30 text-red-400 animate-pulse'
                  : 'bg-white/[0.03] hover:bg-red-500/10 border-white/[0.06] hover:border-red-500/20 text-gray-500 hover:text-red-400'
              }`}
              title="Stop all running agents"
            >
              <Square className="w-3 h-3 fill-current" /> Stop All
            </button>

            {/* Status indicator */}
            <div className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-[11px] font-bold transition-all ${
              isSystemActive
                ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400'
                : 'bg-white/[0.03] border-white/[0.06] text-gray-500'
            }`}>
              <div className={`w-1.5 h-1.5 rounded-full ${isSystemActive ? 'bg-cyan-400 animate-pulse' : 'bg-green-400'}`} />
              {isSystemActive ? 'Running' : 'Idle'}
            </div>
          </div>
        </div>

        {/* Content area with page transitions */}
        <div className="flex-1 flex overflow-hidden">
          <AnimatePresence mode="wait">
            {activeTab === 'chat' && (
              <motion.div
                key="chat"
                variants={pageVariants}
                initial="initial"
                animate="animate"
                exit="exit"
                transition={pageTransition}
                className="flex-1 flex"
              >
                <AgentChat />
              </motion.div>
            )}
            {activeTab === 'simple-chat' && (
              <motion.div
                key="simple-chat"
                variants={pageVariants}
                initial="initial"
                animate="animate"
                exit="exit"
                transition={pageTransition}
                className="flex-1 flex"
              >
                <SimpleChat />
              </motion.div>
            )}
            {activeTab === 'canvas' && (
              <motion.div
                key="canvas"
                variants={pageVariants}
                initial="initial"
                animate="animate"
                exit="exit"
                transition={pageTransition}
                className="flex-1 flex p-4 gap-4"
              >
                <AgentCanvas />
                <TimelinePanel executionLog={executionLog} />
              </motion.div>
            )}
            {activeTab === 'workspace' && (
              <motion.div
                key="workspace"
                variants={pageVariants}
                initial="initial"
                animate="animate"
                exit="exit"
                transition={pageTransition}
                className="flex-1 flex"
              >
                <WorkspaceExplorer />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
