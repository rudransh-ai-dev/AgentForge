import React, { useState } from 'react';
import {
  Cpu, FileCode2, Zap, MessageSquare, BrainCircuit,
  ChevronLeft, ChevronRight, Layers, Plus, Wrench, Sparkles
} from 'lucide-react';
import { useAgentStore } from '../store/useAgentStore';

const NODE_TYPES = [
  {
    type: 'custom',
    label: 'User Input',
    icon: MessageSquare,
    color: '#58a6ff',
    description: 'Trigger point — feeds text into the pipeline',
  },
  {
    type: 'custom',
    label: 'Orchestrator',
    icon: Cpu,
    color: '#06b6d4',
    description: 'Manager — routes tasks & creates execution plans',
    model: 'llama3.1:8b',
  },
  {
    type: 'custom',
    label: 'Senior Coder',
    icon: FileCode2,
    color: '#a855f7',
    description: 'Writer agent — drafts full-stack code',
    model: 'qwen2.5-coder:14b',
  },
  {
    type: 'custom',
    label: 'Code Editor',
    icon: FileCode2,
    color: '#db2777',
    description: 'Editor agent — refines & fixes code',
    model: 'qwen2.5-coder:14b',
  },
  {
    type: 'custom',
    label: 'QA Tester',
    icon: Zap,
    color: '#d29922',
    description: 'Tester agent — adversarial QA validation',
    model: 'deepseek-r1:8b',
  },
  {
    type: 'custom',
    label: 'Researcher',
    icon: BrainCircuit,
    color: '#3fb950',
    description: 'Research & data synthesis agent',
    model: 'qwen2.5:14b',
  },
  {
    type: 'custom',
    label: 'Tool Mgr',
    icon: Wrench,
    color: '#db61a2',
    description: 'File system, deps & project structure',
  },
  {
    type: 'custom',
    label: 'System Architect',
    icon: BrainCircuit,
    color: '#6366f1',
    description: 'Heavy brain for complex architecture',
    model: 'phi4:latest',
  },
];

