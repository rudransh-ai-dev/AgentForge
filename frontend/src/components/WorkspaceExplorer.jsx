import React, { useEffect, useState } from 'react';
import { useAgentStore } from '../store/useAgentStore';
import {
  FolderOpen, File, RefreshCw, X, Play, Trash2, Save,
  Edit3, ChevronRight, ChevronDown, Package, AlertCircle, CheckCircle, Download, Upload, GitCompare
} from 'lucide-react';
import CodeDiffViewer from './CodeDiffViewer';

const API = "";

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
  const [showDiffs, setShowDiffs] = useState(false);

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

  const exportProject = async (projectId) => {
    try {
      const res = await fetch(`${API}/workspace/export/${projectId}`);
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${projectId}.zip`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Failed to export project", e);
    }
  };

  const importProject = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
      await fetch(`${API}/workspace/import`, {
        method: "POST",
        body: formData,
      });
      fetchProjects();
    } catch (err) {
      console.error("Failed to import project", err);
    }
    e.target.value = '';
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

  const getLanguage = (proj) => {
    if (!proj.files) return null;
    if (proj.files.some(f => f.endsWith('.py'))) return 'Python';
    if (proj.files.some(f => f.endsWith('.js') || f.endsWith('.jsx') || f.endsWith('.ts'))) return 'Node.js';
    if (proj.files.some(f => f.endsWith('.go'))) return 'Go';
    if (proj.files.some(f => f.endsWith('.rs'))) return 'Rust';
    if (proj.files.some(f => f.endsWith('.sh'))) return 'Bash';
    return null;
  };

  const langColors = {
    'Python': 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    'Node.js': 'bg-green-500/10 text-green-400 border-green-500/20',
    'Go': 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
    'Rust': 'bg-orange-500/10 text-orange-400 border-orange-500/20',
    'Bash': 'bg-gray-500/10 text-gray-400 border-gray-500/20',
  };

  return (
    <div className="flex-1 h-full flex">
      <div className="w-64 h-full flex flex-col glass-strong border-r border-borderDefault/50 overflow-hidden">
        <div className="px-3 py-2 border-b border-borderDefault/50 flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs font-medium text-fgDefault">
            <FolderOpen className="w-3.5 h-3.5 text-fgMuted" /> Workspace
          </div>
          <div className="flex items-center gap-1">
            <label className="p-1 rounded hover:bg-canvas/50 text-fgSubtle hover:text-fgDefault transition-colors cursor-pointer" title="Import project">
              <Upload className="w-3.5 h-3.5" />
              <input type="file" accept=".zip" onChange={importProject} className="hidden" />
            </label>
            <button
              onClick={fetchProjects}
              className="p-1 rounded hover:bg-canvas/50 text-fgSubtle hover:text-fgDefault transition-colors"
              title="Refresh"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-1.5 space-y-0.5">
          {projects.length === 0 ? (
            <div className="text-xs text-fgSubtle text-center py-10">
              Workspace empty.<br/>Ask the Coder to generate a project.
            </div>
          ) : (
            projects.map((proj) => {
              const lang = getLanguage(proj);
              return (
                <div key={proj.project_id}>
                  <div
                    onClick={() => toggleProject(proj.project_id)}
                    className="flex items-center gap-1.5 px-2 py-1.5 rounded-md cursor-pointer hover:bg-canvas/50 text-xs text-fgDefault group"
                  >
                    {expandedProjects[proj.project_id] ?
                      <ChevronDown className="w-3 h-3 text-fgSubtle" /> :
                      <ChevronRight className="w-3 h-3 text-fgSubtle" />
                    }
                    <Package className="w-3.5 h-3.5 text-fgMuted" />
                    <span className="font-medium truncate flex-1">{proj.project_id}</span>
                    {lang && (
                      <span className={`text-[9px] px-1 py-0 rounded border ${langColors[lang] || ''}`}>{lang}</span>
                    )}

                    <div className="flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={(e) => { e.stopPropagation(); setShowDiffs(true); setSelectedProject(proj.project_id); }}
                        className="p-0.5 rounded hover:bg-canvas/50 text-fgSubtle hover:text-accent"
                        title="View Diffs"
                      >
                        <GitCompare className="w-3 h-3" />
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); exportProject(proj.project_id); }}
                        className="p-0.5 rounded hover:bg-canvas/50 text-fgSubtle hover:text-fgDefault"
                        title="Export as zip"
                      >
                        <Download className="w-3 h-3" />
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); runProject(proj.project_id); }}
                        className="p-0.5 rounded hover:bg-success/10 text-fgSubtle hover:text-success"
                        title="Run Project"
                      >
                        <Play className="w-3 h-3" />
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); deleteProject(proj.project_id); }}
                        className="p-0.5 rounded hover:bg-danger/10 text-fgSubtle hover:text-danger"
                        title="Delete Project"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  </div>

                  {expandedProjects[proj.project_id] && (
                    <div className="ml-4 pl-2 border-l border-borderDefault/50 space-y-0">
                      {proj.files.map(file => (
                        <div
                          key={file}
                          className={`flex items-center gap-1.5 px-2 py-1 rounded-md cursor-pointer text-xs group/file ${
                            selectedFile === file && selectedProject === proj.project_id
                              ? 'bg-accent/10 text-accent'
                              : 'text-fgMuted hover:bg-canvas/50 hover:text-fgDefault'
                          }`}
                        >
                          <span
                            onClick={() => fetchFile(proj.project_id, file)}
                            className="flex items-center gap-1.5 flex-1 truncate"
                          >
                            <File className="w-3 h-3 shrink-0" />
                            <span className="truncate">{file}</span>
                          </span>
                          <button
                            onClick={() => deleteFile(proj.project_id, file)}
                            className="opacity-0 group-hover/file:opacity-100 text-fgSubtle hover:text-danger transition-opacity"
                          >
                            <Trash2 className="w-2.5 h-2.5" />
                          </button>
                        </div>
                      ))}

                      {proj.meta?.entry_point && (
                        <div className="text-[10px] text-fgSubtle px-2 py-1.5 mt-1 border-t border-borderDefault/50">
                          Entry: <span className="text-fgMuted font-mono">{proj.meta.entry_point}</span>
                          {proj.meta.dependencies?.length > 0 && (
                            <div className="mt-0.5">Deps: <span className="text-fgMuted">{proj.meta.dependencies.join(', ')}</span></div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      <div className="flex-1 flex flex-col bg-canvas/50">
        {selectedFile ? (
          <>
            <div className="h-10 border-b border-borderDefault/50 flex items-center justify-between px-4 glass-strong">
              <div className="flex items-center gap-2">
                <span className="text-xs">{getFileIcon(selectedFile)}</span>
                <span className="text-xs font-medium text-fgDefault">{selectedFile}</span>
                <span className="text-[10px] text-fgSubtle">({selectedProject})</span>
              </div>
              <div className="flex items-center gap-1.5">
                {isEditing ? (
                  <>
                    <button onClick={saveFile} className="btn-primary text-xs px-2 py-1">
                      <Save className="w-3 h-3" /> Save
                    </button>
                    <button
                      onClick={() => { setIsEditing(false); setEditContent(fileContent); }}
                      className="btn-secondary text-xs px-2 py-1"
                    >Cancel</button>
                  </>
                ) : (
                  <button
                    onClick={() => setIsEditing(true)}
                    className="btn-secondary text-xs px-2 py-1"
                  >
                    <Edit3 className="w-3 h-3" /> Edit
                  </button>
                )}
                <button onClick={() => setSelectedFile(null)} className="text-fgSubtle hover:text-fgDefault ml-1">
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-auto p-4">
              {isEditing ? (
                <textarea
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  className="w-full h-full bg-transparent text-sm text-fgDefault font-mono leading-relaxed resize-none focus:outline-none"
                  spellCheck={false}
                />
              ) : (
                <pre className="text-sm text-fgDefault font-mono leading-relaxed whitespace-pre-wrap select-text">
                  {fileContent}
                </pre>
              )}
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-fgSubtle">
            <div className="text-center space-y-3">
              <File className="w-10 h-10 mx-auto opacity-20" />
              <p className="text-sm">Select a file to view or edit</p>
            </div>
          </div>
        )}

        {runOutput && (
          <div className={`border-t flex flex-col overflow-hidden ${
            runOutput.status === 'success' ? 'border-success/20' :
            runOutput.status === 'error' ? 'border-danger/20' :
            'border-borderDefault/50'
          }`}>
            <div className="h-8 flex items-center justify-between px-3 glass border-b border-borderDefault/50">
              <div className="flex items-center gap-1.5 text-xs font-medium">
                {runOutput.status === 'success' ? (
                  <><CheckCircle className="w-3.5 h-3.5 text-success" /><span className="text-success">Success</span></>
                ) : runOutput.status === 'running' ? (
                  <><Play className="w-3.5 h-3.5 text-accent animate-pulse" /><span className="text-accent">Running...</span></>
                ) : (
                  <><AlertCircle className="w-3.5 h-3.5 text-danger" /><span className="text-danger">Failed</span></>
                )}
              </div>
              <button onClick={() => setRunOutput(null)} className="text-fgSubtle hover:text-fgDefault">
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="h-40 p-3 overflow-auto">
              <pre className={`text-xs font-mono whitespace-pre-wrap ${
                runOutput.status === 'success' ? 'text-success' : 'text-danger'
              }`}>
                {runOutput.output || runOutput.errors || JSON.stringify(runOutput, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>

      {showDiffs && selectedProject && (
        <div className="absolute inset-0 z-50 bg-canvas">
          <CodeDiffViewer projectId={selectedProject} onClose={() => setShowDiffs(false)} />
        </div>
      )}
    </div>
  );
}
