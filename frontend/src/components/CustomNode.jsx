import React, { useState } from 'react';
import { Handle, Position } from '@xyflow/react';
import { Activity, Clock, FileCode2, Cpu, FileWarning, Send } from 'lucide-react';

export default function CustomNode({ id, data }) {
  const { label, stateData } = data;
  const [nodePrompt, setNodePrompt] = useState('');
  const [isPrompting, setIsPrompting] = useState(false);
  
  const statusColors = {
     idle: 'border-white/10 text-gray-400 bg-[#0a0a0f]',
     running: 'border-cyan-400 shadow-[0_0_20px_rgba(0,240,255,0.2)] text-cyan-400 bg-black/60',
     success: 'border-green-400 shadow-[0_0_15px_rgba(34,197,94,0.15)] text-green-400 bg-black/50',
     error: 'border-red-500 shadow-[0_0_15px_rgba(239,68,68,0.2)] text-red-500 bg-black/50'
  };

  const currentStatus = stateData?.status || 'idle';
  const isManager = label.toLowerCase().includes('manager');
  const isInputNode = label.toLowerCase().includes('request');

  const handlePrompt = async (e) => {
    if ((e.key === 'Enter' || e.type === 'click') && nodePrompt.trim() !== '') {
      setIsPrompting(true);
      try {
        await fetch("http://127.0.0.1:8888/run-node", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ agent_id: id, prompt: nodePrompt })
        });
        setNodePrompt('');
      } catch (err) {
        console.error("Failed to run node directly", err);
      } finally {
        setIsPrompting(false);
      }
    }
  };

  return (
    <div className={`p-4 rounded-xl border-2 w-72 transition-all duration-300 relative group overflow-hidden ${statusColors[currentStatus]}`}>
      
      {/* Input Handle */}
      {label !== 'User Request' && <Handle type="target" position={Position.Left} className="w-2.5 h-6 rounded-sm bg-gray-500 border-none -ml-1 transition-all group-hover:bg-cyan-400 opacity-60 hover:opacity-100" />}
      
      {/* Node Header */}
      <div className="font-bold uppercase tracking-[0.2em] text-[9px] flex justify-between items-center mb-3">
         <span className="flex items-center gap-1.5">
           {isManager ? <Cpu className="w-3.5 h-3.5" /> : <FileCode2 className="w-3.5 h-3.5" />} 
           {label}
         </span>
         
         <div className={`px-2 py-0.5 rounded-full border ${
           currentStatus === 'running' ? 'bg-cyan-500/10 border-cyan-500/30' : 
           currentStatus === 'success' ? 'bg-green-500/10 border-green-500/30' :
           currentStatus === 'error' ? 'bg-red-500/10 border-red-500/30' :
           'bg-white/5 border-white/10'
         }`}>
           {currentStatus === 'running' ? <Activity className="w-3 h-3 animate-spin" /> : currentStatus}
         </div>
      </div>

      <div className="space-y-2">
        {/* State Preview (Output or Input) */}
        {stateData && stateData.status !== 'idle' && (
          <div className="relative bg-[#050505] inset-shadow-sm p-2.5 rounded border border-white/5 text-[10px] font-mono text-gray-300 h-28 overflow-y-auto w-full custom-scrollbar">
              
              {stateData.error ? (
                  <div className="text-red-400 flex items-start gap-2">
                     <FileWarning className="w-4 h-4 mt-0.5 shrink-0" />
                     <span className="break-all">{stateData.error}</span>
                  </div>
              ) : stateData.output ? (
                  isManager && typeof stateData.output === 'string' && stateData.output.startsWith('{') ? (
                      // Manager parsed JSON decision rendering beautifully
                      <pre className="text-cyan-200/90 whitespace-pre-wrap font-mono text-[9px]">
                        {(() => {
                            try { return JSON.stringify(JSON.parse(stateData.output), null, 2); }
                            catch(e) { return stateData.output; }
                        })()}
                      </pre>
                  ) : (
                      // Agent generation rendering
                      <span className="whitespace-pre-wrap break-words">{stateData.output}</span>
                  )
              ) : (
                  <div className="text-gray-500 flex items-center justify-center h-full animate-pulse">
                    Processing matrix...
                  </div>
              )}
          </div>
        )}

        {/* Metrics Footer */}
        {stateData?.metadata?.latency_ms && (
          <div className="flex justify-between items-center text-[10px] text-gray-500 font-mono bg-white/5 px-2 py-1.5 rounded-md border border-white/5 mt-2">
              <span className="flex items-center gap-1">
                 <Clock className="w-3 h-3" />
                 {stateData.metadata.latency_ms}ms
              </span>
              <span>
                 {stateData.metadata.tokens ? `${stateData.metadata.tokens} tokens` : '0 tokens'}
              </span>
          </div>
        )}
      </div>

      {/* INDEPENDENT NODE PROMPTER (Hidden on Input/Manager) */}
      {!isInputNode && !isManager && (
        <div className="mt-3 relative opacity-0 group-hover:opacity-100 transition-opacity duration-300">
          <input
             type="text"
             value={nodePrompt}
             onChange={(e) => setNodePrompt(e.target.value)}
             onKeyDown={handlePrompt}
             disabled={isPrompting}
             placeholder={`Prompt ${label}...`}
             className="w-full bg-[#111] border border-white/10 rounded-md py-1.5 pl-2 pr-6 text-[9px] text-gray-300 placeholder-gray-600 focus:outline-none focus:border-cyan-500/50"
          />
          <button onClick={handlePrompt} className="absolute right-1.5 top-1/2 -translate-y-1/2 text-gray-500 hover:text-cyan-400">
             <Send className="w-3 h-3" />
          </button>
        </div>
      )}

      {/* Output Handle */}
      {label !== 'User Request' && <Handle type="source" position={Position.Right} className="w-2.5 h-6 rounded-sm bg-gray-500 border-none -mr-1 transition-all group-hover:bg-cyan-400 opacity-60 hover:opacity-100" />}
      {label === 'User Request' && <Handle type="source" position={Position.Right} className="w-2 h-2 rounded-full bg-cyan-400 border-none animate-pulse" />}
    </div>
  );
}
