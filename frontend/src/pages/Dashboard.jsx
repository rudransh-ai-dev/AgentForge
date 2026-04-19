import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Terminal, Activity, Search, Cpu, Zap, BrainCircuit, Network,
  FolderTree, Clock, Wifi, MessageSquare, MessageCircle, Square, WifiOff,
  AlertTriangle, CheckCircle2, Loader2, PanelLeftClose, PanelLeft, BarChart3, Users
} from 'lucide-react';
import AgentCanvas from '../components/AgentCanvas';
import WorkspaceExplorer from '../components/WorkspaceExplorer';
import SimpleChat from '../components/SimpleChat';
import VoiceButton from '../components/VoiceButton';
import AgentChat from '../components/AgentChat';
import TimelinePanel from '../components/TimelinePanel';
import StatusBar from '../components/StatusBar';
import PerformanceDashboard from '../components/PerformanceDashboard';
import CustomAgentManager from '../components/CustomAgentManager';
import NodeSidebar from '../components/NodeSidebar';
import TopClock from '../components/TopClock';
import { useAgentStore } from '../store/useAgentStore';

const API = "";

const pageVariants = {
  initial: { opacity: 0, y: 4 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -4 },
};
const pageTransition = { duration: 0.15, ease: [0.4, 0, 0.2, 1] };

