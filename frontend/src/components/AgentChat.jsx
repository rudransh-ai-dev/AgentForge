import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Copy, Check, Bot, User, Loader2, RefreshCw, AlertTriangle, ChevronDown, Cpu, Terminal, BarChart3, ShieldCheck } from 'lucide-react';

const API = "http://127.0.0.1:8888";

const AGENTS = [
  { id: "manager", label: "Manager AI", icon: Cpu, color: "#06b6d4", desc: "System Planning" },
  { id: "coder", label: "Coder", icon: Terminal, color: "#a855f7", desc: "Software Engineer" },
  { id: "analyst", label: "Analyst", icon: BarChart3, color: "#22c55e", desc: "Data & Reasoning" },
  { id: "critic", label: "Critic", icon: ShieldCheck, color: "#f59e0b", desc: "Review & Ethics" },
];

export default function AgentChat() {
  const [availableModels, setAvailableModels] = useState([]);
  const [selectedAgent, setSelectedAgent] = useState(AGENTS[0]);
  const [activeModel, setActiveModel] = useState("llama3:8b");
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [copiedId, setCopiedId] = useState(null);
  const [showModelPicker, setShowModelPicker] = useState(false);
  const [retryPayload, setRetryPayload] = useState(null);
  const scrollRef = useRef(null);
  const inputRef = useRef(null);
  const pickerRef = useRef(null);

  // Fetch available models on mount
  useEffect(() => {
    fetch(`${API}/health`).then(res => res.json()).then(data => {
      setAvailableModels(data.models || []);
      // Set initial model for manager
      if (data.configured?.manager) setActiveModel(data.configured.manager);
    }).catch(console.error);
  }, []);

  // Auto-scroll on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // Close model picker on outside click
  useEffect(() => {
    const handleClick = (e) => {
      if (pickerRef.current && !pickerRef.current.contains(e.target)) {
        setShowModelPicker(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const copyText = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const sendMessage = async (overrideInput) => {
    const msgText = overrideInput || input;
    if (!msgText.trim() || isStreaming) return;

    const agent = selectedAgent;
    const model = activeModel;
    const userMsg = { role: 'user', content: msgText, id: Date.now() };
    const aiMsg = { role: 'assistant', content: '', id: Date.now() + 1, streaming: true, agent, model };

    setRetryPayload(null);
    setMessages(prev => [...prev, userMsg, aiMsg]);
    if (!overrideInput) setInput('');
    setIsStreaming(true);

    try {
      const res = await fetch(`${API}/agent/${agent.id}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msgText, model })
      });

      if (!res.ok) throw new Error(`Server error: ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let fullText = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n').filter(l => l.startsWith('data: '));

        for (const line of lines) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.chunk) {
              fullText += data.chunk;
              setMessages(prev => {
                const msgs = [...prev];
                const lastIdx = msgs.length - 1;
                msgs[lastIdx] = { ...msgs[lastIdx], content: fullText };
                return msgs;
              });
            }
          } catch (e) { }
        }
      }

      setMessages(prev => {
        const msgs = [...prev];
        const lastIdx = msgs.length - 1;
        msgs[lastIdx] = { ...msgs[lastIdx], streaming: false };
        return msgs;
      });
    } catch (err) {
      setRetryPayload(msgText);
      setMessages(prev => {
        const msgs = [...prev];
        const lastIdx = msgs.length - 1;
        msgs[lastIdx] = { ...msgs[lastIdx], content: '', streaming: false, error: err.message };
        return msgs;
      });
    } finally {
      setIsStreaming(false);
    }
  };

  const handleRetry = () => {
    if (retryPayload) {
      setMessages(prev => prev.slice(0, -2));
      sendMessage(retryPayload);
    }
  };

  const renderCodeBlocks = (text) => {
    const parts = text.split(/(```[\s\S]*?```)/g);
    return parts.map((part, i) => {
      if (part.startsWith('```')) {
        const match = part.match(/```(\w*)\n?([\s\S]*?)```/);
        const lang = match?.[1] || '';
        const code = match?.[2] || part.slice(3, -3);
        const blockId = `code-${i}`;
        return (
          <div key={i} className="relative my-3">
            <div className="flex items-center justify-between bg-[#1a1a2e] px-3 py-1.5 rounded-t-lg border border-white/5 border-b-0">
              <span className="text-[9px] text-gray-500 uppercase tracking-widest font-bold">{lang || 'code'}</span>
              <button onClick={() => copyText(code, blockId)} className="text-gray-500 hover:text-cyan-400 transition-colors">
                {copiedId === blockId ? <Check className="w-3 h-3 text-green-400" /> : <Copy className="w-3 h-3" />}
              </button>
            </div>
            <pre className="bg-[#0d0d1a] p-4 rounded-b-lg border border-white/5 border-t-0 text-[12px] text-cyan-100/80 overflow-x-auto custom-scrollbar font-mono leading-relaxed">
              {code}
            </pre>
          </div>
        );
      }
      return <span key={i} className="whitespace-pre-wrap">{part}</span>;
    });
  };

  return (
    <div className="flex-1 h-full flex flex-col bg-[#070709]">

      {/* ── Messages Area ── */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto custom-scrollbar">

        {/* Empty state */}
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="text-center px-6"
            >
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-cyan-500/10 to-purple-500/10 border border-white/[0.06] flex items-center justify-center mx-auto mb-5">
                <Bot className="w-6 h-6 text-cyan-400/60" />
              </div>
              <h2 className="text-xl font-semibold text-gray-200 mb-2">What can I help with?</h2>
              <p className="text-[13px] text-gray-600 max-w-md">
                Ask anything. Switch between agents using the model picker below.
              </p>
            </motion.div>
          </div>
        )}

        {/* Messages */}
        {messages.length > 0 && (
          <div className="max-w-3xl mx-auto px-5 py-6 space-y-1">
            {messages.map((msg) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
              >
                {msg.role === 'user' ? (
                  /* ── User message ── */
                  <div className="flex justify-end mb-4">
                    <div className="bg-white/[0.06] border border-white/[0.06] rounded-2xl rounded-br-md px-4 py-3 max-w-[85%] text-[14px] text-gray-200 leading-relaxed">
                      {msg.content}
                    </div>
                  </div>
                ) : (
                  /* ── AI message ── */
                  <div className="mb-6">
                    {/* Agent label */}
                    {msg.agent && (
                      <div className="flex items-center gap-2 mb-2 ml-1">
                        <div
                          className="w-5 h-5 rounded-lg flex items-center justify-center"
                          style={{ backgroundColor: `${msg.agent.color}15`, border: `1px solid ${msg.agent.color}25` }}
                        >
                          {React.createElement(msg.agent.icon, { className: "w-3 h-3", style: { color: msg.agent.color } })}
                        </div>
                        <span className="text-[12px] font-semibold text-gray-400">{msg.agent.label}</span>
                        <span className="text-[10px] text-gray-600 font-mono">{msg.agent.model}</span>
                      </div>
                    )}

                    {/* Message content */}
                    <div className="text-[14px] text-gray-300 leading-[1.75] ml-1">
                      {msg.error ? (
                        <div className="flex items-start gap-3 bg-red-500/5 border border-red-500/10 rounded-xl px-4 py-3">
                          <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                          <div>
                            <p className="text-red-400 text-[13px]">Failed to get response</p>
                            <p className="text-red-400/50 text-[11px] mt-1 font-mono">{msg.error}</p>
                            <button
                              onClick={handleRetry}
                              className="mt-2 text-[11px] text-red-300 hover:text-white flex items-center gap-1 transition-colors"
                            >
                              <RefreshCw className="w-3 h-3" /> Retry
                            </button>
                          </div>
                        </div>
                      ) : !msg.content && msg.streaming ? (
                        <div className="flex items-center gap-2.5 py-1 text-gray-500">
                          <div className="flex gap-1">
                            <span className="w-1.5 h-1.5 rounded-full bg-gray-500 animate-bounce" style={{ animationDelay: '0ms' }} />
                            <span className="w-1.5 h-1.5 rounded-full bg-gray-500 animate-bounce" style={{ animationDelay: '150ms' }} />
                            <span className="w-1.5 h-1.5 rounded-full bg-gray-500 animate-bounce" style={{ animationDelay: '300ms' }} />
                          </div>
                          <span className="text-[12px] text-gray-600">Thinking...</span>
                        </div>
                      ) : (
                        <>
                          {renderCodeBlocks(msg.content)}
                          {msg.streaming && msg.content && (
                            <span className="inline-block w-[3px] h-[18px] bg-gray-400 animate-pulse ml-0.5 rounded-sm align-text-bottom" />
                          )}
                        </>
                      )}
                    </div>

                    {/* Actions row */}
                    {!msg.streaming && msg.content && !msg.error && (
                      <div className="flex items-center gap-3 mt-2.5 ml-1">
                        <button
                          onClick={() => copyText(msg.content, msg.id)}
                          className="text-gray-600 hover:text-gray-300 transition-colors p-1 rounded-md hover:bg-white/[0.04]"
                          title="Copy"
                        >
                          {copiedId === msg.id ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        )}
      </div>

      {/* ── Input Area ── */}
      <div className="border-t border-white/[0.04] bg-[#070709]">
        <div className="max-w-3xl mx-auto px-5 py-4">
          <div className="relative bg-[#0e0e14] border border-white/[0.08] rounded-2xl focus-within:border-white/[0.15] transition-colors shadow-[0_-4px_20px_rgba(0,0,0,0.3)]">

            {/* Input row */}
            <div className="flex items-end gap-2 p-2">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => {
                  setInput(e.target.value);
                  // Auto-resize
                  e.target.style.height = 'auto';
                  e.target.style.height = Math.min(e.target.scrollHeight, 160) + 'px';
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                  }
                }}
                disabled={isStreaming}
                placeholder={`Ask ${selectedAgent.label}...`}
                rows={1}
                className="flex-1 bg-transparent text-[14px] text-gray-200 placeholder-gray-600 resize-none outline-none px-2 py-2 min-h-[40px] max-h-[160px] disabled:opacity-40"
              />
              <button
                onClick={() => sendMessage()}
                disabled={isStreaming || !input.trim()}
                className="p-2.5 rounded-xl bg-white/[0.06] hover:bg-white/[0.1] text-gray-400 hover:text-white transition-all disabled:opacity-20 disabled:cursor-not-allowed shrink-0 mb-0.5"
              >
                {isStreaming ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              </button>
            </div>

            {/* Bottom controls bar */}
            <div className="flex items-center justify-between px-3 pb-2.5 pt-0.5">
              {/* Model Switcher */}
              <div className="relative" ref={pickerRef}>
                <button
                  onClick={() => setShowModelPicker(!showModelPicker)}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg hover:bg-white/[0.05] transition-colors text-[12px] group"
                >
                  <div
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ backgroundColor: selectedAgent.color, boxShadow: `0 0 6px ${selectedAgent.color}40` }}
                  />
                  <span className="text-gray-400 group-hover:text-gray-200 font-medium transition-colors">{selectedAgent.label}</span>
                  <ChevronDown className={`w-3 h-3 text-gray-600 transition-transform ${showModelPicker ? 'rotate-180' : ''}`} />
                </button>

                {/* Model Picker Dropdown */}
                <AnimatePresence>
                  {showModelPicker && (
                    <motion.div
                      initial={{ opacity: 0, y: 8, scale: 0.96 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: 8, scale: 0.96 }}
                      transition={{ duration: 0.15, ease: [0.4, 0, 0.2, 1] }}
                      className="absolute bottom-full left-0 mb-2 w-72 bg-[#12121a] border border-white/[0.1] rounded-xl shadow-[0_8px_40px_rgba(0,0,0,0.6)] overflow-hidden z-50 flex flex-col"
                    >
                      <div className="p-3 border-b border-white/[0.05] bg-white/[0.02]">
                        <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest flex items-center gap-2">
                           Select Engine for {selectedAgent.label}
                        </span>
                      </div>
                      
                      <div className="p-1.5 max-h-[320px] overflow-y-auto custom-scrollbar">
                        {/* 1. AGENTS Switcher */}
                        <div className="mb-2 pb-2 border-b border-white/[0.05]">
                           {AGENTS.map(agent => (
                             <button
                                key={agent.id}
                                onClick={() => {
                                   setSelectedAgent(agent);
                                   // Try to find a good default model if switching
                                   inputRef.current?.focus();
                                }}
                                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-all text-left group ${selectedAgent.id === agent.id ? 'bg-white/[0.06] text-white' : 'text-gray-500 hover:bg-white/[0.03]'}`}
                             >
                                <div className="w-6 h-6 rounded-md flex items-center justify-center shrink-0" style={{ backgroundColor: `${agent.color}15`, border: `1px solid ${agent.color}25` }}>
                                   {React.createElement(agent.icon, { className: "w-3 h-3", style: { color: agent.color } })}
                                </div>
                                <span className="text-[12px] font-medium">{agent.label}</span>
                                {selectedAgent.id === agent.id && <div className="ml-auto w-1 h-1 rounded-full bg-cyan-400" />}
                             </button>
                           ))}
                        </div>

                        {/* 2. MODELS Switcher (All 7) */}
                        {availableModels.map((modelName) => {
                          const isSelected = activeModel === modelName;
                          return (
                            <button
                              key={modelName}
                              onClick={() => {
                                setActiveModel(modelName);
                                setShowModelPicker(false);
                                inputRef.current?.focus();
                              }}
                              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-left group ${
                                isSelected
                                  ? 'bg-cyan-500/10 border border-cyan-500/20 shadow-[0_0_15px_rgba(6,182,212,0.1)]'
                                  : 'hover:bg-white/[0.04] border border-transparent'
                              }`}
                            >
                              <div
                                className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border transition-colors ${isSelected ? 'bg-cyan-500/20 border-cyan-500/30' : 'bg-white/[0.03] border-white/[0.05] group-hover:border-white/10'}`}
                              >
                                <Cpu className={`w-4 h-4 ${isSelected ? 'text-cyan-400' : 'text-gray-600 group-hover:text-gray-400'}`} />
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                  <span className={`text-[13px] font-semibold truncate ${isSelected ? 'text-cyan-100' : 'text-gray-300 group-hover:text-white'}`}>
                                    {modelName}
                                  </span>
                                </div>
                                <span className="text-[10px] text-gray-600 font-mono tracking-tighter">OLLAMA ENGINE</span>
                              </div>
                              {isSelected && (
                                <div className="w-4 h-4 rounded-full bg-cyan-500 flex items-center justify-center shrink-0 shadow-[0_0_10px_rgba(6,182,212,0.5)]">
                                  <Check className="w-2.5 h-2.5 text-black" strokeWidth={4} />
                                </div>
                              )}
                            </button>
                          );
                        })}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {/* Right side info */}
              <span className="text-[10px] text-cyan-500/60 font-mono tracking-widest uppercase">
                {activeModel}
              </span>
            </div>
          </div>

          {/* Footer */}
          <p className="text-center text-[10px] text-gray-700 mt-3 flex items-center justify-center gap-2">
            <span className="w-1 h-1 rounded-full bg-green-500 animate-pulse" /> Running {availableModels.length} Local Models via Ollama
          </p>
        </div>
      </div>
    </div>
  );
}
