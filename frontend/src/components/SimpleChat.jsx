import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Copy, Check, Bot, User, Loader2, RefreshCw, AlertTriangle, ChevronDown, Cpu, MessageCircle } from 'lucide-react';

export default function SimpleChat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [copiedId, setCopiedId] = useState(null);
  const scrollRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const copyText = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const sendMessage = () => {
    if (!input.trim()) return;

    const userMsg = { role: 'user', content: input, id: Date.now() };
    // For now, just add the user message — no AI response (empty, no agent connected)
    setMessages(prev => [...prev, userMsg]);
    setInput('');
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
                <MessageCircle className="w-6 h-6 text-cyan-400/60" />
              </div>
              <h2 className="text-xl font-semibold text-gray-200 mb-2">Simple Chat</h2>
              <p className="text-[13px] text-gray-600 max-w-md">
                A standalone chat interface. No agents connected yet.
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
                  /* ── AI message (placeholder for future) ── */
                  <div className="mb-6">
                    {/* Message content */}
                    <div className="text-[14px] text-gray-300 leading-[1.75] ml-1">
                      {msg.error ? (
                        <div className="flex items-start gap-3 bg-red-500/5 border border-red-500/10 rounded-xl px-4 py-3">
                          <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                          <div>
                            <p className="text-red-400 text-[13px]">Failed to get response</p>
                            <p className="text-red-400/50 text-[11px] mt-1 font-mono">{msg.error}</p>
                          </div>
                        </div>
                      ) : (
                        <>
                          {renderCodeBlocks(msg.content)}
                        </>
                      )}
                    </div>

                    {/* Actions row */}
                    {msg.content && !msg.error && (
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
                placeholder="Type a message..."
                rows={1}
                className="flex-1 bg-transparent text-[14px] text-gray-200 placeholder-gray-600 resize-none outline-none px-2 py-2 min-h-[40px] max-h-[160px]"
              />
              <button
                onClick={() => sendMessage()}
                disabled={!input.trim()}
                className="p-2.5 rounded-xl bg-white/[0.06] hover:bg-white/[0.1] text-gray-400 hover:text-white transition-all disabled:opacity-20 disabled:cursor-not-allowed shrink-0 mb-0.5"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>

            {/* Bottom controls bar */}
            <div className="flex items-center justify-between px-3 pb-2.5 pt-0.5">
              {/* Placeholder label */}
              <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[12px]">
                <div className="w-2 h-2 rounded-full bg-gray-600 shrink-0" />
                <span className="text-gray-500 font-medium">No Agent</span>
              </div>

              {/* Right side info */}
              <span className="text-[10px] text-gray-600 font-mono tracking-widest uppercase">
                STANDALONE
              </span>
            </div>
          </div>

          {/* Footer */}
          <p className="text-center text-[10px] text-gray-700 mt-3 flex items-center justify-center gap-2">
            <span className="w-1 h-1 rounded-full bg-gray-600" /> Independent Chat · No Agent Connected
          </p>
        </div>
      </div>
    </div>
  );
}
