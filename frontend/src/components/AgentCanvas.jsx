import React, { useEffect } from 'react';
import { ReactFlow, Controls, Background, useNodesState, useEdgesState } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useAgentStore } from '../store/useAgentStore';
import CustomNode from './CustomNode';
import NodeInspectorPanel from './NodeInspectorPanel';

const nodeTypes = { custom: CustomNode };

export default function AgentCanvas() {
  const { nodesState, updateNode, addTimelineEvent, selectedNodeId, configuredModels } = useAgentStore();

  const [nodes, setNodes, onNodesChange] = useNodesState([
    { id: 'input', data: { label: 'User Request', stateData: { status: 'idle', output: 'Awaiting prompt...' } }, type: 'custom', position: { x: 50, y: 150 } },
    { id: 'manager', data: { label: 'Manager AI' }, type: 'custom', position: { x: 450, y: 150 } },
    { id: 'coder', data: { label: 'Coder' }, type: 'custom', position: { x: 900, y: -20 } },
    { id: 'analyst', data: { label: 'Analyst' }, type: 'custom', position: { x: 900, y: 350 } },
    { id: 'critic', data: { label: 'Critic' }, type: 'custom', position: { x: 900, y: 720 } },
    { id: 'tool', data: { label: 'Tool Agent (FS)' }, type: 'custom', position: { x: 1350, y: -20 } },
    { id: 'executor', data: { label: 'Executor (Sandbox)' }, type: 'custom', position: { x: 1350, y: 350 } }
  ]);

  const [edges, setEdges, onEdgesChange] = useEdgesState([
    { id: 'e-in-m', source: 'input', target: 'manager', style: { stroke: '#333', strokeWidth: 2 } },
    { id: 'e-m-c', source: 'manager', target: 'coder', style: { stroke: '#333', strokeWidth: 2 } },
    { id: 'e-m-a', source: 'manager', target: 'analyst', style: { stroke: '#333', strokeWidth: 2 } },
    { id: 'e-m-cr', source: 'manager', target: 'critic', style: { stroke: '#333', strokeWidth: 2 } },
    { id: 'e-c-t', source: 'coder', target: 'tool', style: { stroke: '#333', strokeWidth: 2 } },
    { id: 'e-t-x', source: 'tool', target: 'executor', style: { stroke: '#333', strokeWidth: 2 } },
  ]);

  // Sync Global Zustand state to Nodes & Routing Edges!
  useEffect(() => {
    // Determine active route edge from manager's reasoned JSON decision if it has completed routing
    let routeTarget = null;
    try {
        if(nodesState.manager.status === 'success' && typeof nodesState.manager.output === 'string') {
            const decision = JSON.parse(nodesState.manager.output);
            if(decision) routeTarget = decision.selected_agent;
        }
    } catch(e) {}

    setNodes((nds) => nds.map((n) => {
       const baseLabel = n.id === 'manager' ? 'Manager AI' :
                         n.id === 'coder' ? 'Coder' :
                         n.id === 'analyst' ? 'Analyst' :
                         n.id === 'critic' ? 'Critic' : n.data.label;
       const label = configuredModels && configuredModels[n.id] ? `${baseLabel} (${configuredModels[n.id]})` : baseLabel;

       if(nodesState[n.id]) return { ...n, data: { ...n.data, label, stateData: nodesState[n.id] } };
       return { ...n, data: { ...n.data, label } };
    }));

    setEdges((eds) => eds.map((e) => {
        // Master edge from input -> Manager gets animated if manager is running
        if (e.id === 'e-in-m') {
            return {
                ...e, 
                animated: nodesState.manager.status === 'running',
                style: { stroke: nodesState.manager.status !== 'idle' ? '#00f0ff' : '#333', strokeWidth: 3 }
            };
        }
        
        // Output routing edges (only glow green/purple if active path or running)
        // Manager must be either executing them or selected them
        if (e.target === 'coder') {
            const isActiveRouting = (routeTarget === 'coder' || nodesState.coder.status !== 'idle');
            return {
                ...e,
                animated: nodesState.coder.status === 'running',
                style: { stroke: isActiveRouting ? '#a855f7' : '#222', strokeWidth: isActiveRouting ? 3 : 1, opacity: isActiveRouting ? 1 : 0.2 }
            };
        }

        if (e.target === 'analyst') {
            const isActiveRouting = (routeTarget === 'analyst' || nodesState.analyst?.status !== 'idle');
            return {
                ...e,
                animated: nodesState.analyst?.status === 'running',
                style: { stroke: isActiveRouting ? '#22c55e' : '#222', strokeWidth: isActiveRouting ? 3 : 1, opacity: isActiveRouting ? 1 : 0.2 }
            };
        }

        if (e.target === 'critic') {
            const isActiveRouting = (routeTarget === 'critic' || nodesState.critic?.status !== 'idle');
            return {
                ...e,
                animated: nodesState.critic?.status === 'running',
                style: { stroke: isActiveRouting ? '#f59e0b' : '#222', strokeWidth: isActiveRouting ? 3 : 1, opacity: isActiveRouting ? 1 : 0.2 }
            };
        }
        
        if (e.id === 'e-c-t') {
            const isActiveRouting = (nodesState.tool?.status !== 'idle');
            return {
                ...e,
                animated: nodesState.tool?.status === 'running',
                style: { stroke: isActiveRouting ? '#ec4899' : '#111', strokeWidth: isActiveRouting ? 3 : 1, opacity: isActiveRouting ? 1 : 0.1 }
            };
        }

        if (e.id === 'e-t-x') {
            const isActive = (nodesState.executor?.status !== 'idle');
            return {
                ...e,
                animated: nodesState.executor?.status === 'running',
                style: { stroke: isActive ? '#06b6d4' : '#111', strokeWidth: isActive ? 3 : 1, opacity: isActive ? 1 : 0.1 }
            };
        }
        
        return e;
    }));
  }, [nodesState, setNodes, setEdges, configuredModels]);

  // WebSocket global listener specifically for Timeline + Zustand state injection
  useEffect(() => {
    const ws = new WebSocket("ws://127.0.0.1:8888/ws/agent-stream");
    
    ws.onmessage = (event) => {
       const data = JSON.parse(event.data);      
       
       // Log to timeline history array
       addTimelineEvent(data);

       const { run_id, node_id, type, input, output, metadata, error } = data;

       if (type === 'start') {
           updateNode(run_id, node_id, { status: 'running', input: input || '', output: '', error: '' });
           // If manager starts, we can update the 'input node' visual to show the prompt
           if (node_id === 'manager') {
                setNodes(nds => nds.map(n => n.id === 'input' ? { ...n, data: { ...n.data, stateData: { status: 'success', output: input || "..." } } } : n));
           }
       }
       if (type === 'update') {
           updateNode(run_id, node_id, { output });
       }
       if (type === 'complete') {
           updateNode(run_id, node_id, { status: 'success', output, metadata: metadata || {} });
       }
       if (type === 'error') {
           updateNode(run_id, node_id, { status: 'error', error });
       }
    };
    
    return () => ws.close();
  }, [updateNode, addTimelineEvent, setNodes]);

  const onNodeClick = (_, node) => {
    // Save the ID of the clicked node to the store for inspect panel to catch
    useAgentStore.getState().setSelectedNode(node.id);
  };

  return (
    <div className="flex-1 h-full relative rounded-2xl glass-panel bg-black/50 border border-white/5 shadow-[inset_0_4px_30px_rgba(0,0,0,0.8)] z-10 p-1 font-mono">
       <ReactFlow 
            nodes={nodes} 
            edges={edges} 
            onNodesChange={onNodesChange} 
            onEdgesChange={onEdgesChange} 
            onNodeClick={onNodeClick}
            onPaneClick={() => useAgentStore.getState().setSelectedNode(null)}
            nodeTypes={nodeTypes} 
            fitView 
            minZoom={0.2}
            className="filter sepia-[10%] hue-rotate-15 bg-[#050505]"
       >
         <Background color="#fff" gap={24} size={1} opacity={0.07} />
         <Controls className="bg-black/90 border-white/10 rounded-lg shadow-2xl overflow-hidden [&>button]:border-white/10 [&>button]:text-gray-300 [&>button:hover]:bg-white/10" />
       </ReactFlow>

       {/* INJECT NODE INSPECTOR SIDEBAR */}
       {selectedNodeId && <NodeInspectorPanel />}
    </div>
  );
}
