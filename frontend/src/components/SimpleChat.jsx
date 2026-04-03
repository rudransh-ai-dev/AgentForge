import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Copy, Check, Loader2, RefreshCw, AlertTriangle, ChevronDown, MessageCircle, Heart, Flame, BookOpen, Brain, Skull, Sparkles, Cpu, BarChart3, X, Edit3 } from 'lucide-react';
import { getAgents, getAgentById, loadAgentPrompts, getAgentPrompt, API, CHAT_API } from '../config/agents';

const PERSONA_ICONS = {
  unhinged_gf: Heart,
  raw_bro: Flame,
  savage_teacher: BookOpen,
  therapist: Brain,
  roaster: Skull,
};

const PERSONAS = [
  { key: 'unhinged_gf', label: 'Unhinged GF', icon: Heart, color: '#ec4899', desc: 'Chaotic Love' },
  { key: 'raw_bro', label: 'Raw Bro', icon: Flame, color: '#f97316', desc: 'Unfiltered Truth' },
  { key: 'savage_teacher', label: 'Savage Teacher', icon: BookOpen, color: '#a855f7', desc: 'Brutal Lessons' },
  { key: 'therapist', label: 'Therapist', icon: Brain, color: '#22c55e', desc: 'Calm & Healing' },
  { key: 'roaster', label: 'Roaster', icon: Skull, color: '#ef4444', desc: 'Merciless Burns' },
];

