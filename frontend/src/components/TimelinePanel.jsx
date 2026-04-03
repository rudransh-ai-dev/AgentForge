import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Zap, Clock, Activity } from 'lucide-react';

export default function TimelinePanel({ executionLog }) {
  const filteredLog = executionLog.filter(log => log.type !== 'update');

  return (
    <div className="w-[380px] flex flex-col gap-4 shrink-0">
      <div className="flex-1 glass-panel rounded-2xl flex flex-col overflow-hidden bg-gradient-to-b from-black/40 to-black/80 border border-white/5 relative">
        {/* Top glow accent */}
        <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-cyan-400/50 to-transparent" />
        
        <div className="p-4 border-b border-white/[0.06] flex items-center gap-2">
          <motion.div
            animate={{ rotate: [0, 360] }}
            transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
          >
            <Zap className="w-4 h-4 text-cyan-400" />
          </motion.div>
          <span className="font-bold text-gray-200 text-xs uppercase tracking-wider">Timeline (Live)</span>
          <span className="ml-auto text-[10px] text-cyan-400 font-mono flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-pulse"></span> 
            {executionLog.length} events
          </span>
        </div>
        <div className="flex-1 p-3 overflow-y-auto space-y-2 font-mono text-[10px] custom-scrollbar flex flex-col-reverse">
          <AnimatePresence>
            {[...filteredLog].reverse().map((log) => (
              <motion.div
                key={log.event_id}
                initial={{ opacity: 0, x: -20, scale: 0.95 }}
                animate={{ opacity: 1, x: 0, scale: 1 }}
                exit={{ opacity: 0, x: 20, scale: 0.95 }}
                layout
                className="bg-[#0a0a0f] border border-white/5 rounded-lg p-3 hover:border-white/10 transition-all duration-200 mb-2 group hover:shadow-[0_0_15px_rgba(0,240,255,0.1)]"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-gray-500 text-[9px] flex items-center gap-1">
                    <Clock className="w-2.5 h-2.5" />
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </span>
                  <span className={`uppercase font-bold tracking-widest text-[8px] px-1.5 py-0.5 rounded border flex items-center gap-1 ${
                    log.type === 'start' ? 'text-amber-400 border-amber-400/20 bg-amber-400/5' :
                    log.type === 'complete' ? 'text-green-400 border-green-400/20 bg-green-400/5' :
                    log.type === 'error' ? 'text-red-400 border-red-400/20 bg-red-400/5' : 
                    'text-cyan-400 border-cyan-400/20 bg-cyan-400/5'
                  }`}>
                    {log.type === 'start' && <Activity className="w-2 h-2 animate-spin" />}
                    {log.node_id} · {log.type}
                  </span>
                </div>
                <div className="text-gray-300 leading-relaxed max-h-40 overflow-y-auto custom-scrollbar pr-1">
                    {log.type === 'start' && <div className="text-amber-200 opacity-60 mb-1">▶ EXEC_TARGET: {log.node_id}</div>}
                    <span className="whitespace-pre-wrap break-words">
                      {log.output ? String(log.output).slice(0, 500) : String(log.input).slice(0, 500)}
                    </span>
                </div>
              </motion.div>
            )).slice(0, 50)}

          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
