import React, { useState, useEffect, useCallback } from 'react';
import { ReactFlow, Controls, Background, useNodesState, useEdgesState, addEdge, useReactFlow, ReactFlowProvider } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Maximize2, Minimize2 } from 'lucide-react';
import { useAgentStore } from '../store/useAgentStore';
import CustomNode from './CustomNode';
import NodeInspectorPanel from './NodeInspectorPanel';

const nodeTypes = { custom: CustomNode };

const AGENT_MODELS = {
  manager: 'llama3.1:8b',
  specifier: 'llama3.1:8b',
  writer: 'qwen2.5-coder:14b',
  editor: 'qwen2.5-coder:14b',
  tester: 'llama3.1:8b',
  researcher: 'qwen2.5:14b',
  heavy: 'codestral:22b',
  context_manager: 'llama3.1:8b',
  tool: 'llama3.1:8b',
  executor: 'sandbox',
};

const INITIAL_NODES = [
  { id: 'input', data: { label: 'User Input', stateData: { status: 'idle', output: '', input: '', error: '', metadata: {} } }, type: 'custom', position: { x: 50, y: 300 } },
  { id: 'specifier', data: { label: 'Spec Agent', model: AGENT_MODELS.specifier, stateData: { status: 'idle', output: '', input: '', error: '', metadata: {} } }, type: 'custom', position: { x: 300, y: 300 } },
  { id: 'manager', data: { label: 'Orchestrator', model: AGENT_MODELS.manager, stateData: { status: 'idle', output: '', input: '', error: '', metadata: {} } }, type: 'custom', position: { x: 500, y: 300 } },
  { id: 'writer', data: { label: 'Senior Coder', model: AGENT_MODELS.writer, stateData: { status: 'idle', output: '', input: '', error: '', metadata: {} } }, type: 'custom', position: { x: 650, y: 100 } },
  { id: 'editor', data: { label: 'Code Editor', model: AGENT_MODELS.editor, stateData: { status: 'idle', output: '', input: '', error: '', metadata: {} } }, type: 'custom', position: { x: 650, y: 250 } },
  { id: 'tester', data: { label: 'QA Tester', model: AGENT_MODELS.tester, stateData: { status: 'idle', output: '', input: '', error: '', metadata: {} } }, type: 'custom', position: { x: 650, y: 400 } },
  { id: 'researcher', data: { label: 'Researcher', model: AGENT_MODELS.researcher, stateData: { status: 'idle', output: '', input: '', error: '', metadata: {} } }, type: 'custom', position: { x: 650, y: 550 } },
  { id: 'heavy', data: { label: 'System Architect', model: AGENT_MODELS.heavy, stateData: { status: 'idle', output: '', input: '', error: '', metadata: {} } }, type: 'custom', position: { x: 950, y: 600 } },
  { id: 'tool', data: { label: 'Tool Mgr', model: AGENT_MODELS.tool, stateData: { status: 'idle', output: '', input: '', error: '', metadata: {} } }, type: 'custom', position: { x: 1000, y: 250 } },
  { id: 'executor', data: { label: 'Executor', model: AGENT_MODELS.executor, stateData: { status: 'idle', output: '', input: '', error: '', metadata: {} } }, type: 'custom', position: { x: 1250, y: 250 } },
];

const INITIAL_EDGES = [
  { id: 'e-in-spec', source: 'input', target: 'specifier' },
  { id: 'e-spec-m', source: 'specifier', target: 'manager' },
  { id: 'e-m-w', source: 'manager', target: 'writer' },
  { id: 'e-m-res', source: 'manager', target: 'researcher' },
  { id: 'e-m-heavy', source: 'manager', target: 'heavy' },
  { id: 'e-w-e', source: 'writer', target: 'editor' },
  { id: 'e-e-t', source: 'editor', target: 'tester' },
  { id: 'e-t-e', source: 'tester', target: 'editor', animated: true, style: { strokeDasharray: '4,4', stroke: '#d29922' } },
  { id: 'e-e-tool', source: 'editor', target: 'tool' },
  { id: 'e-tool-x', source: 'tool', target: 'executor' },
];

