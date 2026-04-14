import React, { useState, useRef, useEffect, useMemo } from 'react';
import { Send, Copy, Check, Loader2, RefreshCw, AlertTriangle, ChevronDown, X, Edit3, Cpu, Settings2 } from 'lucide-react';
import VoiceButton from './VoiceButton';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { getAgents, getAgentById, loadAgentPrompts, getAgentPrompt, API } from '../config/agents';
import { useAgentChatHistoryStore } from '../store/useAgentChatHistoryStore';
import { useAgentStore } from '../store/useAgentStore';
import ChatHistoryPanel from './ChatHistoryPanel';

const markdownComponents = {
  code({ inline, className, children, ...props }) {
    const match = /language-(\w+)/.exec(className || '');
    const lang = match ? match[1] : '';
    const codeStr = String(children).replace(/\n$/, '');

    if (!inline && lang) {
      return (
        <div className="relative my-3 rounded-lg overflow-hidden border border-borderDefault/50 group">
          <div className="flex items-center justify-between px-3 py-1.5 bg-[#1e1e1e]/80 border-b border-borderDefault/30">
            <span className="text-[10px] text-fgSubtle font-medium uppercase tracking-wider">{lang}</span>
          </div>
          <SyntaxHighlighter
            style={vscDarkPlus}
            language={lang}
            PreTag="div"
            customStyle={{ margin: 0, borderRadius: 0, padding: '12px', fontSize: '12px', lineHeight: '1.5', background: '#0d1117' }}
            {...props}
          >
            {codeStr}
          </SyntaxHighlighter>
        </div>
      );
    }

    return (
      <code className="bg-canvasSubtle/50 border border-borderDefault/30 rounded px-1.5 py-0.5 text-[11px] font-mono text-accent" {...props}>
        {children}
      </code>
    );
  },
  p: ({ children }) => <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>,
  ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
  li: ({ children }) => <li className="text-sm">{children}</li>,
  strong: ({ children }) => <strong className="font-semibold text-fgDefault">{children}</strong>,
  em: ({ children }) => <em className="italic text-fgMuted">{children}</em>,
  blockquote: ({ children }) => (
    <blockquote className="border-l-2 border-accent/30 pl-3 py-1 my-2 text-fgMuted italic">{children}</blockquote>
  ),
  h1: ({ children }) => <h1 className="text-lg font-bold text-fgDefault mb-2 mt-3">{children}</h1>,
  h2: ({ children }) => <h2 className="text-base font-bold text-fgDefault mb-2 mt-3">{children}</h2>,
  h3: ({ children }) => <h3 className="text-sm font-bold text-fgDefault mb-1 mt-2">{children}</h3>,
  table: ({ children }) => (
    <div className="overflow-x-auto my-3">
      <table className="w-full text-xs border-collapse">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th className="border border-borderDefault/50 px-2 py-1 bg-canvasSubtle/50 text-left font-semibold">{children}</th>
  ),
  td: ({ children }) => (
    <td className="border border-borderDefault/30 px-2 py-1">{children}</td>
  ),
  a: ({ href, children }) => (
    <a href={href} className="text-accent hover:text-accent/80 underline underline-offset-2 transition-colors" target="_blank" rel="noopener noreferrer">{children}</a>
  ),
};

