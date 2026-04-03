import React, { useCallback, useEffect, useRef, useMemo } from 'react';
import { ReactFlow, Controls, Background, useNodesState, useEdgesState, addEdge } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useAgentStore } from '../store/useAgentStore';
import CustomNode from './CustomNode';
import NodeInspectorPanel from './NodeInspectorPanel';

const nodeTypes = { custom: CustomNode };

const AGENT_MODELS = {
  manager: 'qwen2.5:14b',
  coder: 'deepseek-coder-v2:16b',
  analyst: 'qwen2.5:14b',
  critic: 'devstral:24b',
  tool: 'qwen2.5-coder:7b',
  executor: 'sandbox',
};

const INITIAL_NODES = [
  { id: 'input', data: { label: 'User Request', stateData: { status: 'idle', output: 'Awaiting prompt...' } }, type: 'custom', position: { x: 50, y: 150 } },
  { id: 'manager', data: { label: `Manager AI (${AGENT_MODELS.manager})` }, type: 'custom', position: { x: 450, y: 150 } },
  { id: 'coder', data: { label: `Coder (${AGENT_MODELS.coder})` }, type: 'custom', position: { x: 900, y: -20 } },
  { id: 'analyst', data: { label: `Analyst (${AGENT_MODELS.analyst})` }, type: 'custom', position: { x: 900, y: 350 } },
  { id: 'critic', data: { label: `Critic (${AGENT_MODELS.critic})` }, type: 'custom', position: { x: 900, y: 720 } },
  { id: 'tool', data: { label: `Tool Agent (${AGENT_MODELS.tool})` }, type: 'custom', position: { x: 1350, y: -20 } },
  { id: 'executor', data: { label: `Executor (${AGENT_MODELS.executor})` }, type: 'custom', position: { x: 1350, y: 350 } }
];

const INITIAL_EDGES = [
  { id: 'e-in-m', source: 'input', target: 'manager', style: { stroke: '#333', strokeWidth: 2 } },
  { id: 'e-m-c', source: 'manager', target: 'coder', style: { stroke: '#333', strokeWidth: 2 } },
  { id: 'e-m-a', source: 'manager', target: 'analyst', style: { stroke: '#333', strokeWidth: 2 } },
  { id: 'e-m-cr', source: 'manager', target: 'critic', style: { stroke: '#333', strokeWidth: 2 } },
  { id: 'e-c-t', source: 'coder', target: 'tool', style: { stroke: '#333', strokeWidth: 2 } },
  { id: 'e-t-x', source: 'tool', target: 'executor', style: { stroke: '#333', strokeWidth: 2 } },
];