function CanvasInner({ isFullscreen, setIsFullscreen }) {
  const { nodesState, selectedNodeId, activeRunId } = useAgentStore();
  const [nodes, setNodes, onNodesChange] = useNodesState(INITIAL_NODES);
  const [edges, setEdges, onEdgesChange] = useEdgesState(INITIAL_EDGES);
  const [rfInstance, setRfInstance] = useState(null);
  const { deleteElements } = useReactFlow();

  // Sync runtime store state into node data
  useEffect(() => {
    setNodes(nds => nds.map(n => {
      const storeState = nodesState[n.id];
      if (storeState) {
        return { ...n, data: { ...n.data, stateData: storeState } };
      }
      return n;
    }));
  }, [nodesState]);

  // Animate edges based on active pipeline
  useEffect(() => {
    let routeTarget = null;
    try {
      if (nodesState.manager?.status === 'success' && typeof nodesState.manager.output === 'string') {
        const d = JSON.parse(nodesState.manager.output);
        if (d?.selected_agent) routeTarget = d.selected_agent;
      }
    } catch (e) {
      // ignore
    }

    setEdges(eds => eds.map(e => {
      const glow = (color, rgb) => ({
        stroke: color, strokeWidth: 2,
        filter: `drop-shadow(0 0 6px rgba(${rgb},0.8))`
      });
      const dim = { stroke: '#21262d', strokeWidth: 1, opacity: 0.35, filter: 'none' };
      if (e.id === 'e-in-spec') {
        const active = nodesState.specifier?.status !== 'idle';
        return { ...e, animated: nodesState.specifier?.status === 'running', style: active ? glow('#10b981', '16,185,129') : { stroke: '#30363d', strokeWidth: 1.5 } };
      }
      if (e.id === 'e-spec-m') {
        const active = nodesState.manager?.status !== 'idle' || nodesState.specifier?.status === 'success';
        return { ...e, animated: nodesState.manager?.status === 'running', style: active ? glow('#58a6ff', '88,166,255') : { stroke: '#30363d', strokeWidth: 1.5 } };
      }
      const targetAgent = e.target;
      const ns = nodesState[targetAgent];
      if (['writer', 'editor', 'tester', 'researcher', 'heavy'].includes(targetAgent)) {
        const isActive = routeTarget === targetAgent || ns?.status !== 'idle';
        const colors = { writer: ['#a371f7', '163,113,247'], editor: ['#db2777', '219,39,119'], tester: ['#d29922', '210,153,34'], researcher: ['#3fb950', '63,185,80'], heavy: ['#6366f1', '99,102,241'] };
        const [c, rgb] = colors[targetAgent] || ['#58a6ff', '88,166,255'];
        return { ...e, animated: ns?.status === 'running', style: isActive ? glow(c, rgb) : dim };
      }
      if (e.id === 'e-e-tool') {
        const isActive = nodesState.tool?.status !== 'idle';
        return { ...e, animated: nodesState.tool?.status === 'running', style: isActive ? glow('#db61a2', '219,97,162') : dim };
      }
      if (e.id === 'e-tool-x') {
        const isActive = nodesState.executor?.status !== 'idle';
        return { ...e, animated: nodesState.executor?.status === 'running', style: isActive ? glow('#58a6ff', '88,166,255') : dim };
      }
      return e;
    }));
  }, [nodesState]);

  const onNodeClick = useCallback((_, node) => {
    useAgentStore.getState().setSelectedNode(node.id);
  }, []);

  const onConnect = useCallback((params) => {
    setEdges(eds => addEdge({
      ...params,
      style: { stroke: '#58a6ff', strokeWidth: 2, opacity: 0.7, filter: 'drop-shadow(0 0 4px rgba(88,166,255,0.5))' }
    }, eds));
  }, [setEdges]);

  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback((event) => {
    event.preventDefault();
    const type = event.dataTransfer.getData('application/reactflow');
    const label = event.dataTransfer.getData('application/reactflow-label');
    const model = event.dataTransfer.getData('application/reactflow-model');
    if (!type || !rfInstance) return;
    const position = rfInstance.screenToFlowPosition({ x: event.clientX, y: event.clientY });
    const newNode = {
      id: `node-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`,
      type,
      position,
      data: { label, model: model || '', stateData: { status: 'idle', output: '', input: '', error: '', metadata: {} } },
    };
    setNodes(nds => nds.concat(newNode));
  }, [rfInstance, setNodes]);

  // Delete selected node with Backspace/Delete
  useEffect(() => {
    const handleKey = (e) => {
      if ((e.key === 'Delete' || e.key === 'Backspace') && selectedNodeId) {
        const active = document.activeElement;
        if (active && (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA')) return;
        deleteElements({ nodes: [{ id: selectedNodeId }] });
        useAgentStore.getState().setSelectedNode(null);
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [selectedNodeId, deleteElements]);

  // Reset all nodes to idle when a new run starts
  useEffect(() => {
    if (activeRunId) {
      setNodes(nds => nds.map(n => ({
        ...n,
        data: { ...n.data, stateData: { status: 'idle', output: '', input: '', error: '', metadata: {} } },
      })));
    }
  }, [activeRunId]);

  return (
    <div className="flex-1 h-full relative rounded-lg overflow-hidden border border-[#58a6ff]/20 shadow-[inset_0_0_60px_rgba(88,166,255,0.04)]">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        onConnect={onConnect}
        onInit={setRfInstance}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onPaneClick={() => useAgentStore.getState().setSelectedNode(null)}
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.1}
        deleteKeyCode={null}
        className="gradient-bg-animated"
        proOptions={{ hideAttribution: true }}
      >
        <Background color="rgba(88,166,255,0.12)" gap={28} size={1.2} variant="cross" />
        <Controls className="glass-strong border border-[#30363d]/50 rounded-lg overflow-hidden [&>button]:border-[#30363d]/50 [&>button]:text-[#8b949e] [&>button:hover]:bg-[#161b22] [&>button:hover]:text-[#c9d1d9]" />
      </ReactFlow>

      <button
        onClick={() => setIsFullscreen(!isFullscreen)}
        className="absolute top-2 right-2 z-20 p-1.5 rounded glass-strong border border-[#30363d]/50 text-[#6e7681] hover:text-[#c9d1d9] hover:border-[#58a6ff]/40 transition-all"
        title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen canvas'}
      >
        {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
      </button>

      {selectedNodeId && <NodeInspectorPanel />}
    </div>
  );
}

export default function AgentCanvas({ isFullscreen, setIsFullscreen }) {
  return (
    <ReactFlowProvider>
      <CanvasInner isFullscreen={isFullscreen} setIsFullscreen={setIsFullscreen} />
    </ReactFlowProvider>
  );
}
