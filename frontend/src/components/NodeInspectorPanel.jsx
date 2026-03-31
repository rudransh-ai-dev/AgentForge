import React from 'react';
import { useAgentStore } from '../store/useAgentStore';
import { X, Cpu, FileCode2, Clock, CheckCircle, Activity, FileWarning, Play } from 'lucide-react';

export default function NodeInspectorPanel() {
  const { selectedNodeId, nodesState, setSelectedNode, availableModels, configuredModels } = useAgentStore();
  
  if (!selectedNodeId || selectedNodeId === 'input') return null;

  const nodeData = nodesState[selectedNodeId];
  if (!nodeData) return null;

  return (
    <div className="absolute top-0 right-0 w-80 h-full bg-black/80 backdrop-blur-xl border-l border-white/10 p-5 shadow-2xl z-50 flex flex-col animate-in slide-in-from-right font-mono transition-transform duration-300">
      
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-cyan-400 font-bold uppercase tracking-widest text-sm flex items-center gap-2">
          {selectedNodeId === 'manager' ? <Cpu className="w-4 h-4" /> : <FileCode2 className="w-4 h-4" />}
          {selectedNodeId} Inspector
        </h2>
        <button onClick={() => setSelectedNode(null)} className="text-gray-500 hover:text-white transition-colors">
          <X className="w-5 h-5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar space-y-6 pr-2">
        
        {/* Engine Configuration (If applicable) */}
        {configuredModels[selectedNodeId] && (
          <div className="space-y-2">
            <h3 className="text-gray-500 text-[10px] uppercase tracking-wider flex items-center justify-between">
              Live Engine Configuration
            </h3>
            <div className="bg-[#050505] p-2.5 rounded border border-white/5 flex items-center gap-2">
              <Cpu className="w-3.5 h-3.5 text-cyan-500 shrink-0" />
              <select
                value={configuredModels[selectedNodeId]}
                onChange={async (e) => {
                  const newModel = e.target.value;
                  try {
                    await fetch('http://127.0.0.1:8888/config/models', {
                      method: 'PUT',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ [selectedNodeId]: newModel })
                    });
                    // Refresh configured models immediately
                    useAgentStore.getState().setConfiguredModels({
                      ...configuredModels,
                      [selectedNodeId]: newModel
                    });
                  } catch (err) {
                    console.error("Failed to swap engine", err);
                  }
                }}
                className="w-full bg-transparent text-[11px] text-cyan-100 font-semibold border-none outline-none cursor-pointer appearance-none truncate"
              >
                {availableModels.map(m => (
                  <option key={m} value={m} className="bg-[#111] text-gray-200">
                    {m}
                  </option>
                ))}
              </select>
            </div>
            <p className="text-[9px] text-gray-600 font-mono tracking-tighter mt-1">
              Changes apply instantly to the {selectedNodeId} agent logic.
            </p>
          </div>
        )}

        {/* Status */}
        <div className="space-y-2">
            <h3 className="text-gray-500 text-[10px] uppercase tracking-wider">Current State</h3>
            <div className={`px-3 py-1.5 rounded border inline-flex items-center gap-2 text-xs font-bold uppercase tracking-widest ${
              nodeData.status === 'running' ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400' : 
              nodeData.status === 'success' ? 'bg-green-500/10 border-green-500/30 text-green-400' :
              nodeData.status === 'error' ? 'bg-red-500/10 border-red-500/30 text-red-500' :
              'bg-white/5 border-white/10 text-gray-400'
            }`}>
              {nodeData.status === 'running' && <Activity className="w-3.5 h-3.5 animate-spin" />}
              {nodeData.status === 'success' && <CheckCircle className="w-3.5 h-3.5" />}
              {nodeData.status === 'error' && <FileWarning className="w-3.5 h-3.5" />}
              {nodeData.status}
            </div>
        </div>

        {/* System Prompt / Input */}
        <div className="space-y-2">
            <h3 className="text-gray-500 text-[10px] uppercase tracking-wider">Input Event</h3>
            <div className="bg-[#050505] p-3 rounded border border-white/5 text-[11px] text-gray-300 whitespace-pre-wrap break-words max-h-40 overflow-y-auto custom-scrollbar">
              {nodeData.input || "No input received yet."}
            </div>
        </div>

        {/* Streaming Output */}
        <div className="space-y-2">
            <h3 className="text-gray-500 text-[10px] uppercase tracking-wider">Live Output Buffer</h3>
            <div className={`bg-[#050505] p-3 rounded border text-[11px] whitespace-pre-wrap break-words min-h-[100px] max-h-64 overflow-y-auto custom-scrollbar ${nodeData.status === 'error' ? 'border-red-500/30 text-red-400' : 'border-white/5 text-cyan-100'}`}>
              {nodeData.error ? (
                  <div className="flex items-start gap-2">
                    <FileWarning className="w-4 h-4 mt-0.5 shrink-0" />
                    <span>{nodeData.error}</span>
                  </div>
              ) : nodeData.output ? (
                  selectedNodeId === 'manager' && nodeData.output.startsWith('{') ? (
                    <pre className="text-[10px] text-blue-300">
                        {(() => {
                            try { return JSON.stringify(JSON.parse(nodeData.output), null, 2); }
                            catch { return nodeData.output; }
                        })()}
                    </pre>
                  ) : nodeData.output
              ) : (
                  <span className="text-gray-600 animate-pulse">Waiting for matrix stream...</span>
              )}
            </div>
        </div>

        {/* Metadata */}
        {(nodeData.metadata?.latency_ms || nodeData.metadata?.tokens) && (
          <div className="space-y-2 pt-2 border-t border-white/5">
              <h3 className="text-gray-500 text-[10px] uppercase tracking-wider">Execution Metadata</h3>
              <div className="grid grid-cols-2 gap-2 text-[10px] text-gray-400">
                 <div className="bg-white/5 rounded p-2 border border-white/5 flex flex-col items-center">
                    <span className="text-gray-600 mb-1">Time to final token</span>
                    <span className="text-white font-bold tracking-wider flex items-center gap-1.5"><Clock className="w-3 h-3"/> {nodeData.metadata.latency_ms}ms</span>
                 </div>
                 <div className="bg-white/5 rounded p-2 border border-white/5 flex flex-col items-center">
                    <span className="text-gray-600 mb-1">Total Tokens</span>
                    <span className="text-white font-bold tracking-wider">{nodeData.metadata.tokens} tks</span>
                 </div>
                 {nodeData.metadata.confidence && (
                     <div className="bg-white/5 rounded p-2 border border-white/5 flex flex-col items-center col-span-2 mt-1">
                        <span className="text-gray-600 mb-1">Manager Confidence</span>
                        <span className="text-white font-bold tracking-wider text-green-400">{Math.round(nodeData.metadata.confidence * 100)}% Match</span>
                     </div>
                 )}
              </div>
          </div>
        )}
      </div>
    </div>
  );
}
