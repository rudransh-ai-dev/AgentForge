import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAgentStore } from '../store/useAgentStore';
import {
  FolderOpen, File, RefreshCw, X, Play, Trash2, Save,
  Edit3, ChevronRight, ChevronDown, Package, Zap, AlertCircle, CheckCircle
} from 'lucide-react';

const API = "http://127.0.0.1:8888";

export default function WorkspaceExplorer() {
  const {
    projects, setProjects,
    selectedProject, setSelectedProject,
    selectedFile, setSelectedFile,
    fileContent, setFileContent,
    isEditing, setIsEditing,
    editContent, setEditContent
  } = useAgentStore();

  const [expandedProjects, setExpandedProjects] = useState({});
  const [runOutput, setRunOutput] = useState(null);
  const [isRunning, setIsRunning] = useState(false);

  const fetchProjects = async () => {
    try {
      const res = await fetch(`${API}/workspace`);
      const data = await res.json();
      setProjects(data.projects || []);
    } catch (e) {
      console.error("Failed to fetch workspace", e);
    }
  };

  const fetchFile = async (projectId, filename) => {
    try {
      const res = await fetch(`${API}/workspace/${projectId}/${filename}`);
      const data = await res.json();
      setSelectedProject(projectId);
      setSelectedFile(filename);
      setFileContent(data.content || '');
      setEditContent(data.content || '');
      setIsEditing(false);
    } catch (e) {
      console.error("Failed to fetch file", e);
    }
  };

  const saveFile = async () => {
    try {
      await fetch(`${API}/workspace/${selectedProject}/${selectedFile}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: editContent })
      });
      setFileContent(editContent);
      setIsEditing(false);
    } catch (e) {
      console.error("Failed to save file", e);
    }
  };

  const deleteProject = async (projectId) => {
    if (!confirm(`Delete entire project "${projectId}"?`)) return;
    try {
      await fetch(`${API}/workspace/${projectId}`, { method: "DELETE" });
      fetchProjects();
      if (selectedProject === projectId) {
        setSelectedFile(null);
        setSelectedProject(null);
      }
    } catch (e) {
      console.error("Failed to delete project", e);
    }
  };

  const deleteFile = async (projectId, filename) => {
    if (!confirm(`Delete "${filename}"?`)) return;
    try {
      await fetch(`${API}/workspace/${projectId}/${filename}`, { method: "DELETE" });
      fetchProjects();
      if (selectedFile === filename) setSelectedFile(null);
    } catch (e) {
      console.error("Failed to delete file", e);
    }
  };

  const runProject = async (projectId, autofix = false) => {
    setIsRunning(true);
    setRunOutput({ status: 'running', output: 'Starting execution...' });
    try {
      const endpoint = autofix ? `${API}/execute/${projectId}/autofix` : `${API}/execute/${projectId}`;
      const res = await fetch(endpoint, { method: "POST" });
      const data = await res.json();
      setRunOutput(data);
    } catch (e) {
      setRunOutput({ status: 'error', output: `Connection error: ${e.message}` });
    } finally {
      setIsRunning(false);
    }
  };

  const toggleProject = (pid) => {
    setExpandedProjects(prev => ({ ...prev, [pid]: !prev[pid] }));
  };

  useEffect(() => {
    fetchProjects();
    const interval = setInterval(fetchProjects, 6000);
    return () => clearInterval(interval);
  }, []);

  const getFileIcon = (filename) => {
    if (filename.endsWith('.json')) return '📋';
    if (filename.endsWith('.py')) return '🐍';
    if (filename.endsWith('.js') || filename.endsWith('.jsx')) return '⚡';
    if (filename.endsWith('.html')) return '🌐';
    if (filename.endsWith('.css')) return '🎨';
    if (filename.endsWith('.txt') || filename.endsWith('.md')) return '📝';
    return '📄';
  };

  return (
    <div className="flex-1 h-full flex font-mono">
      {/* FILE TREE PANEL */}
      <div className="w-72 h-full flex flex-col glass-panel border-r border-white/5 bg-black/40 overflow-hidden relative">
        {/* Top accent */}
        <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-purple-400/50 to-transparent" />
        
        <div className="p-4 border-b border-white/10 flex items-center justify-between text-xs tracking-widest text-gray-500 uppercase font-bold bg-white/[0.02]">
          <div className="flex items-center gap-2">
            <FolderOpen className="w-4 h-4 text-cyan-400" /> Workspace
          </div>
          <motion.button 
            whileHover={{ rotate: 180 }}
            transition={{ duration: 0.3 }}
            onClick={fetchProjects} 
            className="hover:text-cyan-400 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </motion.button>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1 custom-scrollbar">
          {projects.length === 0 ? (
            <div className="text-[10px] text-gray-600 text-center py-10 italic">
              Workspace empty.<br/>Ask the Coder to generate a project.
            </div>
          ) : (
            projects.map((proj, idx) => (
              <motion.div 
                key={proj.project_id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.05 }}
              >
                {/* Project Header */}
                <div
                  onClick={() => toggleProject(proj.project_id)}
                  className="flex items-center gap-2 px-3 py-2 rounded-md cursor-pointer hover:bg-white/5 text-[11px] text-gray-300 group"
                >
                  {expandedProjects[proj.project_id] ?
                    <ChevronDown className="w-3 h-3 text-gray-500" /> :
                    <ChevronRight className="w-3 h-3 text-gray-500" />
                  }
                  <Package className="w-3.5 h-3.5 text-purple-400" />
                  <span className="font-bold truncate flex-1">{proj.project_id}</span>

                  <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => { e.stopPropagation(); runProject(proj.project_id); }}
                      className="p-1 rounded hover:bg-green-500/20 text-green-400"
                      title="Run Project"
                    >
                      <Play className="w-3 h-3" />
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); runProject(proj.project_id, true); }}
                      className="p-1 rounded hover:bg-amber-500/20 text-amber-400"
                      title="Run + Auto-Fix"
                    >
                      <Zap className="w-3 h-3" />
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); deleteProject(proj.project_id); }}
                      className="p-1 rounded hover:bg-red-500/20 text-red-400"
                      title="Delete Project"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                </div>

                {/* File List */}
                {expandedProjects[proj.project_id] && (
                  <div className="ml-4 pl-3 border-l border-white/5 space-y-0.5">
                    {proj.files.map(file => (
                      <div
                        key={file}
                        className={`flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer text-[10px] group/file transition-all ${
                          selectedFile === file && selectedProject === proj.project_id
                            ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
                            : 'text-gray-400 hover:bg-white/5 hover:text-gray-200'
                        }`}
                      >
                        <span
                          onClick={() => fetchFile(proj.project_id, file)}
                          className="flex items-center gap-2 flex-1 truncate"
                        >
                          <span>{getFileIcon(file)}</span>
                          <span className="truncate">{file}</span>
                        </span>
                        <button
                          onClick={() => deleteFile(proj.project_id, file)}
                          className="opacity-0 group-hover/file:opacity-100 text-red-400 hover:text-red-300 transition-opacity"
                        >
                          <Trash2 className="w-2.5 h-2.5" />
                        </button>
                      </div>
                    ))}

                    {/* Project Meta */}
                    {proj.meta?.entry_point && (
                      <div className="text-[9px] text-gray-600 px-2 py-1 mt-1 border-t border-white/5">
                        Entry: <span className="text-gray-400">{proj.meta.entry_point}</span>
                        {proj.meta.dependencies?.length > 0 && (
                          <div className="mt-0.5">Deps: <span className="text-purple-400">{proj.meta.dependencies.join(', ')}</span></div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </motion.div>
            ))
          )}
        </div>
      </div>

      {/* FILE CONTENT / EDITOR PANEL */}
      <div className="flex-1 flex flex-col bg-[#070709] border-l border-white/5">
        {selectedFile ? (
          <>
            {/* File Header Bar */}
            <div className="h-12 border-b border-white/10 flex items-center justify-between px-4 bg-black/50">
              <div className="flex items-center gap-3">
                <span className="text-[11px]">{getFileIcon(selectedFile)}</span>
                <span className="text-[12px] text-cyan-100 font-bold tracking-wider">{selectedFile}</span>
                <span className="text-[9px] text-gray-600">({selectedProject})</span>
              </div>
              <div className="flex items-center gap-2">
                {isEditing ? (
                  <>
                    <button
                      onClick={saveFile}
                      className="flex items-center gap-1.5 px-2.5 py-1 bg-green-500/10 hover:bg-green-500/20 text-green-400 border border-green-500/20 rounded text-[10px] font-bold"
                    >
                      <Save className="w-3 h-3" /> Save
                    </button>
                    <button
                      onClick={() => { setIsEditing(false); setEditContent(fileContent); }}
                      className="text-gray-500 hover:text-white text-[10px] px-2 py-1"
                    >Cancel</button>
                  </>
                ) : (
                  <button
                    onClick={() => setIsEditing(true)}
                    className="flex items-center gap-1.5 px-2.5 py-1 bg-white/5 hover:bg-white/10 text-gray-300 border border-white/10 rounded text-[10px]"
                  >
                    <Edit3 className="w-3 h-3" /> Edit
                  </button>
                )}
                <button onClick={() => setSelectedFile(null)} className="text-gray-500 hover:text-white ml-2">
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* File Content */}
            <div className="flex-1 overflow-auto custom-scrollbar p-0">
              {isEditing ? (
                <textarea
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  className="w-full h-full bg-transparent text-[12px] text-cyan-50/90 font-mono leading-relaxed p-6 resize-none focus:outline-none"
                  spellCheck={false}
                />
              ) : (
                <pre className="text-[12px] text-cyan-50/80 font-mono leading-relaxed p-6 select-text whitespace-pre-wrap">
                  {fileContent}
                </pre>
              )}
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-600">
            <div className="text-center space-y-4">
              <File className="w-12 h-12 mx-auto opacity-20" />
              <p className="text-sm">Select a file to view or edit</p>
              <p className="text-[10px] text-gray-700">Or run a prompt to generate a project</p>
            </div>
          </div>
        )}

        {/* Execution Output Panel */}
        {runOutput && (
          <div className={`h-48 border-t flex flex-col overflow-hidden ${
            runOutput.status === 'success' ? 'border-green-500/30' :
            runOutput.status === 'error' ? 'border-red-500/30' :
            'border-cyan-500/30'
          }`}>
            <div className="h-8 flex items-center justify-between px-4 bg-black/60 border-b border-white/5">
              <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest">
                {runOutput.status === 'success' ? (
                  <><CheckCircle className="w-3.5 h-3.5 text-green-400" /><span className="text-green-400">Execution Success</span></>
                ) : runOutput.status === 'running' ? (
                  <><Play className="w-3.5 h-3.5 text-cyan-400 animate-pulse" /><span className="text-cyan-400">Running...</span></>
                ) : (
                  <><AlertCircle className="w-3.5 h-3.5 text-red-400" /><span className="text-red-400">Execution Failed</span></>
                )}
              </div>
              <button onClick={() => setRunOutput(null)} className="text-gray-500 hover:text-white">
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="flex-1 p-3 overflow-auto custom-scrollbar">
              <pre className={`text-[11px] font-mono whitespace-pre-wrap ${
                runOutput.status === 'success' ? 'text-green-300/80' : 'text-red-300/80'
              }`}>
                {runOutput.output || runOutput.errors || JSON.stringify(runOutput, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
