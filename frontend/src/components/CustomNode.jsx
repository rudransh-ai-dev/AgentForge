import React, { memo, useState } from 'react';
import { Handle, Position, useReactFlow } from '@xyflow/react';
import {
  Activity, Clock, FileCode2, Cpu, FileWarning, Send, Zap, Play,
  Minus, Trash2, Maximize2, Settings2, X, Check, ChevronDown
} from 'lucide-react';
import { useAgentStore } from '../store/useAgentStore';

function CustomNode({ id, data }) {
  const { label, stateData: nodeStateData } = data;
  const { nodesState, availableModels, setCanvasNodeModel, canvasNodeModels, resetAll } = useAgentStore();
  const [nodePrompt, setNodePrompt] = useState('');
  const [isPrompting, setIsPrompting] = useState(false);
  const [isRunningPipeline, setIsRunningPipeline] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [showConfig, setShowConfig] = useState(false);
  const [configLabel, setConfigLabel] = useState(label);
  const [configSystemPrompt, setConfigSystemPrompt] = useState(data.systemPrompt || '');
  const [configModel, setConfigModel] = useState(data.model || '');
  const { deleteElements, setNodes } = useReactFlow();

  // Prefer store state over node data for live updates
  const storeState = nodesState[id];
  const stateData = storeState || nodeStateData || { status: 'idle', input: '', output: '', error: '', metadata: {} };

  const statusColors = {
    idle: 'border-[#30363d]/80 text-[#8b949e] bg-[#0d1117]/90',
    running: 'border-[#58a6ff]/60 text-[#58a6ff] bg-[#0d1117]/90 shadow-[0_0_15px_rgba(88,166,255,0.2)]',
    success: 'border-[#3fb950]/60 text-[#3fb950] bg-[#0d1117]/90 shadow-[0_0_15px_rgba(63,185,80,0.2)]',
    error: 'border-[#f85149]/60 text-[#f85149] bg-[#0d1117]/90 shadow-[0_0_15px_rgba(248,81,73,0.2)]'
  };

  const currentStatus = stateData?.status || 'idle';
  const isInputNode = label.toLowerCase().includes('input');

  const handlePrompt = async (e) => {
    if ((e.key === 'Enter' || e.type === 'click') && nodePrompt.trim() !== '') {
      setIsPrompting(true);
      try {
        await fetch("/run-node", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ agent_id: id, prompt: nodePrompt, model: configModel || undefined, system_prompt: configSystemPrompt || undefined })
        });
        setNodePrompt('');
      } catch (err) {
        console.error("Failed to run node directly", err);
      } finally {
        setIsPrompting(false);
      }
    }
  };

  const handleRunPipeline = async () => {
    if (nodePrompt.trim() === '' || isRunningPipeline) return;
    setIsRunningPipeline(true);
    resetAll();
    try {
      const res = await fetch("/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: nodePrompt,
          mode: "agent",
          node_models: canvasNodeModels || {},
        })
      });
      if (!res.ok) {
        const txt = await res.text();
        console.error("Pipeline run failed:", res.status, txt);
      }
    } catch (err) {
      console.error("Pipeline run error:", err);
    } finally {
      setIsRunningPipeline(false);
    }
  };

  const saveConfig = () => {
    setNodes(nds => nds.map(n => n.id === id
      ? { ...n, data: { ...n.data, label: configLabel, model: configModel, systemPrompt: configSystemPrompt } }
      : n
    ));
    // Push model override to global store → sent with next /run request
    if (configModel) {
      setCanvasNodeModel(id, configModel);
    }
    setShowConfig(false);
  };

  return (
    <div className={`rounded-lg border w-64 transition-all duration-300 relative group backdrop-blur-md futuristic-node ${statusColors[currentStatus]}`}>

      {/* Status dot */}
      {currentStatus !== 'idle' && (
        <div className="absolute -top-1.5 -right-1.5 z-10">
          <div className={`w-3 h-3 rounded-full border-2 border-[#0d1117] ${currentStatus === 'running' ? 'bg-[#58a6ff] shadow-[0_0_8px_rgba(88,166,255,0.8)] animate-pulse' :
              currentStatus === 'success' ? 'bg-[#3fb950] shadow-[0_0_8px_rgba(63,185,80,0.8)]' :
                'bg-[#f85149] shadow-[0_0_8px_rgba(248,81,73,0.8)]'
            }`} />
        </div>
      )}

      {/* Handles */}
      {!isInputNode && <Handle type="target" position={Position.Left} className="!w-2.5 !h-2.5 !rounded-full !bg-[#30363d] !border-2 !border-[#21262d] group-hover:!bg-[#58a6ff] !transition-all" />}
      <Handle type="source" position={Position.Right} className="!w-2.5 !h-2.5 !rounded-full !bg-[#30363d] !border-2 !border-[#21262d] group-hover:!bg-[#58a6ff] !transition-all" />

      {/* Header */}
      <div className={`flex items-center gap-2 px-3 py-2 border-b ${isMinimized ? 'border-transparent' : 'border-[#21262d]'}`}>
        <div className={`p-1 rounded shrink-0 ${currentStatus === 'running' ? 'bg-[#58a6ff]/15' :
            currentStatus === 'success' ? 'bg-[#3fb950]/15' :
              'bg-[#21262d]'
          }`}>
          {label.toLowerCase().includes('manager') || label.toLowerCase().includes('agent') ? (
            <Cpu className="w-3 h-3" />
          ) : label.toLowerCase().includes('coder') ? (
            <FileCode2 className="w-3 h-3" />
          ) : (
            <Zap className="w-3 h-3" />
          )}
        </div>
        <span className="text-[10px] font-semibold uppercase tracking-wider truncate flex-1" title={data.label || label}>
          {data.label || label}
          {data.model && <span className="ml-1 text-[#6e7681] normal-case font-mono">· {data.model.split(':')[0]}</span>}
        </span>

        {/* Action buttons — visible on hover */}
        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onMouseDown={(e) => e.stopPropagation()}
            onClick={(e) => { e.stopPropagation(); setShowConfig(!showConfig); setIsMinimized(false); }}
            className={`p-0.5 rounded transition-colors ${showConfig ? 'text-[#58a6ff]' : 'text-[#6e7681] hover:text-[#c9d1d9]'}`}
            title="Configure Node"
          >
            <Settings2 className="w-3 h-3" />
          </button>
          <button
            onMouseDown={(e) => e.stopPropagation()}
            onClick={(e) => { e.stopPropagation(); setIsMinimized(!isMinimized); setShowConfig(false); }}
            className="p-0.5 rounded text-[#6e7681] hover:text-[#c9d1d9] transition-colors"
            title={isMinimized ? "Expand" : "Minimize"}
          >
            {isMinimized ? <Maximize2 className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
          </button>
          <button
            onMouseDown={(e) => e.stopPropagation()}
            onClick={(e) => { e.stopPropagation(); deleteElements({ nodes: [{ id }] }); }}
            className="p-0.5 rounded text-[#6e7681] hover:text-[#f85149] transition-colors"
            title="Delete Node"
          >
            <Trash2 className="w-3 h-3" />
          </button>
        </div>

        {/* Status badge */}
        <div className={`ml-1 px-1.5 py-0.5 rounded text-[8px] font-semibold tracking-wider uppercase shrink-0 ${currentStatus === 'running' ? 'bg-[#58a6ff]/10 text-[#58a6ff]' :
            currentStatus === 'success' ? 'bg-[#3fb950]/10 text-[#3fb950]' :
              currentStatus === 'error' ? 'bg-[#f85149]/10 text-[#f85149]' :
                'bg-[#21262d] text-[#6e7681]'
          }`}>
          {currentStatus === 'running' ? <Activity className="w-2 h-2 animate-spin" /> : currentStatus}
        </div>
      </div>

      {/* Config Panel */}
      {showConfig && !isMinimized && (
        <div className="px-3 py-2.5 border-b border-[#21262d] space-y-2.5 text-[11px]">
          <div>
            <label className="block text-[#6e7681] mb-1 text-[10px] uppercase tracking-wider font-medium">Node Label</label>
            <input
              className="w-full bg-[#161b22] border border-[#30363d] rounded px-2 py-1 text-[#c9d1d9] text-xs focus:outline-none focus:border-[#58a6ff]"
              value={configLabel}
              onChange={e => setConfigLabel(e.target.value)}
              placeholder="Node name..."
            />
          </div>

          <div>
            <label className="block text-[#6e7681] mb-1 text-[10px] uppercase tracking-wider font-medium">Model</label>
            <div className="relative">
              <select
                className="w-full bg-[#161b22] border border-[#30363d] rounded px-2 py-1 text-[#c9d1d9] text-xs focus:outline-none focus:border-[#58a6ff] appearance-none cursor-pointer pr-6"
                value={configModel}
                onChange={e => setConfigModel(e.target.value)}
              >
                <option value="">Auto / Default</option>
                {availableModels.map(m => <option key={m} value={m}>{m}</option>)}
              </select>
              <ChevronDown className="absolute right-1.5 top-1/2 -translate-y-1/2 w-3 h-3 text-[#6e7681] pointer-events-none" />
            </div>
          </div>

          <div>
            <label className="block text-[#6e7681] mb-1 text-[10px] uppercase tracking-wider font-medium">System Prompt</label>
            <textarea
              className="w-full bg-[#161b22] border border-[#30363d] rounded px-2 py-1 text-[#c9d1d9] text-[10px] font-mono focus:outline-none focus:border-[#58a6ff] resize-none"
              rows={3}
              value={configSystemPrompt}
              onChange={e => setConfigSystemPrompt(e.target.value)}
              placeholder="Override system prompt for this node..."
            />
          </div>

          <div className="flex gap-1.5 pt-0.5">
            <button
              onClick={saveConfig}
              className="flex-1 flex items-center justify-center gap-1 py-1 rounded bg-[#238636]/20 border border-[#238636]/40 text-[#3fb950] hover:bg-[#238636]/30 transition-colors text-[10px] font-medium"
            >
              <Check className="w-3 h-3" /> Apply
            </button>
            <button
              onClick={() => setShowConfig(false)}
              className="px-2 py-1 rounded bg-[#161b22] border border-[#30363d] text-[#6e7681] hover:text-[#c9d1d9] transition-colors text-[10px]"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        </div>
      )}

      {/* Node Body */}
      {!isMinimized && !showConfig && (
        <div className="px-3 py-2 space-y-2">
          {/* Output / Status area */}
          {stateData && stateData.status !== 'idle' && (
            <div className="bg-[#0d1117] p-2 rounded border border-[#21262d] text-[10px] font-mono text-[#c9d1d9] h-20 overflow-y-auto">
              {stateData.error ? (
                <div className="text-[#f85149] flex items-start gap-1.5">
                  <FileWarning className="w-3 h-3 mt-0.5 shrink-0" />
                  <span className="break-all">{stateData.error}</span>
                </div>
              ) : stateData.output ? (
                <span className="whitespace-pre-wrap break-words">{String(stateData.output).slice(0, 180)}</span>
              ) : (
                <div className="text-[#6e7681] flex items-center justify-center h-full">
                  <Activity className="w-3 h-3 animate-spin mr-1" /> Processing...
                </div>
              )}
            </div>
          )}

          {/* Latency bar */}
          {stateData?.metadata?.latency_ms && (
            <div className="flex justify-between items-center text-[9px] text-[#6e7681] font-mono">
              <span className="flex items-center gap-1">
                <Clock className="w-2.5 h-2.5" />{stateData.metadata.latency_ms}ms
              </span>
              <span>{stateData.metadata.tokens ? `${stateData.metadata.tokens} tok` : ''}</span>
            </div>
          )}

          {/* Quick prompt input (non-input nodes) */}
          {!isInputNode && (
            <div className="relative">
              <input
                name={`node-prompt-${id}`}
                id={`node-prompt-${id}`}
                type="text"
                value={nodePrompt}
                onChange={(e) => setNodePrompt(e.target.value)}
                onKeyDown={handlePrompt}
                disabled={isPrompting}
                placeholder={`Prompt this node...`}
                className="w-full bg-[#0d1117] border border-[#21262d] rounded py-1 pl-2 pr-6 text-[10px] text-[#c9d1d9] placeholder-[#484f58] focus:outline-none focus:border-[#58a6ff]/60 disabled:opacity-40 transition-colors"
              />
              <button
                onClick={handlePrompt}
                className="absolute right-1.5 top-1/2 -translate-y-1/2 text-[#484f58] hover:text-[#58a6ff] transition-colors"
              >
                <Send className="w-3 h-3" />
              </button>
            </div>
          )}

          {/* Pipeline trigger (input node only) */}
          {isInputNode && (
            <div className="space-y-1.5">
              <textarea
                name={`pipeline-prompt-${id}`}
                value={nodePrompt}
                onChange={(e) => setNodePrompt(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleRunPipeline();
                }}
                disabled={isRunningPipeline}
                rows={3}
                placeholder="Describe the task… (Ctrl+Enter to run)"
                className="w-full bg-[#0d1117] border border-[#21262d] rounded p-1.5 text-[10px] text-[#c9d1d9] placeholder-[#484f58] focus:outline-none focus:border-[#58a6ff]/60 disabled:opacity-40 resize-none font-mono"
              />
              <button
                onClick={handleRunPipeline}
                disabled={isRunningPipeline || !nodePrompt.trim()}
                className="w-full flex items-center justify-center gap-1.5 py-1.5 rounded bg-[#238636]/20 border border-[#238636]/40 text-[#3fb950] hover:bg-[#238636]/30 disabled:opacity-40 disabled:cursor-not-allowed transition-colors text-[10px] font-semibold uppercase tracking-wider"
              >
                {isRunningPipeline ? (
                  <><Activity className="w-3 h-3 animate-spin" /> Running…</>
                ) : (
                  <><Play className="w-3 h-3" /> Run Pipeline</>
                )}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default memo(CustomNode);
