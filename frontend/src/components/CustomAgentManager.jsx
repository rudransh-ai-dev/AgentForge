import React, { useState, useEffect, useRef } from 'react';
import { Plus, Trash2, Edit3, Send, Copy, Check, Loader2, X, RefreshCw, Cpu, ChevronDown } from 'lucide-react';

const API = "http://127.0.0.1:8888";

const AGENT_COLORS = ['#58a6ff', '#3fb950', '#f85149', '#d29922', '#a371f7', '#db61a2', '#79c0ff', '#7ee787', '#ffa657', '#ff7b72'];

export default function CustomAgentManager() {
  const [agents, setAgents] = useState([]);
  const [availableModels, setAvailableModels] = useState([]);
  const [editingAgent, setEditingAgent] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({ name: '', model: '', system_prompt: '', color: AGENT_COLORS[0], icon: 'Cpu' });
  const [testingAgent, setTestingAgent] = useState(null);
  const [testInput, setTestInput] = useState('');
  const [testOutput, setTestOutput] = useState('');
  const [testStreaming, setTestStreaming] = useState(false);
  const [copiedId, setCopiedId] = useState(null);
  const [showModelPicker, setShowModelPicker] = useState(false);
  const pickerRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    fetchAgents();
    fetch(`${API}/health`).then(r => r.json()).then(d => {
      if (d.models) setAvailableModels(d.models);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    const handleClick = (e) => {
      if (pickerRef.current && !pickerRef.current.contains(e.target)) {
        setShowModelPicker(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const fetchAgents = async () => {
    try {
      const res = await fetch(`${API}/custom-agents`);
      const data = await res.json();
      setAgents(data.agents || []);
    } catch (e) {
      setAgents([]);
    }
  };

  const handleSubmit = async () => {
    if (!formData.name || !formData.model || !formData.system_prompt) return;

    const url = editingAgent ? `${API}/custom-agents/${editingAgent.id}` : `${API}/custom-agents`;
    const method = editingAgent ? 'PUT' : 'POST';

    try {
      await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      fetchAgents();
      resetForm();
    } catch (e) {
      console.error("Failed to save agent", e);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Delete this agent?')) return;
    try {
      await fetch(`${API}/custom-agents/${id}`, { method: 'DELETE' });
      fetchAgents();
      if (testingAgent?.id === id) setTestingAgent(null);
    } catch (e) {
      console.error("Failed to delete agent", e);
    }
  };

  const handleEdit = (agent) => {
    setEditingAgent(agent);
    setFormData({
      name: agent.name,
      model: agent.model,
      system_prompt: agent.system_prompt,
      color: agent.color || AGENT_COLORS[0],
      icon: agent.icon || 'Cpu',
    });
    setShowForm(true);
  };

  const resetForm = () => {
    setEditingAgent(null);
    setShowForm(false);
    setFormData({ name: '', model: '', system_prompt: '', color: AGENT_COLORS[0], icon: 'Cpu' });
  };

  const copyText = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const testAgent = async () => {
    if (!testInput.trim() || !testingAgent || testStreaming) return;
    setTestOutput('');
    setTestStreaming(true);

    try {
      const res = await fetch(`${API}/agent/custom-${testingAgent.id}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: testInput,
          model: testingAgent.model,
          custom_prompt: testingAgent.system_prompt,
        }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

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
              setTestOutput(fullText);
            }
          } catch (e) {}
        }
      }
    } catch (err) {
      setTestOutput(`Error: ${err.message}`);
    } finally {
      setTestStreaming(false);
    }
  };

  return (
    <div className="flex-1 h-full overflow-y-auto p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gradient-accent">Custom Agents</h2>
        <button onClick={() => { resetForm(); setShowForm(true); }} className="btn-primary text-xs flex items-center gap-1.5">
          <Plus className="w-3.5 h-3.5" /> New Agent
        </button>
      </div>

      {showForm && (
        <div className="glass border border-borderDefault/50 rounded-lg p-4 space-y-3 card-hover">
          <h3 className="text-sm font-medium text-fgDefault">{editingAgent ? 'Edit Agent' : 'Create Agent'}</h3>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-fgSubtle mb-1 block">Name</label>
              <input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="input-field w-full"
                placeholder="My Agent"
              />
            </div>
            <div>
              <label className="text-xs text-fgSubtle mb-1 block">Model</label>
              <div className="relative" ref={pickerRef}>
                <button
                  onClick={() => setShowModelPicker(!showModelPicker)}
                  className="input-field w-full flex items-center justify-between"
                >
                  <span className={formData.model ? 'text-fgDefault' : 'text-fgSubtle'}>
                    {formData.model || 'Select model'}
                  </span>
                  <ChevronDown className="w-3 h-3 text-fgSubtle" />
                </button>
                {showModelPicker && (
                  <div className="absolute top-full left-0 right-0 mt-1 glass-strong rounded-md shadow-dropdown z-50 max-h-48 overflow-y-auto">
                    {availableModels.map(m => (
                      <button
                        key={m}
                        onClick={() => { setFormData({ ...formData, model: m }); setShowModelPicker(false); }}
                        className={`w-full text-left text-xs px-3 py-2 hover:bg-canvas/50 transition-colors font-mono ${formData.model === m ? 'text-accent' : 'text-fgDefault'}`}
                      >
                        {m}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          <div>
            <label className="text-xs text-fgSubtle mb-1 block">System Prompt</label>
            <textarea
              value={formData.system_prompt}
              onChange={(e) => setFormData({ ...formData, system_prompt: e.target.value })}
              className="input-field w-full font-mono text-xs"
              rows={5}
              placeholder="You are a helpful assistant..."
            />
          </div>

          <div>
            <label className="text-xs text-fgSubtle mb-1 block">Color</label>
            <div className="flex gap-1.5">
              {AGENT_COLORS.map(c => (
                <button
                  key={c}
                  onClick={() => setFormData({ ...formData, color: c })}
                  className={`w-6 h-6 rounded-full border-2 transition-all ${formData.color === c ? 'border-fgDefault scale-110 shadow-[0_0_8px_rgba(255,255,255,0.2)]' : 'border-transparent hover:scale-105'}`}
                  style={{ backgroundColor: c }}
                />
              ))}
            </div>
          </div>

          <div className="flex items-center justify-end gap-2 pt-2">
            <button onClick={resetForm} className="btn-secondary text-xs">Cancel</button>
            <button onClick={handleSubmit} className="btn-primary text-xs">
              {editingAgent ? 'Update' : 'Create'}
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        {agents.map(agent => (
          <div key={agent.id} className="glass border border-borderDefault/50 rounded-lg p-4 card-hover">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-md flex items-center justify-center" style={{ backgroundColor: `${agent.color}15`, border: `1px solid ${agent.color}30` }}>
                  <Cpu className="w-4 h-4" style={{ color: agent.color }} />
                </div>
                <div>
                  <h3 className="text-sm font-medium text-fgDefault">{agent.name}</h3>
                  <p className="text-[10px] text-fgSubtle font-mono">{agent.model}</p>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <button onClick={() => handleEdit(agent)} className="p-1.5 rounded hover:bg-canvas/50 text-fgSubtle hover:text-fgDefault transition-colors">
                  <Edit3 className="w-3.5 h-3.5" />
                </button>
                <button onClick={() => handleDelete(agent.id)} className="p-1.5 rounded hover:bg-danger/10 text-fgSubtle hover:text-danger transition-colors">
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            <button
              onClick={() => setTestingAgent(testingAgent?.id === agent.id ? null : agent)}
              className="btn-secondary text-xs w-full"
            >
              {testingAgent?.id === agent.id ? 'Hide Test Panel' : 'Test Agent'}
            </button>

            {testingAgent?.id === agent.id && (
              <div className="mt-3 space-y-2 border-t border-borderDefault/50 pt-3">
                <div className="flex gap-2">
                  <input
                    ref={inputRef}
                    value={testInput}
                    onChange={(e) => setTestInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && testAgent()}
                    placeholder="Test message..."
                    className="input-field flex-1 text-xs"
                    disabled={testStreaming}
                  />
                  <button onClick={testAgent} disabled={testStreaming || !testInput.trim()} className="btn-primary text-xs px-3">
                    {testStreaming ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                  </button>
                </div>
                {testOutput && (
                  <div className="glass border border-borderDefault/50 rounded-md p-3 text-xs text-fgDefault font-mono whitespace-pre-wrap max-h-40 overflow-y-auto relative">
                    {testOutput}
                    <button
                      onClick={() => copyText(testOutput, 'test')}
                      className="absolute top-1.5 right-1.5 text-fgSubtle hover:text-fgDefault"
                    >
                      {copiedId === 'test' ? <Check className="w-3 h-3 text-success" /> : <Copy className="w-3 h-3" />}
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}

        {agents.length === 0 && !showForm && (
          <div className="col-span-full text-center py-16 text-fgSubtle">
            <Cpu className="w-10 h-10 mx-auto mb-3 opacity-20" />
            <p className="text-sm">No custom agents yet</p>
            <p className="text-xs mt-1">Create your first custom agent to get started</p>
          </div>
        )}
      </div>
    </div>
  );
}
