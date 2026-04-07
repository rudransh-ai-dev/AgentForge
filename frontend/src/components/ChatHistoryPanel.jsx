import React, { useState } from 'react';
import { Plus, Trash2, MessageSquare, Clock, ChevronLeft, ChevronRight } from 'lucide-react';

function formatTime(ts) {
  const d = new Date(ts);
  const now = new Date();
  const diffMs = now - d;
  const diffMin = Math.floor(diffMs / 60000);
  const diffHr = Math.floor(diffMs / 3600000);
  const diffDay = Math.floor(diffMs / 86400000);
  if (diffMin < 1) return 'Just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHr < 24) return `${diffHr}h ago`;
  if (diffDay < 7) return `${diffDay}d ago`;
  return d.toLocaleDateString();
}

export default function ChatHistoryPanel({
  sessions,
  activeSessionId,
  onSelectSession,
  onCreateNew,
  onDeleteSession,
  emptyLabel = 'No conversations yet',
}) {
  const [collapsed, setCollapsed] = useState(false);

  if (collapsed) {
    return (
      <div className="h-full shrink-0 flex">
        <button
          onClick={() => setCollapsed(false)}
          className="w-6 h-full bg-canvasSubtle/60 border-l border-borderDefault/50 flex items-center justify-center text-fgSubtle hover:text-accent hover:bg-canvasSubtle transition-all"
          title="Show chat history"
        >
          <ChevronLeft className="w-3.5 h-3.5" />
        </button>
      </div>
    );
  }

  return (
    <div className="h-full flex shrink-0 transition-all">
      <div className="w-64 h-full bg-canvasSubtle/80 border-l border-borderDefault/50 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-3 py-2.5 border-b border-borderDefault/50">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-3.5 h-3.5 text-accent" />
            <span className="text-xs font-semibold text-fgDefault">Chat History</span>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={onCreateNew}
              className="p-1 rounded hover:bg-canvas/50 text-fgSubtle hover:text-accent transition-colors"
              title="New chat"
            >
              <Plus className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setCollapsed(true)}
              className="p-1 rounded hover:bg-canvas/50 text-fgSubtle hover:text-accent transition-colors"
              title="Hide chat history"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Sessions list */}
        <div className="flex-1 overflow-y-auto">
          {sessions.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full px-4 text-center">
              <MessageSquare className="w-8 h-8 text-fgSubtle/30 mb-2" />
              <p className="text-xs text-fgSubtle">{emptyLabel}</p>
            </div>
          ) : (
            <div className="p-1.5 space-y-0.5">
              {sessions.map((session) => {
                const isActive = session.id === activeSessionId;
                return (
                  <div
                    key={session.id}
                    className={`group flex items-start gap-2 px-2.5 py-2 rounded-md cursor-pointer transition-all ${
                      isActive
                        ? 'bg-accent/10 border border-accent/20'
                        : 'hover:bg-canvas/50 border border-transparent'
                    }`}
                    onClick={() => onSelectSession(session.id)}
                  >
                    <div className="flex-1 min-w-0 mt-0.5">
                      <p className={`text-xs font-medium truncate ${isActive ? 'text-accent' : 'text-fgDefault'}`}>
                        {session.title}
                      </p>
                      <div className="flex items-center gap-1.5 mt-1">
                        <Clock className="w-2.5 h-2.5 text-fgSubtle" />
                        <span className="text-[10px] text-fgSubtle">{formatTime(session.createdAt)}</span>
                      </div>
                      {session.agent && (
                        <div className="flex items-center gap-1 mt-1">
                          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: session.agent.color }} />
                          <span className="text-[10px] text-fgSubtle truncate">{session.agent.label}</span>
                        </div>
                      )}
                      {session.persona && (
                        <div className="flex items-center gap-1 mt-1">
                          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: session.persona.color }} />
                          <span className="text-[10px] text-fgSubtle truncate">{session.persona.label}</span>
                        </div>
                      )}
                      {session.model && (
                        <span className="text-[9px] text-fgSubtle font-mono mt-0.5 block truncate">{session.model}</span>
                      )}
                      {session.mode && (
                        <span className="text-[9px] text-fgSubtle uppercase tracking-wider mt-0.5 block">{session.mode}</span>
                      )}
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteSession(session.id);
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-danger/10 text-fgSubtle hover:text-danger transition-all shrink-0 mt-0.5"
                      title="Delete conversation"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