export default function NodeSidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const { availableModels, customAgents } = useAgentStore();

  const onDragStart = (event, nodeType, label) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.setData('application/reactflow-label', label);
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div
      className={`flex flex-col glass-strong border border-[#30363d]/50 rounded-lg h-full transition-all duration-200 overflow-hidden ${
        collapsed ? 'w-10' : 'w-52'
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-2 py-2 border-b border-[#21262d] shrink-0">
        {!collapsed && (
          <div className="flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-[#58a6ff]" />
            <span className="text-xs font-semibold text-[#c9d1d9]">Nodes</span>
          </div>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className={`p-1 rounded hover:bg-[#21262d] text-[#6e7681] hover:text-[#c9d1d9] transition-colors ${collapsed ? 'mx-auto' : ''}`}
          title={collapsed ? 'Expand palette' : 'Collapse palette'}
        >
          {collapsed ? <ChevronRight className="w-3.5 h-3.5" /> : <ChevronLeft className="w-3.5 h-3.5" />}
        </button>
      </div>

      {/* Node list */}
      {!collapsed && (
        <div className="flex-1 overflow-y-auto p-1.5 space-y-1">
          <p className="text-[9px] text-[#484f58] uppercase tracking-wider font-medium px-1 pt-1 pb-0.5">Drag to canvas</p>

          {NODE_TYPES.map((node) => {
            const Icon = node.icon;
            return (
              <div
                key={node.label}
                onDragStart={(event) => onDragStart(event, node.type, node.label)}
                draggable
                className="flex items-center gap-2.5 px-2 py-2 rounded-md border border-[#21262d] bg-[#0d1117]/60 hover:bg-[#161b22] hover:border-[#30363d] cursor-grab active:cursor-grabbing transition-all group select-none"
                title={node.description}
              >
                <div
                  className="p-1.5 rounded shrink-0"
                  style={{ backgroundColor: `${node.color}18`, border: `1px solid ${node.color}30` }}
                >
                  <Icon className="w-3.5 h-3.5" style={{ color: node.color }} />
                </div>
                <div className="min-w-0">
                  <div className="text-[11px] font-medium text-[#c9d1d9] truncate">{node.label}</div>
                  <div className="text-[9px] text-[#484f58] leading-tight line-clamp-1">{node.description}</div>
                </div>
                <Plus className="w-3 h-3 text-[#484f58] group-hover:text-[#58a6ff] shrink-0 ml-auto transition-colors" />
              </div>
            );
          })}

          {/* Custom agents section */}
          {customAgents.length > 0 && (
            <>
              <p className="text-[9px] text-[#484f58] uppercase tracking-wider font-medium px-1 pt-3 pb-0.5">Your Agents</p>
              {customAgents.map((agent) => (
                <div
                  key={agent.id}
                  onDragStart={(event) => {
                    event.dataTransfer.setData('application/reactflow', 'custom');
                    event.dataTransfer.setData('application/reactflow-label', agent.name);
                    event.dataTransfer.setData('application/reactflow-model', agent.model);
                  }}
                  draggable
                  className="flex items-center gap-2.5 px-2 py-2 rounded-md border border-[#21262d] bg-[#0d1117]/60 hover:bg-[#161b22] hover:border-[#30363d] cursor-grab active:cursor-grabbing transition-all group select-none"
                  title={agent.system_prompt?.slice(0, 80) || agent.name}
                >
                  <div
                    className="p-1.5 rounded shrink-0"
                    style={{ backgroundColor: `${agent.color || '#58a6ff'}18`, border: `1px solid ${agent.color || '#58a6ff'}30` }}
                  >
                    <Sparkles className="w-3.5 h-3.5" style={{ color: agent.color || '#58a6ff' }} />
                  </div>
                  <div className="min-w-0">
                    <div className="text-[11px] font-medium text-[#c9d1d9] truncate">{agent.name}</div>
                    <div className="text-[9px] text-[#484f58] leading-tight line-clamp-1 font-mono">{agent.model}</div>
                  </div>
                  <Plus className="w-3 h-3 text-[#484f58] group-hover:text-[#58a6ff] shrink-0 ml-auto transition-colors" />
                </div>
              ))}
            </>
          )}

          {/* Saved agents section */}
          {availableModels.length > 0 && (
            <>
              <p className="text-[9px] text-[#484f58] uppercase tracking-wider font-medium px-1 pt-3 pb-0.5">Quick Model Nodes</p>
              {availableModels.slice(0, 5).map((model) => (
                <div
                  key={model}
                  onDragStart={(event) => {
                    event.dataTransfer.setData('application/reactflow', 'custom');
                    event.dataTransfer.setData('application/reactflow-label', model.split(':')[0]);
                    event.dataTransfer.setData('application/reactflow-model', model);
                  }}
                  draggable
                  className="flex items-center gap-2 px-2 py-1.5 rounded-md border border-[#21262d] bg-[#0d1117]/40 hover:bg-[#161b22] hover:border-[#30363d] cursor-grab active:cursor-grabbing transition-all group select-none"
                >
                  <div className="p-1 rounded bg-[#a371f7]/10 border border-[#a371f7]/20 shrink-0">
                    <BrainCircuit className="w-3 h-3 text-[#a371f7]" />
                  </div>
                  <span className="text-[10px] text-[#8b949e] font-mono truncate">{model}</span>
                  <Plus className="w-3 h-3 text-[#484f58] group-hover:text-[#a371f7] shrink-0 ml-auto transition-colors" />
                </div>
              ))}
            </>
          )}
        </div>
      )}

      {/* Collapsed icon column */}
      {collapsed && (
        <div className="flex flex-col items-center py-2 gap-1.5 overflow-y-auto">
          {NODE_TYPES.map((node) => {
            const Icon = node.icon;
            return (
              <div
                key={node.label}
                onDragStart={(event) => onDragStart(event, node.type, node.label)}
                draggable
                className="p-1.5 rounded-md border border-[#21262d] bg-[#0d1117]/60 hover:bg-[#161b22] cursor-grab active:cursor-grabbing transition-all"
                title={node.label}
              >
                <Icon className="w-4 h-4" style={{ color: node.color }} />
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
