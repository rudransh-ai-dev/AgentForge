import React, { useState, useEffect, useRef } from 'react';
import { Activity, ChevronDown, ChevronRight, Clock, CheckCircle, XCircle, Zap, RefreshCw, Trash2 } from 'lucide-react';
import { useAgentStore } from '../store/useAgentStore';

const API = "http://127.0.0.1:8888";

const nodeColors = {
  manager: '#58a6ff',
  coder: '#a371f7',
  analyst: '#3fb950',
  critic: '#d29922',
  tool: '#db61a2',
  executor: '#58a6ff',
  system: '#6e7681',
};

const eventIcon = (type) => {
  if (type === 'complete') return <CheckCircle className="w-3 h-3 text-[#3fb950]" />;
  if (type === 'error') return <XCircle className="w-3 h-3 text-[#f85149]" />;
  if (type === 'start') return <Zap className="w-3 h-3 text-[#d29922]" />;
  return <Activity className="w-3 h-3 text-[#58a6ff] animate-spin" />;
};

export default function TimelinePanel({ executionLog }) {
  const { activeRunId, clearExecutionLog } = useAgentStore();
  const [historicalRuns, setHistoricalRuns] = useState([]);
  const [expandedRuns, setExpandedRuns] = useState({});
  const [runSteps, setRunSteps] = useState({});
  const scrollRef = useRef(null);

  useEffect(() => {
    if (!activeRunId) {
      fetch(`${API}/canvas/runs?limit=10`)
        .then(r => r.json())
        .then(data => setHistoricalRuns(data.runs || []))
        .catch(() => {});
    }
  }, [activeRunId]);

  // Auto-scroll to bottom on new events
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [executionLog.length]);

  const toggleRun = async (runId) => {
    if (expandedRuns[runId]) {
      setExpandedRuns(prev => ({ ...prev, [runId]: false }));
      return;
    }
    if (!runSteps[runId]) {
      try {
        const res = await fetch(`${API}/canvas/runs/${runId}/steps`);
        const data = await res.json();
        setRunSteps(prev => ({ ...prev, [runId]: data.steps || [] }));
      } catch {
        setRunSteps(prev => ({ ...prev, [runId]: [] }));
      }
    }
    setExpandedRuns(prev => ({ ...prev, [runId]: true }));
  };

  const liveLog = executionLog.filter(log => log.type !== 'update');
  const nodeColor = (nodeId) => nodeColors[nodeId] || '#6e7681';

  return (
    <div className="h-full flex flex-col glass-strong border border-[#30363d]/50 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="px-3 py-2 border-b border-[#21262d] flex items-center gap-2 shrink-0">
        <Activity className="w-3.5 h-3.5 text-[#58a6ff]" />
        <span className="font-semibold text-[#c9d1d9] text-xs">Timeline</span>
        <span className="ml-auto text-[9px] text-[#6e7681] font-mono bg-[#161b22] px-1.5 py-0.5 rounded">
          {liveLog.length} events
        </span>
        {!activeRunId && (
          <button
            onClick={() => fetch(`${API}/canvas/runs?limit=10`).then(r=>r.json()).then(d=>setHistoricalRuns(d.runs||[])).catch(()=>{})}
            className="p-0.5 text-[#6e7681] hover:text-[#c9d1d9] transition-colors"
            title="Refresh history"
          >
            <RefreshCw className="w-3 h-3" />
          </button>
        )}
        <button
          onClick={() => { clearExecutionLog(); setHistoricalRuns([]); setExpandedRuns({}); setRunSteps({}); }}
          className="p-0.5 text-[#6e7681] hover:text-[#f85149] transition-colors"
          title="Clear timeline"
        >
          <Trash2 className="w-3 h-3" />
        </button>
      </div>

      {/* Content */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-2 space-y-1.5">
        {activeRunId && liveLog.length > 0 ? (
          [...liveLog].reverse().slice(0, 60).map((log, i) => (
            <div
              key={log.event_id || i}
              className="rounded-md border border-[#21262d] bg-[#0d1117]/60 hover:border-[#30363d] transition-all overflow-hidden"
            >
              {/* Event header */}
              <div className="flex items-center gap-2 px-2.5 py-1.5">
                {eventIcon(log.type)}
                <span
                  className="text-[10px] font-semibold uppercase tracking-wider"
                  style={{ color: nodeColor(log.node_id) }}
                >
                  {log.node_id}
                </span>
                <span className={`ml-auto text-[8px] uppercase tracking-wider font-medium px-1 py-0.5 rounded ${
                  log.type === 'complete' ? 'text-[#3fb950] bg-[#3fb950]/10' :
                  log.type === 'error' ? 'text-[#f85149] bg-[#f85149]/10' :
                  log.type === 'start' ? 'text-[#d29922] bg-[#d29922]/10' :
                  'text-[#58a6ff] bg-[#58a6ff]/10'
                }`}>
                  {log.type}
                </span>
                <span className="text-[9px] text-[#484f58] font-mono ml-1">
                  {new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>
              </div>

              {/* Event body */}
              {(log.output || log.input || log.error) && (
                <div className="px-2.5 pb-2 text-[10px] font-mono text-[#8b949e] leading-relaxed max-h-24 overflow-y-auto border-t border-[#161b22]">
                  <p className="whitespace-pre-wrap break-words pt-1.5">
                    {log.error
                      ? <span className="text-[#f85149]">{String(log.error).slice(0, 300)}</span>
                      : String(log.output || log.input || '').slice(0, 300)
                    }
                  </p>
                </div>
              )}

              {/* Metadata */}
              {log.metadata && (log.metadata.latency_ms || log.metadata.model) && (
                <div className="flex items-center gap-2 px-2.5 py-1 border-t border-[#161b22] text-[9px] text-[#484f58] font-mono">
                  {log.metadata.latency_ms && (
                    <span className="flex items-center gap-0.5">
                      <Clock className="w-2.5 h-2.5" /> {log.metadata.latency_ms}ms
                    </span>
                  )}
                  {log.metadata.model && (
                    <span className="truncate">{log.metadata.model}</span>
                  )}
                  {log.metadata.route && (
                    <span className="ml-auto text-[#6e7681]">→ {log.metadata.route}</span>
                  )}
                </div>
              )}
            </div>
          ))
        ) : historicalRuns.length > 0 ? (
          <div className="space-y-1">
            <p className="text-[9px] text-[#484f58] uppercase tracking-wider px-1 pt-1 pb-1.5 font-medium">Run History</p>
            {historicalRuns.map(run => (
              <div key={run.run_id} className="rounded-md border border-[#21262d] overflow-hidden">
                <button
                  onClick={() => toggleRun(run.run_id)}
                  className="w-full flex items-center gap-1.5 px-2.5 py-2 hover:bg-[#161b22] text-xs text-[#c9d1d9] text-left transition-colors"
                >
                  {expandedRuns[run.run_id]
                    ? <ChevronDown className="w-3 h-3 text-[#6e7681] shrink-0" />
                    : <ChevronRight className="w-3 h-3 text-[#6e7681] shrink-0" />}
                  <span className="truncate flex-1 text-[11px] text-[#8b949e]">
                    {run.prompt?.slice(0, 55) || 'No prompt'}
                  </span>
                  <span className={`text-[8px] px-1.5 py-0.5 rounded shrink-0 ${
                    run.status === 'success' ? 'text-[#3fb950] bg-[#3fb950]/10 border border-[#3fb950]/20' :
                    run.status === 'error' ? 'text-[#f85149] bg-[#f85149]/10 border border-[#f85149]/20' :
                    'text-[#6e7681] bg-[#21262d]'
                  }`}>{run.status}</span>
                </button>
                {expandedRuns[run.run_id] && (
                  <div className="border-t border-[#161b22] bg-[#0d1117]/40">
                    {runSteps[run.run_id]?.length > 0 ? (
                      runSteps[run.run_id].map(step => (
                        <div key={step.id} className="flex items-start gap-2 px-3 py-1.5 text-[9px] border-b border-[#161b22] last:border-0">
                          <div className={`w-1.5 h-1.5 rounded-full mt-0.5 shrink-0 ${
                            step.status === 'success' ? 'bg-[#3fb950]' :
                            step.status === 'error' ? 'bg-[#f85149]' :
                            'bg-[#6e7681]'
                          }`} />
                          <div className="flex-1 min-w-0">
                            <span className="font-medium text-[#8b949e]" style={{ color: nodeColor(step.node_id) }}>
                              {step.node_id}
                            </span>
                            <span className="text-[#484f58] ml-1.5 truncate block">
                              {(step.output || step.input || '').slice(0, 80)}
                            </span>
                          </div>
                          {step.latency_ms && (
                            <span className="text-[#484f58] shrink-0">{step.latency_ms}ms</span>
                          )}
                        </div>
                      ))
                    ) : (
                      <div className="px-3 py-2 text-[9px] text-[#484f58]">No steps recorded</div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full gap-2 text-[#484f58]">
            <Activity className="w-6 h-6 opacity-30" />
            <span className="text-xs">No events yet</span>
            <span className="text-[10px] text-center">Run a task to see the live execution timeline here</span>
          </div>
        )}
      </div>
    </div>
  );
}