export default function AgentCanvas() {
  const { nodesState, selectedNodeId, configuredModels } = useAgentStore();

  const [nodes, setNodes, onNodesChange] = useNodesState(INITIAL_NODES);
  const [edges, setEdges, onEdgesChange] = useEdgesState(INITIAL_EDGES);

  // Sync Zustand state to node data (labels + stateData)
  useEffect(() => {
    setNodes((nds) => nds.map((n) => {
      const baseLabel = n.id === 'manager' ? `Manager AI (${AGENT_MODELS.manager})` :
                        n.id === 'coder' ? `Coder (${AGENT_MODELS.coder})` :
                        n.id === 'analyst' ? `Analyst (${AGENT_MODELS.analyst})` :
                        n.id === 'critic' ? `Critic (${AGENT_MODELS.critic})` :
                        n.id === 'tool' ? `Tool Agent (${AGENT_MODELS.tool})` :
                        n.id === 'executor' ? `Executor (${AGENT_MODELS.executor})` : n.data.label;
      const label = configuredModels && configuredModels[n.id] ? `${baseLabel} → ${configuredModels[n.id]}` : baseLabel;
      const stateData = nodesState[n.id] || n.data.stateData;
      return { ...n, data: { ...n.data, label, stateData } };
    }));
  }, [nodesState, configuredModels]);

  // Compute edge styles from state
  useEffect(() => {
    let routeTarget = null;
    try {
      if (nodesState.manager.status === 'success' && typeof nodesState.manager.output === 'string') {
        const decision = JSON.parse(nodesState.manager.output);
        if (decision && decision.selected_agent) routeTarget = decision.selected_agent;
      }
    } catch (e) {}

    setEdges((eds) => eds.map((e) => {
      if (e.id === 'e-in-m') {
        return {
          ...e,
          animated: nodesState.manager.status === 'running',
          style: { stroke: nodesState.manager.status !== 'idle' ? '#00f0ff' : '#333', strokeWidth: 3 }
        };
      }
      if (e.target === 'coder') {
        const isActive = routeTarget === 'coder' || nodesState.coder.status !== 'idle';
        return { ...e, animated: nodesState.coder.status === 'running', style: { stroke: isActive ? '#a855f7' : '#222', strokeWidth: isActive ? 3 : 1, opacity: isActive ? 1 : 0.2 } };
      }
      if (e.target === 'analyst') {
        const isActive = routeTarget === 'analyst' || nodesState.analyst?.status !== 'idle';
        return { ...e, animated: nodesState.analyst?.status === 'running', style: { stroke: isActive ? '#22c55e' : '#222', strokeWidth: isActive ? 3 : 1, opacity: isActive ? 1 : 0.2 } };
      }
      if (e.target === 'critic') {
        const isActive = routeTarget === 'critic' || nodesState.critic?.status !== 'idle';
        return { ...e, animated: nodesState.critic?.status === 'running', style: { stroke: isActive ? '#f59e0b' : '#222', strokeWidth: isActive ? 3 : 1, opacity: isActive ? 1 : 0.2 } };
      }
      if (e.id === 'e-c-t') {
        const isActive = nodesState.tool?.status !== 'idle';
        return { ...e, animated: nodesState.tool?.status === 'running', style: { stroke: isActive ? '#ec4899' : '#111', strokeWidth: isActive ? 3 : 1, opacity: isActive ? 1 : 0.1 } };
      }
      if (e.id === 'e-t-x') {
        const isActive = nodesState.executor?.status !== 'idle';
        return { ...e, animated: nodesState.executor?.status === 'running', style: { stroke: isActive ? '#06b6d4' : '#111', strokeWidth: isActive ? 3 : 1, opacity: isActive ? 1 : 0.1 } };
      }
      return e;
    }));
  }, [nodesState]);

  const onNodeClick = useCallback((_, node) => {
    useAgentStore.getState().setSelectedNode(node.id);
  }, []);

  const onConnect = useCallback((params) => {
    setEdges((eds) => addEdge({ ...params, style: { stroke: '#00f0ff', strokeWidth: 2, opacity: 0.6 } }, eds));
  }, [setEdges]);

  return (
    <div className="flex-1 h-full relative rounded-2xl glass-panel bg-black/50 border border-white/5 shadow-[inset_0_4px_30px_rgba(0,0,0,0.8),0_0_40px_rgba(0,240,255,0.05)] z-10 p-1 font-mono overflow-hidden">
      {/* Animated corner accents */}
      <div className="absolute top-0 left-0 w-16 h-16 pointer-events-none">
        <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-cyan-400/50 to-transparent" />
        <div className="absolute top-0 left-0 w-[1px] h-full bg-gradient-to-b from-cyan-400/50 to-transparent" />
      </div>
      <div className="absolute top-0 right-0 w-16 h-16 pointer-events-none">
        <div className="absolute top-0 right-0 w-full h-[1px] bg-gradient-to-l from-purple-400/50 to-transparent" />
        <div className="absolute top-0 right-0 w-[1px] h-full bg-gradient-to-b from-purple-400/50 to-transparent" />
      </div>
      <div className="absolute bottom-0 left-0 w-16 h-16 pointer-events-none">
        <div className="absolute bottom-0 left-0 w-full h-[1px] bg-gradient-to-r from-pink-400/50 to-transparent" />
        <div className="absolute bottom-0 left-0 w-[1px] h-full bg-gradient-to-t from-pink-400/50 to-transparent" />
      </div>
      <div className="absolute bottom-0 right-0 w-16 h-16 pointer-events-none">
        <div className="absolute bottom-0 right-0 w-full h-[1px] bg-gradient-to-l from-green-400/50 to-transparent" />
        <div className="absolute bottom-0 right-0 w-[1px] h-full bg-gradient-to-t from-green-400/50 to-transparent" />
      </div>
      
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        onConnect={onConnect}
        onPaneClick={() => useAgentStore.getState().setSelectedNode(null)}
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.2}
        className="filter sepia-[10%] hue-rotate-15 bg-[#050505]"
      >
        <Background color="#fff" gap={24} size={1} opacity={0.07} />
        <Controls className="bg-black/90 border-white/10 rounded-lg shadow-2xl overflow-hidden [&>button]:border-white/10 [&>button]:text-gray-300 [&>button:hover]:bg-white/10" />
      </ReactFlow>

      {selectedNodeId && <NodeInspectorPanel />}
    </div>
  );
}