function ConnectionStatus({ health, wsStatus }) {
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
    connected: { icon: <Wifi className="w-3 h-3" />, color: 'text-success', bg: 'bg-success/10', border: 'border-success/20', label: 'Ollama' },
    disconnected: { icon: <WifiOff className="w-3 h-3" />, color: 'text-danger', bg: 'bg-danger/10', border: 'border-danger/20', label: 'Offline' },
    checking: { icon: <Loader2 className="w-3 h-3 animate-spin" />, color: 'text-attention', bg: 'bg-attention/10', border: 'border-attention/20', label: 'Checking' },
  };
  const s = statusMap[health.ollama] || statusMap.checking;

  return (
    <div className="relative" ref={popoverRef}>
      <button
        onClick={() => setShowModels(!showModels)}
        className={`flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium ${s.bg} border ${s.border} ${s.color} transition-colors cursor-pointer`}
      >
        {s.icon}
        <span className="hidden sm:inline">{wsStatus === 'connecting' ? 'WS Connecting' : wsStatus === 'disconnected' ? 'WS Offline' : s.label}</span>
        {health.models?.length > 0 && (
          <span className="text-fgSubtle hidden md:inline">({health.models.length})</span>
        )}
      </button>

      <AnimatePresence>
        {showModels && (
          <motion.div
            initial={{ opacity: 0, y: 4, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 4, scale: 0.98 }}
            transition={{ duration: 0.1 }}
            className="absolute top-full right-0 mt-1 w-72 bg-canvasSubtle border border-borderDefault rounded-md shadow-dropdown z-50 overflow-hidden"
          >
            <div className="px-3 py-2 border-b border-borderDefault">
              <span className="text-xs font-semibold text-fgDefault flex items-center gap-2">
                <Cpu className="w-3.5 h-3.5 text-accent" />
                Available Models
              </span>
            </div>

            <div className="p-1.5 max-h-[300px] overflow-y-auto">
              {health.models?.length > 0 ? (
                health.models.map((model, idx) => (
                  <div
                    key={idx}
                    className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-canvas text-xs text-fgDefault transition-colors"
                  >
                    <span className="text-fgSubtle font-mono w-5 text-right">{idx + 1}</span>
                    <span className="truncate">{model}</span>
                    <div className="ml-auto w-1.5 h-1.5 rounded-full bg-success" />
                  </div>
                ))
              ) : (
                <div className="py-8 text-center text-xs text-fgSubtle">No models found</div>
              )}
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
  const [activeTab, setActiveTab] = useState('chat');
  const [sidebarExpanded, setSidebarExpanded] = useState(false);
  const [sidebarPinned, setSidebarPinned] = useState(false);
  const [execMode, setExecMode] = useState('auto');
  const [allowHeavy, setAllowHeavy] = useState(false);
  const [timelineWidth, setTimelineWidth] = useState(340);
  const [isResizingTimeline, setIsResizingTimeline] = useState(false);
  const [canvasFullscreen, setCanvasFullscreen] = useState(false);
  const searchInputRef = React.useRef(null);

  const { nodesState, executionLog, projects, canvasRuns, setCanvasRuns, chatSessions, setChatSessions } = useAgentStore();
  const isSystemActive = Object.values(nodesState).some(n => n?.status === 'running');

  const wsRef = useRef(null);
  const [wsStatus, setWsStatus] = useState('disconnected');
  const storeRef = useRef({ updateNode: null, addTimelineEvent: null });
  storeRef.current.updateNode = useAgentStore.getState().updateNode;
  storeRef.current.addTimelineEvent = useAgentStore.getState().addTimelineEvent;

  useEffect(() => {
    if (!isResizingTimeline) return;
    
    const handleMouseMove = (e) => {
      const newWidth = document.body.clientWidth - e.clientX - 16;
      if (newWidth >= 250 && newWidth <= 800) {
        setTimelineWidth(newWidth);
      }
    };
    
    const handleMouseUp = () => {
      setIsResizingTimeline(false);
    };
    
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizingTimeline]);

  useEffect(() => {
    let ws;
    let reconnectTimer;
    let pingTimer;

    const connect = () => {
      setWsStatus('connecting');
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws/agent-stream`);
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
            const existing = useAgentStore.getState().nodesState[node_id];
            if (existing?.status !== 'success') {
              storeRef.current.updateNode(run_id, node_id, { output });
            }
          } else if (type === 'complete') {
            storeRef.current.updateNode(run_id, node_id, { status: 'success', output, metadata: metadata || {} });
          } else if (type === 'error') {
            storeRef.current.updateNode(run_id, node_id, { status: 'error', error });
          } else if (type === 'run_complete') {
            // Reset any nodes still stuck in "running" to idle
            const currentNodes = useAgentStore.getState().nodesState;
            Object.entries(currentNodes).forEach(([nid, ns]) => {
              if (ns?.status === 'running') {
                storeRef.current.updateNode(run_id, nid, { status: 'idle' });
              }
            });
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
      if (ws && ws.readyState !== WebSocket.CONNECTING && ws.readyState !== WebSocket.CLOSED && ws.readyState !== WebSocket.CLOSING) {
        ws.onclose = null;
        ws.close();
      }
      wsRef.current = null;
    };
  }, []);

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

  // Load custom agents into global store so NodeSidebar + AgentChat can use them
  useEffect(() => {
    const loadCustomAgents = async () => {
      try {
        const res = await fetch(`${API}/custom-agents`);
        const data = await res.json();
        useAgentStore.getState().setCustomAgents(data.agents || []);
      } catch { }
    };
    loadCustomAgents();
    const interval = setInterval(loadCustomAgents, 30000);
    return () => clearInterval(interval);
  }, []);

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

  useEffect(() => {
    const loadHistory = async () => {
      try {
        const [canvasRes, chatRes] = await Promise.all([
          fetch(`${API}/canvas/runs?limit=20`).then(r => r.json()).catch(() => ({ runs: [] })),
          fetch(`${API}/chat/sessions?limit=20`).then(r => r.json()).catch(() => ({ sessions: [] })),
        ]);
        setCanvasRuns(canvasRes.runs || []);
        setChatSessions(chatRes.sessions || []);
      } catch (e) { }
    };
    loadHistory();
    const interval = setInterval(loadHistory, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleQuery = async (e) => {
    if (e.key === 'Enter' && query.trim() !== '') {
      const prompt = query;
      setQuery('');
      setIsProcessing(true);
      try {
        // Collect per-node model overrides from canvas (set via node config panel)
        const nodeModels = useAgentStore.getState().canvasNodeModels || {};

        await fetch(`${API}/run`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            prompt,
            mode: execMode,
            allow_heavy: allowHeavy,
            node_models: Object.keys(nodeModels).length > 0 ? nodeModels : undefined,
          })
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

  const handleClearLogs = () => {
    useAgentStore.getState().clearExecutionLog();
  };

  const TABS = useMemo(() => [
    { id: 'chat', icon: <MessageSquare className="w-4 h-4" />, label: 'Agent Chat' },
    { id: 'simple-chat', icon: <MessageCircle className="w-4 h-4" />, label: 'Chat' },
    { id: 'canvas', icon: <Network className="w-4 h-4" />, label: 'Canvas' },
    { id: 'workspace', icon: <FolderTree className="w-4 h-4" />, label: 'Files', badge: projects.length || null },
    { id: 'performance', icon: <BarChart3 className="w-4 h-4" />, label: 'Metrics' },
    { id: 'custom-agents', icon: <Users className="w-4 h-4" />, label: 'Agents' },
  ], [projects.length]);

  const isSidebarVisible = sidebarExpanded || sidebarPinned;

  return (
    <div className="flex flex-col h-screen gradient-bg-animated text-fgDefault relative overflow-hidden font-sans grain">
      {/* Ambient floating orbs — sit behind everything */}
      <div className="ambient-orb ambient-orb-1" />
      <div className="ambient-orb ambient-orb-2" />
      <div className="ambient-orb ambient-orb-3" />

      {/* ══════════════════════════════════════════════════════
          FULL-WIDTH TOP DOCK
          ══════════════════════════════════════════════════════ */}
      <div className="h-14 flex items-center gap-3 px-4 glass-strong shrink-0 relative z-40">
        <div className="aurora-line absolute bottom-0 left-0 right-0" />

        {/* Brand — always visible on the left */}
        <div className="flex items-center gap-2.5 shrink-0 pr-3 mr-1 border-r" style={{ borderColor: 'var(--stroke-1)' }}>
          <motion.div
            className="p-2 rounded-xl shrink-0 relative"
            style={{
              background: 'linear-gradient(135deg, rgba(88,166,255,0.18), rgba(163,113,247,0.12))',
              border: '1px solid rgba(88,166,255,0.3)',
              boxShadow: '0 0 20px rgba(88,166,255,0.25), inset 0 1px 0 rgba(255,255,255,0.1)',
            }}
            animate={isSystemActive ? { scale: [1, 1.08, 1], rotate: [0, 3, -3, 0] } : {}}
            transition={{ duration: 2.4, repeat: Infinity, ease: 'easeInOut' }}
          >
            <BrainCircuit className="text-accent w-4 h-4" />
          </motion.div>
          <div className="flex flex-col leading-tight">
            <h1 className="text-base font-bold text-gradient-premium whitespace-nowrap">
              AgentForge
            </h1>
            <span className="text-[9px] text-fgSubtle whitespace-nowrap uppercase tracking-[0.15em] font-medium">
              Multi-Agent IDE
            </span>
          </div>
        </div>

        <div className="flex-1 max-w-2xl flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-fgSubtle" />
            <input
              ref={searchInputRef}
              name="command-input"
              id="command-input"
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleQuery}
              disabled={isProcessing || isSystemActive}
              placeholder={isSystemActive ? "Processing..." : "Run a task... (Ctrl+K)"}
              className="w-full bg-canvas/50 border border-borderDefault/50 rounded-lg py-1.5 pl-9 pr-14 text-sm text-fgDefault placeholder-fgSubtle focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/20 disabled:opacity-40 transition-all focus:shadow-[0_0_16px_rgba(88,166,255,0.2)]"
            />
            <div className="absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none">
              <span className="text-[10px] font-mono bg-canvasSubtle/50 border border-borderDefault/50 text-fgSubtle px-1.5 py-0.5 rounded">Ctrl+K</span>
            </div>
          </div>

          <VoiceButton
            onTranscript={(text) => setQuery((prev) => prev ? prev + ' ' + text : text)}
            disabled={isProcessing || isSystemActive}
          />

          <div className="flex items-center gap-1 shrink-0">
            <div className="flex items-center bg-canvas/50 border border-borderDefault/50 rounded-lg p-0.5">
              {['auto', 'direct', 'agent'].map(mode => (
                <motion.button
                  key={mode}
                  onClick={() => setExecMode(mode)}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className={`px-2.5 py-1 text-[11px] font-medium rounded-md transition-all ${
                    execMode === mode
                      ? 'bg-gradient-to-r from-accent/20 to-accent/5 text-accent shadow-sm'
                      : 'text-fgSubtle hover:text-fgDefault hover:bg-canvasSubtle/50'
                  }`}
                  title={`Run in ${mode} mode`}
                >
                  {mode}
                </motion.button>
              ))}
            </div>

            <motion.button
              onClick={() => setAllowHeavy(!allowHeavy)}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 text-[11px] font-medium rounded-lg border transition-all shrink-0 ${
                allowHeavy
                  ? 'bg-gradient-to-r from-done/15 to-done/5 text-done border-done/20 glow-accent'
                  : 'bg-canvas/50 text-fgSubtle border-borderDefault/50 hover:bg-canvasSubtle/50'
              }`}
              title="Allow Heavy Models"
            >
              <BrainCircuit className="w-3.5 h-3.5" />
              <span className="hidden xl:inline">{allowHeavy ? 'Deep Think' : 'Fast'}</span>
            </motion.button>
          </div>
        </div>

        <div className="flex-1" />

        <div className="flex items-center gap-2 shrink-0">
          <TopClock />
          <ConnectionStatus health={health} wsStatus={wsStatus} />



          <motion.button
            onClick={handleClearLogs}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="flex items-center gap-1 px-2 py-1 bg-canvas/50 hover:bg-canvasSubtle/50 border border-borderDefault/50 rounded-lg text-fgSubtle hover:text-fgDefault text-xs transition-colors"
          >
            Clear
          </motion.button>

          <motion.button
            onClick={handleStop}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-xs font-medium transition-all ${
              isSystemActive
                ? 'bg-gradient-to-r from-danger/15 to-danger/5 hover:from-danger/20 hover:to-danger/10 border-danger/20 text-danger glow-danger'
                : 'bg-canvas/50 hover:bg-danger/10 border-borderDefault/50 hover:border-danger/20 text-fgSubtle hover:text-danger'
            }`}
            title="Stop all running agents"
          >
            <Square className="w-3 h-3 fill-current" /> Stop
          </motion.button>
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════
          SIDEBAR + CONTENT ROW
          ══════════════════════════════════════════════════════ */}
      <div className="flex flex-1 min-h-0 relative">

      <motion.div
        className="flex flex-col glass-strong border-r relative z-30 shrink-0"
        style={{ borderColor: 'var(--stroke-2)' }}
        animate={{ width: isSidebarVisible ? 220 : 56 }}
        transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
        onMouseEnter={() => !sidebarPinned && setSidebarExpanded(true)}
        onMouseLeave={() => !sidebarPinned && setSidebarExpanded(false)}
      >
        <div className="flex-1 flex flex-col px-2 py-3 overflow-y-auto">
          <div className="space-y-0.5 mb-2">
            {TABS.map((tab) => (
              <motion.button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                whileHover={{ x: isSidebarVisible ? 2 : 0, scale: isSidebarVisible ? 1 : 1.08 }}
                whileTap={{ scale: 0.95 }}
                className={`w-full flex items-center ${isSidebarVisible ? 'justify-start gap-2.5 px-2.5' : 'justify-center px-0'} h-10 rounded-lg text-sm transition-all relative ${activeTab === tab.id
                    ? 'bg-gradient-to-r from-accent/20 to-accent/5 text-accent font-medium glow-accent'
                    : 'text-fgMuted hover:text-fgDefault hover:bg-canvas/50'
                  }`}
                title={!isSidebarVisible ? tab.label : undefined}
              >
                <motion.span
                  className={`shrink-0 flex items-center justify-center ${activeTab === tab.id ? 'text-accent' : ''}`}
                  animate={activeTab === tab.id ? { filter: 'drop-shadow(0 0 6px rgba(88,166,255,0.5))' } : {}}
                >
                  {tab.icon}
                </motion.span>
                <AnimatePresence>
                  {isSidebarVisible && (
                    <motion.span
                      initial={{ opacity: 0, width: 0 }}
                      animate={{ opacity: 1, width: 'auto' }}
                      exit={{ opacity: 0, width: 0 }}
                      transition={{ duration: 0.15 }}
                      className="whitespace-nowrap overflow-hidden text-xs"
                    >
                      {tab.label}
                      {tab.badge && (
                        <span className="ml-1.5 bg-accent/15 text-accent text-[10px] px-1.5 py-0.5 rounded-full font-mono font-bold">
                          {tab.badge}
                        </span>
                      )}
                    </motion.span>
                  )}
                </AnimatePresence>
                {activeTab === tab.id && (
                  <motion.div
                    layoutId="activeTab"
                    className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-accent rounded-r-full"
                    transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                  />
                )}
              </motion.button>
            ))}
          </div>
        </div>

        <div className="p-2 border-t border-borderDefault/50">
          <button
            onClick={() => setSidebarPinned(!sidebarPinned)}
            className="w-full flex items-center justify-center gap-2 py-1.5 rounded-md hover:bg-canvas/50 text-fgSubtle hover:text-fgDefault transition-colors"
            title={sidebarPinned ? "Unpin sidebar" : "Pin sidebar"}
          >
            {sidebarPinned ? <PanelLeftClose className="w-3.5 h-3.5" /> : <PanelLeft className="w-3.5 h-3.5" />}
            <AnimatePresence>
              {isSidebarVisible && (
                <motion.span
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="text-xs whitespace-nowrap"
                >
                  {sidebarPinned ? 'Unpin' : 'Pin'}
                </motion.span>
              )}
            </AnimatePresence>
          </button>
        </div>
      </motion.div>

      <div className="flex-1 flex flex-col min-w-0 relative z-10">
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
                className="flex-1 flex p-2 h-full gap-2 relative"
              >
                <NodeSidebar />
                <div className="flex-1 min-w-0 pb-1">
                  <AgentCanvas isFullscreen={canvasFullscreen} setIsFullscreen={setCanvasFullscreen} />
                </div>
                
                {/* Resizer Handle */}
                <div 
                  className="w-3 cursor-col-resize hover:bg-accent/10 active:bg-accent/20 transition-colors z-10 flex items-center justify-center group rounded-full"
                  onMouseDown={(e) => {
                    e.preventDefault();
                    setIsResizingTimeline(true);
                  }}
                >
                  <div className={`w-[2px] h-12 rounded-full transition-colors ${isResizingTimeline ? 'bg-accent' : 'bg-[#30363d] group-hover:bg-[#58a6ff]'}`} />
                </div>

                <div style={{ width: timelineWidth }} className="shrink-0 flex flex-col pb-1">
                  <TimelinePanel executionLog={executionLog} />
                </div>
                
                {isResizingTimeline && <div className="fixed inset-0 z-50 cursor-col-resize" />}
              </motion.div>
            )}

            {/* Fullscreen Canvas Overlay */}
            {canvasFullscreen && (
              <div className="fixed inset-0 z-[100] bg-[#0d1117] flex p-2 gap-2">
                <NodeSidebar />
                <div className="flex-1 min-w-0">
                  <AgentCanvas isFullscreen={canvasFullscreen} setIsFullscreen={setCanvasFullscreen} />
                </div>
              </div>
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
            {activeTab === 'performance' && (
              <motion.div
                key="performance"
                variants={pageVariants}
                initial="initial"
                animate="animate"
                exit="exit"
                transition={pageTransition}
                className="flex-1 flex"
              >
                <PerformanceDashboard />
              </motion.div>
            )}
            {activeTab === 'custom-agents' && (
              <motion.div
                key="custom-agents"
                variants={pageVariants}
                initial="initial"
                animate="animate"
                exit="exit"
                transition={pageTransition}
                className="flex-1 flex"
              >
                <CustomAgentManager />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      </div> {/* /sidebar+content row */}

      <StatusBar health={health} wsStatus={wsStatus} sysStats={sysStats} isSystemActive={isSystemActive} />
    </div>
  );
}