export default function SimpleChat() {
  const AGENTS = getAgents();
  const [availableModels, setAvailableModels] = useState([]);
  const [selectedPersona, setSelectedPersona] = useState(PERSONAS[0]);
  const [selectedAgent, setSelectedAgent] = useState(AGENTS[0]);
  const [chatMode, setChatMode] = useState('persona');
  const [selectedModel, setSelectedModel] = useState('');
  const [directModel, setDirectModel] = useState('');
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [copiedId, setCopiedId] = useState(null);
  const [showModelPicker, setShowModelPicker] = useState(false);
  const [retryPayload, setRetryPayload] = useState(null);
  const [sessionId] = useState(() => `chat_${Date.now()}`);
  const [personaDefaultPrompts, setPersonaDefaultPrompts] = useState({});
  const [personaCustomPrompts, setPersonaCustomPrompts] = useState({});
  const [agentDefaultPrompts, setAgentDefaultPrompts] = useState({});
  const [agentCustomPrompts, setAgentCustomPrompts] = useState({});
  const [editingPrompt, setEditingPrompt] = useState(null);
  const [editingPromptType, setEditingPromptType] = useState(null);
  const [promptText, setPromptText] = useState('');
  const scrollRef = useRef(null);
  const inputRef = useRef(null);
  const pickerRef = useRef(null);

  useEffect(() => {
    Promise.all([
      fetch(`${API}/health`).then(res => res.json()).catch(() => null),
      fetch(`${CHAT_API}/models`).then(res => res.json()).catch(() => null),
      fetch(`${CHAT_API}/personas`).then(res => res.json()).catch(() => null),
      loadAgentPrompts(),
    ]).then(([healthData, chatModelsData, personasData, promptsData]) => {
      const mainModels = healthData?.models || [];
      const chatModels = chatModelsData?.models || [];
      const allModels = [...new Set([...mainModels, ...chatModels])];
      if (allModels.length > 0) {
        setAvailableModels(allModels);
        if (!selectedModel) setSelectedModel(allModels[0]);
      }

      if (personasData?.personas?.length > 0) {
        const defaults = {};
        const customs = {};
        personasData.personas.forEach(p => {
          defaults[p.key] = p.system || '';
          customs[p.key] = p.system || '';
        });
        setPersonaDefaultPrompts(defaults);
        setPersonaCustomPrompts(customs);
      }

      const agentDefaults = {};
      if (promptsData) {
        Object.keys(promptsData).forEach(id => {
          agentDefaults[id] = promptsData[id].chat || '';
        });
      }
      setAgentDefaultPrompts(agentDefaults);
      setAgentCustomPrompts({ ...agentDefaults });
    }).catch(console.error);
  }, []);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  useEffect(() => {
    const handleClick = (e) => {
      if (pickerRef.current && !pickerRef.current.contains(e.target)) {
        setShowModelPicker(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const copyText = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const openPromptEditor = (key, type) => {
    setEditingPrompt(key);
    setEditingPromptType(type);
    if (type === 'persona') {
      setPromptText(personaCustomPrompts[key] || personaDefaultPrompts[key] || '');
    } else {
      setPromptText(agentCustomPrompts[key] || agentDefaultPrompts[key] || getAgentPrompt(key, 'chat') || '');
    }
  };

  const savePrompt = () => {
    if (editingPrompt && editingPromptType) {
      if (editingPromptType === 'persona') {
        setPersonaCustomPrompts(prev => ({ ...prev, [editingPrompt]: promptText }));
      } else {
        setAgentCustomPrompts(prev => ({ ...prev, [editingPrompt]: promptText }));
      }
      setEditingPrompt(null);
      setEditingPromptType(null);
      setPromptText('');
    }
  };

  const resetPrompt = () => {
    if (editingPromptType === 'persona') {
      const original = personaDefaultPrompts[editingPrompt];
      if (original) {
        setPersonaCustomPrompts(prev => ({ ...prev, [editingPrompt]: original }));
        setPromptText(original);
      }
    } else {
      const original = agentDefaultPrompts[editingPrompt] || getAgentPrompt(editingPrompt, 'chat') || '';
      setAgentCustomPrompts(prev => ({ ...prev, [editingPrompt]: original }));
      setPromptText(original);
    }
  };

  const sendMessage = async (overrideInput) => {
    const msgText = overrideInput || input;
    if (!msgText.trim() || isStreaming) return;

    const userMsg = { role: 'user', content: msgText, id: Date.now() };
    const aiMsg = {
      role: 'assistant',
      content: '',
      id: Date.now() + 1,
      streaming: true,
      persona: chatMode === 'persona' ? selectedPersona.key : undefined,
      agent: chatMode === 'agent' ? selectedAgent : undefined,
      directModel: chatMode === 'direct' ? directModel : undefined,
      model: chatMode === 'direct' ? directModel : selectedModel,
    };

    setRetryPayload(null);
    setMessages(prev => [...prev, userMsg, aiMsg]);
    if (!overrideInput) setInput('');
    setIsStreaming(true);

    try {
      let res;
      if (chatMode === 'agent') {
        const customPrompt = agentCustomPrompts[selectedAgent.id];
        const isCustom = customPrompt !== agentDefaultPrompts[selectedAgent.id];
        res = await fetch(`${API}/agent/${selectedAgent.id}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ 
            message: msgText, 
            model: selectedModel,
            custom_prompt: isCustom ? customPrompt : undefined,
          }),
        });
      } else if (chatMode === 'direct') {
        res = await fetch(`${API}/agent/manager/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: msgText, model: directModel }),
        });
      } else {
        res = await fetch(`${CHAT_API}/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: msgText,
            persona: selectedPersona.key,
            model: selectedModel || undefined,
            session_id: sessionId,
            custom_prompt: personaCustomPrompts[selectedPersona.key] || undefined,
          }),
        });
      }

      if (!res.ok) throw new Error(`Server error: ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let fullText = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = decoder.decode(value);
        const lines = text.split('\n').filter(l => l.startsWith('data: '));

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

  const currentColor = chatMode === 'agent' ? selectedAgent.color : chatMode === 'direct' ? '#6366f1' : selectedPersona.color;
  const currentLabel = chatMode === 'agent' ? selectedAgent.label : chatMode === 'direct' ? directModel : selectedPersona.label;

  return (
    <div className="flex-1 h-full flex flex-col bg-[#070709]">
      <div ref={scrollRef} className="flex-1 overflow-y-auto custom-scrollbar">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="text-center px-6"
            >
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-cyan-500/10 to-purple-500/10 border border-white/[0.06] flex items-center justify-center mx-auto mb-5">
                {chatMode === 'direct' ? (
                  <BarChart3 className="w-6 h-6 text-indigo-400/60" />
                ) : chatMode === 'agent' ? (
                  React.createElement(selectedAgent.icon, { className: 'w-6 h-6', style: { color: selectedAgent.color } })
                ) : (
                  React.createElement(selectedPersona.icon || Sparkles, { className: 'w-6 h-6', style: { color: selectedPersona.color } })
                )}
              </div>
              <h2 className="text-xl font-semibold text-gray-200 mb-2">What can I help with?</h2>
              <p className="text-[13px] text-gray-600 max-w-md">
                {chatMode === 'direct'
                  ? `Chat directly with ${directModel || 'a model'}.`
                  : chatMode === 'agent'
                  ? `Chat with ${currentLabel}. Click the edit icon to customize the system prompt.`
                  : `Ask ${currentLabel}. Switch personas or models below.`}
              </p>
            </motion.div>
          </div>
        )}

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
                  <div className="flex justify-end mb-4">
                    <div className="bg-white/[0.06] border border-white/[0.06] rounded-2xl rounded-br-md px-4 py-3 max-w-[85%] text-[14px] text-gray-200 leading-relaxed">
                      {msg.content}
                    </div>
                  </div>
                ) : (
                  <div className="mb-6">
                    {(msg.persona || msg.agent || msg.directModel) && (
                      <div className="flex items-center gap-2 mb-2 ml-1">
                        {msg.agent ? (
                          <>
                            <div className="w-5 h-5 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${msg.agent.color}15`, border: `1px solid ${msg.agent.color}25` }}>
                              {React.createElement(msg.agent.icon, { className: "w-3 h-3", style: { color: msg.agent.color } })}
                            </div>
                            <span className="text-[12px] font-semibold text-gray-400">{msg.agent.label}</span>
                          </>
                        ) : msg.persona ? (
                          <>
                            <div className="w-5 h-5 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${PERSONAS.find(p => p.key === msg.persona)?.color || '#06b6d4'}15`, border: `1px solid ${PERSONAS.find(p => p.key === msg.persona)?.color || '#06b6d4'}25` }}>
                              {React.createElement(PERSONA_ICONS[msg.persona] || Sparkles, { className: "w-3 h-3", style: { color: PERSONAS.find(p => p.key === msg.persona)?.color } })}
                            </div>
                            <span className="text-[12px] font-semibold text-gray-400">{PERSONAS.find(p => p.key === msg.persona)?.label || 'AI'}</span>
                          </>
                        ) : msg.directModel ? (
                          <>
                            <div className="w-5 h-5 rounded-lg flex items-center justify-center bg-indigo-500/15 border border-indigo-500/25">
                              <BarChart3 className="w-3 h-3 text-indigo-400" />
                            </div>
                            <span className="text-[12px] font-semibold text-gray-400">Direct</span>
                          </>
                        ) : null}
                        <span className="text-[10px] text-gray-600 font-mono">{msg.model}</span>
                      </div>
                    )}

                    <div className="text-[14px] text-gray-300 leading-[1.75] ml-1">
                      {msg.error ? (
                        <div className="flex items-start gap-3 bg-red-500/5 border border-red-500/10 rounded-xl px-4 py-3">
                          <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                          <div>
                            <p className="text-red-400 text-[13px]">Failed to get response</p>
                            <p className="text-red-400/50 text-[11px] mt-1 font-mono">{msg.error}</p>
                            <button onClick={handleRetry} className="mt-2 text-[11px] text-red-300 hover:text-white flex items-center gap-1 transition-colors">
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

                    {!msg.streaming && msg.content && !msg.error && (
                      <div className="flex items-center gap-3 mt-2.5 ml-1">
                        <button onClick={() => copyText(msg.content, msg.id)} className="text-gray-600 hover:text-gray-300 transition-colors p-1 rounded-md hover:bg-white/[0.04]" title="Copy">
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

      <div className="border-t border-white/[0.04] bg-[#070709]">
        <div className="max-w-3xl mx-auto px-5 py-4">
          <div className="relative bg-[#0e0e14] border border-white/[0.08] rounded-2xl focus-within:border-white/[0.15] transition-colors shadow-[0_-4px_20px_rgba(0,0,0,0.3)]">
            <div className="flex items-end gap-2 p-2">
              <textarea
                ref={inputRef}
                name="chat-input"
                id="chat-input"
                value={input}
                onChange={(e) => {
                  setInput(e.target.value);
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
                placeholder={`Ask ${currentLabel}...`}
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

            <div className="flex items-center justify-between px-3 pb-2.5 pt-0.5">
              <div className="relative" ref={pickerRef}>
                <button
                  onClick={() => setShowModelPicker(!showModelPicker)}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg hover:bg-white/[0.05] transition-colors text-[12px] group"
                >
                  <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: currentColor, boxShadow: `0 0 6px ${currentColor}40` }} />
                  <span className="text-gray-400 group-hover:text-gray-200 font-medium transition-colors">{currentLabel}</span>
                  <ChevronDown className={`w-3 h-3 text-gray-600 transition-transform ${showModelPicker ? 'rotate-180' : ''}`} />
                </button>

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
                        <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">
                          {chatMode === 'persona' ? 'Select Persona' : chatMode === 'agent' ? 'Select Agent' : 'Select LLM'}
                        </span>
                      </div>

                      <div className="p-1.5 max-h-[420px] overflow-y-auto custom-scrollbar">
                        {chatMode === 'persona' && (
                          <div className="mb-2 pb-2 border-b border-white/[0.05]">
                            {PERSONAS.map(persona => (
                              <div key={persona.key} className="flex items-center gap-1">
                                <button
                                  onClick={() => { setSelectedPersona(persona); inputRef.current?.focus(); }}
                                  className={`flex-1 flex items-center gap-3 px-3 py-2 rounded-lg transition-all text-left group ${selectedPersona.key === persona.key ? 'bg-white/[0.06] text-white' : 'text-gray-500 hover:bg-white/[0.03]'}`}
                                >
                                  <div className="w-6 h-6 rounded-md flex items-center justify-center shrink-0" style={{ backgroundColor: `${persona.color}15`, border: `1px solid ${persona.color}25` }}>
                                    {React.createElement(persona.icon, { className: "w-3 h-3", style: { color: persona.color } })}
                                  </div>
                                  <span className="text-[12px] font-medium">{persona.label}</span>
                                  {selectedPersona.key === persona.key && <div className="ml-auto w-1 h-1 rounded-full bg-cyan-400" />}
                                </button>
                                <button
                                  onClick={() => openPromptEditor(persona.key, 'persona')}
                                  className="p-1.5 rounded-md text-gray-600 hover:text-cyan-400 hover:bg-white/[0.05] transition-all shrink-0"
                                  title="Edit system prompt"
                                >
                                  <Edit3 className="w-3 h-3" />
                                </button>
                              </div>
                            ))}
                          </div>
                        )}

                        {chatMode === 'agent' && (
                          <div className="mb-2 pb-2 border-b border-white/[0.05]">
                            {AGENTS.map(agent => (
                              <div key={agent.id} className="flex items-center gap-1">
                                <button
                                  onClick={() => { setSelectedAgent(agent); inputRef.current?.focus(); }}
                                  className={`flex-1 flex items-center gap-3 px-3 py-2 rounded-lg transition-all text-left group ${selectedAgent.id === agent.id ? 'bg-white/[0.06] text-white' : 'text-gray-500 hover:bg-white/[0.03]'}`}
                                >
                                  <div className="w-6 h-6 rounded-md flex items-center justify-center shrink-0" style={{ backgroundColor: `${agent.color}15`, border: `1px solid ${agent.color}25` }}>
                                    {React.createElement(agent.icon, { className: "w-3 h-3", style: { color: agent.color } })}
                                  </div>
                                  <div className="flex-1 min-w-0">
                                    <span className="text-[12px] font-medium">{agent.label}</span>
                                    {agentCustomPrompts[agent.id] !== agentDefaultPrompts[agent.id] && (
                                      <span className="text-[9px] text-cyan-400/60 block">custom prompt</span>
                                    )}
                                  </div>
                                  {selectedAgent.id === agent.id && <div className="ml-auto w-1 h-1 rounded-full bg-cyan-400" />}
                                </button>
                                <button
                                  onClick={() => openPromptEditor(agent.id, 'agent')}
                                  className="p-1.5 rounded-md text-gray-600 hover:text-cyan-400 hover:bg-white/[0.05] transition-all shrink-0"
                                  title="Edit system prompt"
                                >
                                  <Edit3 className="w-3 h-3" />
                                </button>
                              </div>
                            ))}
                          </div>
                        )}

                        {chatMode === 'direct' && (
                          <div className="mb-2 pb-2 border-b border-white/[0.05]">
                            {availableModels.map((modelName) => {
                              const isSelected = directModel === modelName;
                              return (
                                <button
                                  key={modelName}
                                  onClick={() => { setDirectModel(modelName); inputRef.current?.focus(); }}
                                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-left group ${isSelected ? 'bg-indigo-500/10 border border-indigo-500/20' : 'hover:bg-white/[0.04] border border-transparent'}`}
                                >
                                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border transition-colors ${isSelected ? 'bg-indigo-500/20 border-indigo-500/30' : 'bg-white/[0.03] border-white/[0.05]'}`}>
                                    <BarChart3 className={`w-4 h-4 ${isSelected ? 'text-indigo-400' : 'text-gray-600'}`} />
                                  </div>
                                  <div className="flex-1 min-w-0">
                                    <span className={`text-[13px] font-semibold truncate block ${isSelected ? 'text-indigo-100' : 'text-gray-300'}`}>{modelName}</span>
                                    <span className="text-[10px] text-gray-600 font-mono">DIRECT CHAT</span>
                                  </div>
                                  {isSelected && (
                                    <div className="w-4 h-4 rounded-full bg-indigo-500 flex items-center justify-center shrink-0">
                                      <Check className="w-2.5 h-2.5 text-black" strokeWidth={4} />
                                    </div>
                                  )}
                                </button>
                              );
                            })}
                          </div>
                        )}

                        {(chatMode === 'persona' || chatMode === 'agent') && (
                          <div>
                            <div className="px-3 py-1.5 text-[10px] text-gray-500 uppercase tracking-wider font-bold">Model</div>
                            {availableModels.map((modelName) => {
                              const isSelected = selectedModel === modelName;
                              return (
                                <button
                                  key={modelName}
                                  onClick={() => { setSelectedModel(modelName); setShowModelPicker(false); inputRef.current?.focus(); }}
                                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-left group ${isSelected ? 'bg-cyan-500/10 border border-cyan-500/20' : 'hover:bg-white/[0.04] border border-transparent'}`}
                                >
                                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border transition-colors ${isSelected ? 'bg-cyan-500/20 border-cyan-500/30' : 'bg-white/[0.03] border-white/[0.05]'}`}>
                                    <Cpu className={`w-4 h-4 ${isSelected ? 'text-cyan-400' : 'text-gray-600'}`} />
                                  </div>
                                  <div className="flex-1 min-w-0">
                                    <span className={`text-[13px] font-semibold truncate block ${isSelected ? 'text-cyan-100' : 'text-gray-300'}`}>{modelName}</span>
                                    <span className="text-[10px] text-gray-600 font-mono">OLLAMA ENGINE</span>
                                  </div>
                                  {isSelected && (
                                    <div className="w-4 h-4 rounded-full bg-cyan-500 flex items-center justify-center shrink-0">
                                      <Check className="w-2.5 h-2.5 text-black" strokeWidth={4} />
                                    </div>
                                  )}
                                </button>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              <span className="text-[10px] text-cyan-500/60 font-mono tracking-widest uppercase">
                {chatMode === 'direct' ? directModel : selectedModel}
              </span>
            </div>
          </div>

          <div className="flex gap-1 mt-3 p-1 bg-white/[0.03] rounded-lg">
            <button
              onClick={() => setChatMode('persona')}
              className={`flex-1 flex items-center justify-center gap-1.5 px-2 py-2 rounded-md text-[11px] transition-all ${chatMode === 'persona' ? 'bg-white/[0.08] text-white' : 'text-gray-500 hover:text-gray-300'}`}
            >
              <MessageCircle className="w-3 h-3" /> Persona
            </button>
            <button
              onClick={() => setChatMode('agent')}
              className={`flex-1 flex items-center justify-center gap-1.5 px-2 py-2 rounded-md text-[11px] transition-all ${chatMode === 'agent' ? 'bg-white/[0.08] text-white' : 'text-gray-500 hover:text-gray-300'}`}
            >
              <Cpu className="w-3 h-3" /> Agent
            </button>
            <button
              onClick={() => setChatMode('direct')}
              className={`flex-1 flex items-center justify-center gap-1.5 px-2 py-2 rounded-md text-[11px] transition-all ${chatMode === 'direct' ? 'bg-white/[0.08] text-white' : 'text-gray-500 hover:text-gray-300'}`}
            >
              <BarChart3 className="w-3 h-3" /> Direct LLM
            </button>
          </div>

          <p className="text-center text-[10px] text-gray-700 mt-3 flex items-center justify-center gap-2">
            <span className="w-1 h-1 rounded-full bg-green-500 animate-pulse" /> Running {availableModels.length} Local Models via Ollama
          </p>
        </div>
      </div>

      <AnimatePresence>
        {editingPrompt && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 backdrop-blur-sm z-[100] flex items-center justify-center p-4"
            onClick={() => { setEditingPrompt(null); setEditingPromptType(null); }}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="w-full max-w-lg bg-[#12121a] border border-white/[0.1] rounded-2xl shadow-2xl overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.05]">
                <div className="flex items-center gap-3">
                  {editingPromptType === 'agent' ? (
                    <>
                      {(() => {
                        const agent = getAgentById(editingPrompt);
                        const color = agent?.color || '#06b6d4';
                        const Icon = agent?.icon || Cpu;
                        const label = agent?.label || 'Edit Prompt';
                        return (
                          <>
                            <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${color}15`, border: `1px solid ${color}25` }}>
                              {React.createElement(Icon, { className: "w-4 h-4", style: { color } })}
                            </div>
                            <div>
                              <h3 className="text-[14px] font-semibold text-gray-200">{label}</h3>
                              <p className="text-[10px] text-gray-500">System prompt</p>
                            </div>
                          </>
                        );
                      })()}
                    </>
                  ) : (
                    <>
                      <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${PERSONAS.find(p => p.key === editingPrompt)?.color || '#06b6d4'}15`, border: `1px solid ${PERSONAS.find(p => p.key === editingPrompt)?.color || '#06b6d4'}25` }}>
                        {React.createElement(PERSONA_ICONS[editingPrompt] || Sparkles, { className: "w-4 h-4", style: { color: PERSONAS.find(p => p.key === editingPrompt)?.color } })}
                      </div>
                      <div>
                        <h3 className="text-[14px] font-semibold text-gray-200">{PERSONAS.find(p => p.key === editingPrompt)?.label || 'Edit Prompt'}</h3>
                        <p className="text-[10px] text-gray-500">System prompt</p>
                      </div>
                    </>
                  )}
                </div>
                <button onClick={() => { setEditingPrompt(null); setEditingPromptType(null); }} className="p-1.5 rounded-lg hover:bg-white/[0.05] text-gray-500 hover:text-white transition-all">
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="p-5">
                <textarea
                  value={promptText}
                  onChange={(e) => setPromptText(e.target.value)}
                  rows={10}
                  name="prompt-editor"
                  id="prompt-editor"
                  className="w-full bg-[#0a0a0f] border border-white/[0.08] rounded-xl px-4 py-3 text-[13px] text-gray-300 placeholder-gray-600 resize-none outline-none focus:border-white/[0.15] transition-colors font-mono leading-relaxed custom-scrollbar"
                  placeholder="Enter custom system prompt..."
                />
              </div>

              <div className="flex items-center justify-between px-5 py-4 border-t border-white/[0.05] bg-white/[0.02]">
                <button
                  onClick={resetPrompt}
                  className="text-[12px] text-gray-500 hover:text-white transition-colors flex items-center gap-1.5"
                >
                  <RefreshCw className="w-3.5 h-3.5" /> Reset to default
                </button>
                <div className="flex gap-2">
                  <button onClick={() => { setEditingPrompt(null); setEditingPromptType(null); }} className="px-4 py-2 rounded-lg text-[12px] text-gray-400 hover:text-white hover:bg-white/[0.05] transition-all">
                    Cancel
                  </button>
                  <button onClick={savePrompt} className="px-4 py-2 rounded-lg text-[12px] bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500/20 transition-all font-medium">
                    Save
                  </button>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
