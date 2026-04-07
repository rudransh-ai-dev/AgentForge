import React from 'react';
import { X, Cpu, FileCode2, Clock, CheckCircle, Activity, FileWarning } from 'lucide-react';
import { useAgentStore } from '../store/useAgentStore';

export default function NodeInspectorPanel() {
  const { selectedNodeId, nodesState, setSelectedNode, availableModels, configuredModels } = useAgentStore();

  if (!selectedNodeId || selectedNodeId === 'input') return null;

  const nodeData = nodesState[selectedNodeId];
  if (!nodeData) return null;

  return (
    <div className="absolute top-0 right-0 w-80 h-full bg-[#161b22]/95 backdrop-blur-xl border-l border-[#30363d]/50 p-4 shadow-[0_1px_3px_rgba(0,0,0,0.3),_0_1px_2px_rgba(0,0,0,0.4)] z-50 flex flex-col">
      <div className="flex justify-between items-center mb-4">
        <h2 className="bg-clip-text text-transparent bg-gradient-to-r from-[#58a6ff] to-[#a371f7] font-semibold text-sm flex items-center gap-2">
          {selectedNodeId === 'manager' ? <Cpu className="w-4 h-4" /> : <FileCode2 className="w-4 h-4" />}
          {selectedNodeId}
        </h2>
        <button onClick={() => setSelectedNode(null)} className="text-[#484f58] hover:text-[#c9d1d9] transition-colors">
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto space-y-4 pr-1">
        {configuredModels[selectedNodeId] && (
          <div className="space-y-1.5">
            <h3 className="text-[#484f58] text-[10px] uppercase tracking-wider font-medium">Model</h3>
            <div className="bg-[#161b22]/80 backdrop-blur-md p-2 rounded border border-[#30363d]/50 flex items-center gap-2">
              <Cpu className="w-3.5 h-3.5 text-[#58a6ff] shrink-0" />
              <select
                value={configuredModels[selectedNodeId]}
                onChange={async (e) => {
                  const newModel = e.target.value;
                  try {
                    await fetch('/config/models', {
                      method: 'PUT',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ [selectedNodeId]: newModel })
                    });
                    useAgentStore.getState().setConfiguredModels({
                      ...configuredModels,
                      [selectedNodeId]: newModel
                    });
                  } catch (err) {
                    console.error("Failed to swap engine", err);
                  }
                }}
                className="w-full bg-transparent text-xs text-[#c9d1d9] border-none outline-none cursor-pointer appearance-none truncate"
              >
                {availableModels.map(m => (
                  <option key={m} value={m} className="bg-[#161b22] text-[#c9d1d9]">
                    {m}
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}

        <div className="space-y-1.5">
          <h3 className="text-[#484f58] text-[10px] uppercase tracking-wider font-medium">Status</h3>
          <div className={`px-2 py-1 rounded border inline-flex items-center gap-1.5 text-xs font-medium ${
            nodeData.status === 'running' ? 'bg-[#58a6ff]/10 border-[#58a6ff]/20 text-[#58a6ff]' :
            nodeData.status === 'success' ? 'bg-[#3fb950]/10 border-[#3fb950]/20 text-[#3fb950]' :
            nodeData.status === 'error' ? 'bg-[#f85149]/10 border-[#f85149]/20 text-[#f85149]' :
            'bg-[#0d1117]/50 border-[#30363d]/50 text-[#484f58]'
          }`}>
            {nodeData.status === 'running' && <Activity className="w-3 h-3 animate-spin" />}
            {nodeData.status === 'success' && <CheckCircle className="w-3 h-3" />}
            {nodeData.status === 'error' && <FileWarning className="w-3 h-3" />}
            {nodeData.status}
          </div>
        </div>

        <div className="space-y-1.5">
          <h3 className="text-[#484f58] text-[10px] uppercase tracking-wider font-medium">Input</h3>
          <div className="bg-[#161b22]/80 backdrop-blur-md p-2.5 rounded border border-[#30363d]/50 text-xs text-[#c9d1d9] whitespace-pre-wrap break-words max-h-32 overflow-y-auto">
            {nodeData.input || "No input received yet."}
          </div>
        </div>

        <div className="space-y-1.5">
          <h3 className="text-[#484f58] text-[10px] uppercase tracking-wider font-medium">Output</h3>
          <div className={`bg-[#161b22]/80 backdrop-blur-md p-2.5 rounded border text-xs whitespace-pre-wrap break-words min-h-[80px] max-h-48 overflow-y-auto ${nodeData.status === 'error' ? 'border-[#f85149]/20 text-[#f85149]' : 'border-[#30363d]/50 text-[#c9d1d9]'}`}>
            {nodeData.error ? (
              <div className="flex items-start gap-1.5">
                <FileWarning className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                <span>{nodeData.error}</span>
              </div>
            ) : nodeData.output ? (
              selectedNodeId === 'manager' && nodeData.output.startsWith('{') ? (
                <pre className="text-[11px] text-[#58a6ff]">
                  {(() => {
                    try { return JSON.stringify(JSON.parse(nodeData.output), null, 2); }
                    catch { return nodeData.output; }
                  })()}
                </pre>
              ) : nodeData.output
            ) : (
              <span className="text-[#484f58] animate-pulse">Waiting for output...</span>
            )}
          </div>
        </div>

        {(nodeData.metadata?.latency_ms || nodeData.metadata?.tokens) && (
          <div className="space-y-1.5 pt-2 border-t border-[#30363d]/50">
            <h3 className="text-[#484f58] text-[10px] uppercase tracking-wider font-medium">Metadata</h3>
            <div className="grid grid-cols-2 gap-2 text-[11px] text-[#8b949e]">
              <div className="bg-[#161b22]/80 backdrop-blur-md rounded p-2 border border-[#30363d]/30 flex flex-col items-center">
                <span className="text-[#484f58] mb-1 text-[10px]">Latency</span>
                <span className="text-[#c9d1d9] font-medium flex items-center gap-1"><Clock className="w-3 h-3"/> {nodeData.metadata.latency_ms}ms</span>
              </div>
              <div className="bg-[#161b22]/80 backdrop-blur-md rounded p-2 border border-[#30363d]/30 flex flex-col items-center">
                <span className="text-[#484f58] mb-1 text-[10px]">Tokens</span>
                <span className="text-[#c9d1d9] font-medium">{nodeData.metadata.tokens} tks</span>
              </div>
              {nodeData.metadata.confidence && (
                <div className="bg-[#161b22]/80 backdrop-blur-md rounded p-2 border border-[#30363d]/30 flex flex-col items-center col-span-2">
                  <span className="text-[#484f58] mb-1 text-[10px]">Confidence</span>
                  <span className="text-[#3fb950] font-medium">{Math.round(nodeData.metadata.confidence * 100)}%</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