export default function AgentChat() {
  const { customAgents } = useAgentStore();
  const builtinAgents = getAgents();
  const AGENTS = useMemo(() => [
    ...builtinAgents,
    ...customAgents.map(a => ({
      id: `custom_${a.id}`,
      label: a.name,
      icon: Cpu,
      color: a.color || '#58a6ff',
      desc: a.model,
      isCustom: true,
      customId: a.id,
      systemPrompt: a.system_prompt,
      model: a.model,
    })),
  ], [customAgents]);

  const [availableModels, setAvailableModels] = useState([]);
  const [selectedAgent, setSelectedAgent] = useState(AGENTS[0]);
  const [selectedModel, setSelectedModel] = useState('');
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [copiedId, setCopiedId] = useState(null);
  const [showModelPicker, setShowModelPicker] = useState(false);
  const [retryPayload, setRetryPayload] = useState(null);
  const [agentCustomPrompts, setAgentCustomPrompts] = useState({});
  const [agentDefaultPrompts, setAgentDefaultPrompts] = useState({});
  const [editingPrompt, setEditingPrompt] = useState(null);
  const [promptText, setPromptText] = useState('');
  const scrollRef = useRef(null);
  const inputRef = useRef(null);
  const pickerRef = useRef(null);

  const {
    sessions, activeSessionId,
    createSession, setActiveSession,
    addMessage, updateLastMessage,
    deleteSession, setSessionMessages, updateSessionMeta,
  } = useAgentChatHistoryStore();

  const activeSession = sessions.find(s => s.id === activeSessionId);
  const messages = activeSession ? activeSession.messages : [];

  useEffect(() => {
    Promise.all([
      fetch(`${API}/health`).then(res => res.json()).catch(() => null),
      loadAgentPrompts(),
    ]).then(([healthData, promptsData]) => {
      const mainModels = healthData?.models || [];
      if (mainModels.length > 0) {
        setAvailableModels(mainModels);
        if (!selectedModel) setSelectedModel(mainModels[0]);
      }

      const defaults = {};
      if (promptsData) {
        Object.keys(promptsData).forEach(id => {
          defaults[id] = promptsData[id].chat || '';
        });
      }
      setAgentDefaultPrompts(defaults);
      setAgentCustomPrompts({ ...defaults });
    }).catch(console.error);
  }, []);

  useEffect(() => {
    if (sessions.length === 0) {
      createSession(AGENTS[0], '');
    }
  }, []);

  useEffect(() => {
    if (activeSessionId && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, activeSessionId]);

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
  }, [activeSessionId]);

  const handleSelectSession = (id) => {
    setActiveSession(id);
    const session = sessions.find(s => s.id === id);
    if (session) {
      if (session.agent) {
        const agent = getAgentById(session.agent.id);
        if (agent) setSelectedAgent(agent);
      }
      if (session.model && availableModels.includes(session.model)) {
        setSelectedModel(session.model);
      }
    }
  };

  const handleCreateNew = () => {
    createSession(selectedAgent, selectedModel);
  };

  const handleDeleteSession = (id) => {
    deleteSession(id);
  };

  const copyText = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const openPromptEditor = (key) => {
    setEditingPrompt(key);
    setPromptText(agentCustomPrompts[key] || agentDefaultPrompts[key] || getAgentPrompt(key, 'chat') || '');
  };

  const savePrompt = () => {
    if (editingPrompt) {
      setAgentCustomPrompts(prev => ({ ...prev, [editingPrompt]: promptText }));
      setEditingPrompt(null);
      setPromptText('');
    }
  };

  const resetPrompt = () => {
    const original = agentDefaultPrompts[editingPrompt] || getAgentPrompt(editingPrompt, 'chat') || '';
    setAgentCustomPrompts(prev => ({ ...prev, [editingPrompt]: original }));
    setPromptText(original);
  };

  const handleAgentChange = (agent) => {
    const prevAgent = selectedAgent.label;
    setSelectedAgent(agent);
    if (messages.length > 0) {
      const sysMsg = {
        role: 'system',
        content: `Agent changed: ${prevAgent} → ${agent.label}`,
        id: Date.now(),
        systemType: 'agent_change',
      };
      addMessage(sysMsg);
    }
    updateSessionMeta({ agent: { id: agent.id, label: agent.label, color: agent.color } });
  };

  const handleModelChange = (model) => {
    const prevModel = selectedModel;
    setSelectedModel(model);
    if (messages.length > 0) {
      const sysMsg = {
        role: 'system',
        content: `Model changed: ${prevModel} → ${model}`,
        id: Date.now(),
        systemType: 'model_change',
      };
      addMessage(sysMsg);
    }
    updateSessionMeta({ model });
  };

  const sendMessage = async (overrideInput) => {
    const msgText = overrideInput || input;
    if (!msgText.trim() || isStreaming) return;

    if (!activeSessionId) {
      createSession(selectedAgent, selectedModel);
    }

    const userMsg = { role: 'user', content: msgText, id: Date.now() };
    const aiMsg = {
      role: 'assistant',
      content: '',
      id: Date.now() + 1,
      streaming: true,
      agent: selectedAgent,
      model: selectedModel,
    };

    setRetryPayload(null);
    addMessage(userMsg);
    addMessage(aiMsg);
    if (!overrideInput) setInput('');
    setIsStreaming(true);

    try {
      const customPrompt = agentCustomPrompts[selectedAgent.id];
      const isCustom = customPrompt !== agentDefaultPrompts[selectedAgent.id];

      // Custom agents use their actual backend ID, not the frontend `custom_` prefix
      const endpoint = selectedAgent.isCustom
        ? `${API}/agent/custom/${selectedAgent.customId}/chat`
        : `${API}/agent/${selectedAgent.id}/chat`;

      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: msgText,
          model: selectedModel || selectedAgent.model,
          custom_prompt: selectedAgent.isCustom
            ? selectedAgent.systemPrompt
            : (isCustom ? customPrompt : undefined),
        }),
      });

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
              updateLastMessage(msg => ({ ...msg, content: fullText }));
            }
          } catch (e) { }
        }
      }

      updateLastMessage(msg => ({ ...msg, streaming: false }));
    } catch (err) {
      setRetryPayload(msgText);
      updateLastMessage(msg => ({ ...msg, content: '', streaming: false, error: err.message }));
    } finally {
      setIsStreaming(false);
    }
  };

  const handleRetry = () => {
    if (retryPayload) {
      const msgs = [...messages];
      const lastTwoRemoved = msgs.slice(0, -2);
      setSessionMessages(lastTwoRemoved);
      sendMessage(retryPayload);
    }
  };

  const renderMessageContent = (content) => {
    return (
      <ReactMarkdown components={markdownComponents}>
        {content}
      </ReactMarkdown>
    );
  };

  return (
    <div className="flex-1 h-full flex bg-gradient-bg-mesh">
      <div className="flex-1 h-full flex flex-col min-w-0">
        <div ref={scrollRef} className="flex-1 overflow-y-auto">
          {messages.length === 0 && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center px-6">
                <div className="w-14 h-14 rounded-xl bg-canvasSubtle/50 border border-borderDefault/50 flex items-center justify-center mx-auto mb-4 animate-float backdrop-blur-sm">
                  {React.createElement(selectedAgent.icon, { className: 'w-7 h-7', style: { color: selectedAgent.color } })}
                </div>
                <h2 className="text-lg font-semibold text-gradient-accent mb-1">Agent Chat</h2>
                <p className="text-sm text-fgMuted max-w-md">
                  Chat with {selectedAgent.label}. Click the edit icon to customize the system prompt.
                </p>
              </div>
            </div>
          )}

          {messages.length > 0 && (
            <div className="max-w-3xl mx-auto px-4 py-6 space-y-4">
              {messages.map((msg) => (
                <div key={msg.id}>
                  {msg.role === 'system' ? (
                    <div className="flex items-center justify-center my-3">
                      <div className="flex items-center gap-2 px-3 py-1.5 bg-canvasSubtle/50 border border-borderDefault/30 rounded-full">
                        <Settings2 className="w-3 h-3 text-fgSubtle" />
                        <span className="text-[11px] text-fgSubtle font-medium">{msg.content}</span>
                      </div>
                    </div>
                  ) : msg.role === 'user' ? (
                    <div className="flex justify-end mb-4">
                      <div className="bg-gradient-to-br from-accent/15 to-accent/5 border border-accent/20 rounded-lg rounded-br-sm px-4 py-2.5 max-w-[85%] text-sm text-fgDefault leading-relaxed shadow-[0_2px_8px_rgba(88,166,255,0.1)]">
                        {msg.content}
                      </div>
                    </div>
                  ) : (
                    <div className="mb-4">
                      {msg.agent && (
                        <div className="flex items-center gap-2 mb-1.5 ml-1">
                          <div className="w-5 h-5 rounded flex items-center justify-center" style={{ backgroundColor: `${msg.agent.color}15`, border: `1px solid ${msg.agent.color}25` }}>
                            {React.createElement(msg.agent.icon, { className: "w-3 h-3", style: { color: msg.agent.color } })}
                          </div>
                          <span className="text-xs font-medium text-fgMuted">{msg.agent.label}</span>
                          <span className="text-[10px] text-fgSubtle font-mono">{msg.model}</span>
                        </div>
                      )}

                      <div className="text-sm text-fgDefault leading-relaxed ml-1">
                        {msg.error ? (
                          <div className="flex items-start gap-2.5 bg-danger/5 border border-danger/20 rounded-md px-3 py-2.5">
                            <AlertTriangle className="w-4 h-4 text-danger shrink-0 mt-0.5" />
                            <div>
                              <p className="text-danger text-sm">Failed to get response</p>
                              <p className="text-danger/60 text-xs mt-0.5 font-mono">{msg.error}</p>
                              <button onClick={handleRetry} className="mt-1.5 text-xs text-danger hover:text-danger/80 flex items-center gap-1 transition-colors">
                                <RefreshCw className="w-3 h-3" /> Retry
                              </button>
                            </div>
                          </div>
                        ) : !msg.content && msg.streaming ? (
                          <div className="flex items-center gap-2 py-1 text-fgSubtle">
                            <div className="flex gap-1">
                              <span className="w-1.5 h-1.5 rounded-full bg-accent animate-bounce" style={{ animationDelay: '0ms' }} />
                              <span className="w-1.5 h-1.5 rounded-full bg-accent animate-bounce" style={{ animationDelay: '150ms' }} />
                              <span className="w-1.5 h-1.5 rounded-full bg-accent animate-bounce" style={{ animationDelay: '300ms' }} />
                            </div>
                            <span className="text-xs">Thinking...</span>
                          </div>
                        ) : (
                          <>
                            <div className="prose prose-invert max-w-none prose-p:mb-2 prose-p:last:mb-0 prose-sm">
                              {renderMessageContent(msg.content)}
                            </div>
                            {msg.streaming && msg.content && (
                              <span className="inline-block w-[2px] h-[16px] bg-accent animate-pulse ml-0.5 rounded-sm align-text-bottom" />
                            )}
                          </>
                        )}
                      </div>

                      {!msg.streaming && msg.content && !msg.error && (
                        <div className="flex items-center gap-2 mt-2 ml-1">
                          <button onClick={() => copyText(msg.content, msg.id)} className="text-fgSubtle hover:text-accent transition-colors p-1 rounded hover:bg-canvasSubtle/50" title="Copy">
                            {copiedId === msg.id ? <Check className="w-3.5 h-3.5 text-success" /> : <Copy className="w-3.5 h-3.5" />}
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="border-t border-borderDefault/50 bg-canvasSubtle/80 backdrop-blur-sm">
          <div className="max-w-3xl mx-auto px-4 py-3">
            <div className="relative bg-canvas/50 border border-borderDefault/50 rounded-lg focus-within:border-accent focus-within:ring-1 focus-within:ring-accent/20 transition-all focus-within:shadow-[0_0_10px_rgba(88,166,255,0.1)]">
              <div className="flex items-end gap-2 p-2">
                <textarea
                  ref={inputRef}
                  name="agent-chat-input"
                  id="agent-chat-input"
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
                  placeholder={`Ask ${selectedAgent.label}...`}
                  rows={1}
                  className="flex-1 bg-transparent text-sm text-fgDefault placeholder-fgSubtle resize-none outline-none px-2 py-1.5 min-h-[36px] max-h-[160px] disabled:opacity-40"
                />
                <VoiceButton
                  onTranscript={(text) => setInput((prev) => prev ? prev + ' ' + text : text)}
                  disabled={isStreaming}
                />
                <button
                  onClick={() => sendMessage()}
                  disabled={isStreaming || !input.trim()}
                  className="p-2 rounded-md bg-gradient-to-r from-accent to-accent/80 hover:from-accent/90 hover:to-accent/70 text-white transition-all disabled:opacity-30 disabled:cursor-not-allowed shrink-0 cursor-pointer shadow-[0_0_8px_rgba(88,166,255,0.2)]"
                >
                  {isStreaming ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                </button>
              </div>

              <div className="flex items-center justify-between px-3 pb-2 pt-0">
                <div className="relative" ref={pickerRef}>
                  <button
                    onClick={() => setShowModelPicker(!showModelPicker)}
                    className="flex items-center gap-1.5 px-2 py-1 rounded hover:bg-canvasSubtle/50 transition-colors text-xs group"
                  >
                    <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: selectedAgent.color }} />
                    <span className="text-fgMuted group-hover:text-fgDefault font-medium transition-colors">{selectedAgent.label}</span>
                    <ChevronDown className={`w-3 h-3 text-fgSubtle transition-transform ${showModelPicker ? 'rotate-180' : ''}`} />
                  </button>

                  {showModelPicker && (
                    <div className="absolute bottom-full left-0 mb-1 w-64 glass-strong rounded-md shadow-dropdown overflow-hidden z-50 flex flex-col">
                      <div className="p-2 border-b border-borderDefault/50">
                        <span className="text-[10px] font-semibold text-fgSubtle uppercase tracking-wider">Select Agent</span>
                      </div>

                      <div className="p-1 max-h-[350px] overflow-y-auto">
                        <div className="mb-1 pb-1 border-b border-borderDefault/50">
                          {AGENTS.map(agent => (
                            <div key={agent.id} className="flex items-center gap-1">
                              <button
                                onClick={() => { handleAgentChange(agent); inputRef.current?.focus(); }}
                                className={`flex-1 flex items-center gap-2.5 px-2.5 py-1.5 rounded-md transition-colors text-left text-sm ${selectedAgent.id === agent.id ? 'bg-accent/10 text-accent' : 'text-fgMuted hover:bg-canvas hover:text-fgDefault'}`}
                              >
                                <div className="w-5 h-5 rounded flex items-center justify-center shrink-0" style={{ backgroundColor: `${agent.color}15`, border: `1px solid ${agent.color}25` }}>
                                  {React.createElement(agent.icon, { className: "w-3 h-3", style: { color: agent.color } })}
                                </div>
                                <span className="text-xs font-medium">{agent.label}</span>
                                {selectedAgent.id === agent.id && <div className="ml-auto w-1.5 h-1.5 rounded-full bg-accent" />}
                              </button>
                              <button
                                onClick={() => openPromptEditor(agent.id)}
                                className="p-1 rounded text-fgSubtle hover:text-accent hover:bg-canvas transition-colors shrink-0"
                                title="Edit system prompt"
                              >
                                <Edit3 className="w-3 h-3" />
                              </button>
                            </div>
                          ))}
                        </div>

                        <div>
                          <div className="px-2.5 py-1 text-[10px] text-fgSubtle uppercase tracking-wider font-semibold">Model</div>
                          {availableModels.map((modelName) => {
                            const isSelected = selectedModel === modelName;
                            return (
                              <button
                                key={modelName}
                                onClick={() => { handleModelChange(modelName); setShowModelPicker(false); inputRef.current?.focus(); }}
                                className={`w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-md transition-colors text-left text-sm ${isSelected ? 'bg-accent/10 text-accent' : 'text-fgMuted hover:bg-canvas hover:text-fgDefault'}`}
                              >
                                <Cpu className={`w-3.5 h-3.5 shrink-0 ${isSelected ? 'text-accent' : 'text-fgSubtle'}`} />
                                <span className="text-xs font-mono truncate">{modelName}</span>
                                {isSelected && <div className="ml-auto w-1.5 h-1.5 rounded-full bg-accent" />}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                <span className="text-[10px] text-fgSubtle font-mono">
                  {selectedModel}
                </span>
              </div>
            </div>
          </div>
        </div>

        {editingPrompt && (
          <div
            className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4 backdrop-blur-sm"
            onClick={() => setEditingPrompt(null)}
          >
            <div
              className="w-full max-w-lg glass-strong rounded-lg shadow-dropdown overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between px-4 py-3 border-b border-borderDefault/50">
                <div className="flex items-center gap-2.5">
                  {(() => {
                    const agent = getAgentById(editingPrompt);
                    const color = agent?.color || '#58a6ff';
                    const Icon = agent?.icon || Cpu;
                    const label = agent?.label || 'Edit Prompt';
                    return (
                      <>
                        <div className="w-7 h-7 rounded flex items-center justify-center" style={{ backgroundColor: `${color}15`, border: `1px solid ${color}25` }}>
                          {React.createElement(Icon, { className: "w-3.5 h-3.5", style: { color } })}
                        </div>
                        <div>
                          <h3 className="text-sm font-medium text-fgDefault">{label}</h3>
                          <p className="text-[10px] text-fgSubtle">System prompt</p>
                        </div>
                      </>
                    );
                  })()}
                </div>
                <button onClick={() => setEditingPrompt(null)} className="text-fgSubtle hover:text-fgDefault transition-colors">
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="p-4">
                <textarea
                  value={promptText}
                  onChange={(e) => setPromptText(e.target.value)}
                  rows={10}
                  name="agent-prompt-editor"
                  id="agent-prompt-editor"
                  className="w-full bg-canvas/50 border border-borderDefault/50 rounded-md px-3 py-2.5 text-sm text-fgDefault placeholder-fgSubtle resize-none outline-none focus:border-accent focus:ring-1 focus:ring-accent/20 transition-colors font-mono leading-relaxed"
                  placeholder="Enter custom system prompt..."
                />
              </div>

              <div className="flex items-center justify-between px-4 py-3 border-t border-borderDefault/50 bg-canvas/50">
                <button
                  onClick={resetPrompt}
                  className="text-xs text-fgMuted hover:text-fgDefault transition-colors flex items-center gap-1.5"
                >
                  <RefreshCw className="w-3.5 h-3.5" /> Reset to default
                </button>
                <div className="flex gap-2">
                  <button onClick={() => setEditingPrompt(null)} className="btn-secondary">
                    Cancel
                  </button>
                  <button onClick={savePrompt} className="btn-primary">
                    Save
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      <ChatHistoryPanel
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={handleSelectSession}
        onCreateNew={handleCreateNew}
        onDeleteSession={handleDeleteSession}
        emptyLabel="Start your first agent chat"
      />
    </div>
  );
}
