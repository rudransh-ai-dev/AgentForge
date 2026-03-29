import React, { useState, useRef, useEffect } from 'react';
import { Send, Copy, Check, Bot, User, Sparkles, ArrowLeft } from 'lucide-react';

const API = "http://127.0.0.1:8888";

const AGENTS = {
  coder:   { label: "Coder Agent",  model: "DeepSeek-6.7B", color: "#a855f7", gradient: "from-purple-500/20 to-purple-900/10" },
  analyst: { label: "Analyst",      model: "Phi-3-Mini",     color: "#22c55e", gradient: "from-green-500/20 to-green-900/10" },
  critic:  { label: "Critic",       model: "Llama-3",        color: "#f59e0b", gradient: "from-amber-500/20 to-amber-900/10" },
  manager: { label: "Manager AI",   model: "Llama-3-8B",     color: "#06b6d4", gradient: "from-cyan-500/20 to-cyan-900/10" },
};

export default function AgentChat({ initialAgent }) {
  const [activeAgent, setActiveAgent] = useState(initialAgent || null);
  const [messages, setMessages] = useState({});
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [copiedId, setCopiedId] = useState(null);
  const scrollRef = useRef(null);

  const agentMessages = messages[activeAgent] || [];

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [agentMessages]);

  const copyText = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const sendMessage = async () => {
    if (!input.trim() || !activeAgent || isStreaming) return;

    const userMsg = { role: 'user', content: input, id: Date.now() };
    const aiMsg = { role: 'assistant', content: '', id: Date.now() + 1, streaming: true };

    setMessages(prev => ({
      ...prev,
      [activeAgent]: [...(prev[activeAgent] || []), userMsg, aiMsg]
    }));
    setInput('');
    setIsStreaming(true);

    try {
      const res = await fetch(`${API}/agent/${activeAgent}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: input })
      });

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
                const agentMsgs = [...(prev[activeAgent] || [])];
                const lastIdx = agentMsgs.length - 1;
                agentMsgs[lastIdx] = { ...agentMsgs[lastIdx], content: fullText };
                return { ...prev, [activeAgent]: agentMsgs };
              });
            }
          } catch (e) {}
        }
      }

      // Mark as done
      setMessages(prev => {
        const agentMsgs = [...(prev[activeAgent] || [])];
        const lastIdx = agentMsgs.length - 1;
        agentMsgs[lastIdx] = { ...agentMsgs[lastIdx], streaming: false };
        return { ...prev, [activeAgent]: agentMsgs };
      });
    } catch (err) {
      setMessages(prev => {
        const agentMsgs = [...(prev[activeAgent] || [])];
        const lastIdx = agentMsgs.length - 1;
        agentMsgs[lastIdx] = { ...agentMsgs[lastIdx], content: `Error: ${err.message}`, streaming: false };
        return { ...prev, [activeAgent]: agentMsgs };
      });
    } finally {
      setIsStreaming(false);
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
          <div key={i} className="relative my-3 group/code">
            <div className="flex items-center justify-between bg-[#1a1a2e] px-3 py-1.5 rounded-t-lg border border-white/5 border-b-0">
              <span className="text-[9px] text-gray-500 uppercase tracking-widest font-bold">{lang || 'code'}</span>
              <button
                onClick={() => copyText(code, blockId)}
                className="text-gray-500 hover:text-cyan-400 transition-colors"
              >
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

  // Agent selector view
  if (!activeAgent) {
    return (
      <div className="flex-1 h-full flex items-center justify-center">
        <div className="max-w-2xl w-full px-8">
          <div className="text-center mb-12">
            <Sparkles className="w-10 h-10 text-cyan-400 mx-auto mb-4 opacity-60" />
            <h2 className="text-2xl font-bold text-white mb-2">Agent Chat</h2>
            <p className="text-sm text-gray-500">Select an agent to start a direct conversation</p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {Object.entries(AGENTS).map(([id, agent]) => (
              <button
                key={id}
                onClick={() => setActiveAgent(id)}
                className={`p-6 rounded-2xl border border-white/10 bg-gradient-to-br ${agent.gradient} hover:border-white/20 transition-all duration-300 text-left group hover:scale-[1.02] hover:shadow-xl`}
              >
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: agent.color, boxShadow: `0 0 12px ${agent.color}40` }} />
                  <span className="font-bold text-white text-sm">{agent.label}</span>
                </div>
                <p className="text-[11px] text-gray-500 font-mono">{agent.model}</p>
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  const agentInfo = AGENTS[activeAgent];

  // Chat view
  return (
    <div className="flex-1 h-full flex flex-col bg-[#070709]">
      {/* Chat header */}
      <div className="h-14 border-b border-white/10 flex items-center gap-4 px-5 bg-black/40">
        <button onClick={() => setActiveAgent(null)} className="text-gray-500 hover:text-white transition-colors">
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: agentInfo.color, boxShadow: `0 0 10px ${agentInfo.color}50` }} />
        <div>
          <span className="font-bold text-sm text-white">{agentInfo.label}</span>
          <span className="text-[10px] text-gray-500 font-mono ml-2">{agentInfo.model}</span>
        </div>
        {isStreaming && <div className="ml-auto text-[10px] text-cyan-400 animate-pulse font-mono">streaming...</div>}
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-6">
        {agentMessages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-gray-600">
              <Bot className="w-12 h-12 mx-auto mb-4 opacity-20" />
              <p className="text-sm">Start chatting with {agentInfo.label}</p>
              <p className="text-[10px] text-gray-700 mt-1">Messages are streamed in real-time from your local model</p>
            </div>
          </div>
        )}

        {agentMessages.map((msg) => (
          <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
            <div className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${
              msg.role === 'user'
                ? 'bg-gradient-to-br from-blue-500/20 to-blue-900/20 border border-blue-500/20'
                : `bg-gradient-to-br ${agentInfo.gradient} border border-white/10`
            }`}>
              {msg.role === 'user' ? <User className="w-4 h-4 text-blue-400" /> : <Bot className="w-4 h-4" style={{ color: agentInfo.color }} />}
            </div>
            <div className={`max-w-[80%] ${msg.role === 'user' ? 'text-right' : ''}`}>
              <div className={`inline-block rounded-2xl px-4 py-3 text-[13px] leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-blue-500/10 border border-blue-500/20 text-blue-100'
                  : 'bg-[#0c0c14] border border-white/5 text-gray-300'
              }`}>
                {msg.role === 'assistant' ? renderCodeBlocks(msg.content) : msg.content}
                {msg.streaming && <span className="inline-block w-1.5 h-4 bg-cyan-400 animate-pulse ml-1 rounded-sm" />}
              </div>
              {msg.role === 'assistant' && !msg.streaming && msg.content && (
                <div className="mt-1.5 flex gap-2">
                  <button
                    onClick={() => copyText(msg.content, msg.id)}
                    className="text-[9px] text-gray-600 hover:text-gray-300 flex items-center gap-1 transition-colors"
                  >
                    {copiedId === msg.id ? <><Check className="w-2.5 h-2.5 text-green-400" /> Copied</> : <><Copy className="w-2.5 h-2.5" /> Copy</>}
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Input */}
      <div className="border-t border-white/10 p-4 bg-black/30">
        <div className="flex items-center gap-3 max-w-4xl mx-auto">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
            disabled={isStreaming}
            placeholder={`Message ${agentInfo.label}...`}
            className="flex-1 bg-[#0a0a12] border border-white/10 rounded-xl py-3 px-4 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-cyan-500/30 disabled:opacity-50"
          />
          <button
            onClick={sendMessage}
            disabled={isStreaming || !input.trim()}
            className="p-3 rounded-xl bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-500/20 text-cyan-400 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
