import React, { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight, FileCode, Plus, Minus, RefreshCw, ArrowLeft } from 'lucide-react';

const API = "http://127.0.0.1:8888";

export default function CodeDiffViewer({ projectId, onClose }) {
  const [diffs, setDiffs] = useState([]);
  const [selectedDiff, setSelectedDiff] = useState(null);
  const [diffDetail, setDiffDetail] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDiffs();
  }, [projectId]);

  useEffect(() => {
    if (selectedDiff) {
      fetchDiffDetail(selectedDiff);
    }
  }, [selectedDiff]);

  const fetchDiffs = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/workspace/${projectId}/diffs`);
      const data = await res.json();
      setDiffs(data.diffs || []);
      if (data.diffs?.length > 0 && !selectedDiff) {
        setSelectedDiff(data.diffs[0].diff_id);
      }
    } catch (e) {
      console.error("Failed to fetch diffs", e);
    } finally {
      setLoading(false);
    }
  };

  const fetchDiffDetail = async (diffId) => {
    try {
      const res = await fetch(`${API}/workspace/${projectId}/diffs/${diffId}`);
      const data = await res.json();
      setDiffDetail(data);
    } catch (e) {
      console.error("Failed to fetch diff detail", e);
    }
  };

  const currentDiff = diffs.find(d => d.diff_id === selectedDiff);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <RefreshCw className="w-5 h-5 text-fgSubtle animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex-1 h-full flex flex-col bg-canvas">
      <div className="h-10 border-b border-borderDefault flex items-center justify-between px-4 bg-canvasSubtle">
        <div className="flex items-center gap-2">
          {onClose && (
            <button onClick={onClose} className="text-fgSubtle hover:text-fgDefault">
              <ArrowLeft className="w-4 h-4" />
            </button>
          )}
          <FileCode className="w-3.5 h-3.5 text-fgMuted" />
          <span className="text-xs font-medium text-fgDefault">Diffs</span>
          <span className="text-[10px] text-fgSubtle">({diffs.length})</span>
        </div>
        <button onClick={fetchDiffs} className="text-fgSubtle hover:text-fgDefault">
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="w-56 border-r border-borderDefault bg-canvasSubtle overflow-y-auto">
          {diffs.length === 0 ? (
            <div className="p-3 text-xs text-fgSubtle text-center py-8">No diffs recorded</div>
          ) : (
            diffs.map(diff => (
              <button
                key={diff.diff_id}
                onClick={() => setSelectedDiff(diff.diff_id)}
                className={`w-full text-left px-3 py-2 text-xs border-b border-borderDefault/50 transition-colors ${
                  selectedDiff === diff.diff_id
                    ? 'bg-accent/10 text-accent'
                    : 'text-fgMuted hover:bg-canvas hover:text-fgDefault'
                }`}
              >
                <div className="font-mono truncate">{diff.filename}</div>
                <div className="flex items-center gap-2 mt-0.5 text-[10px] text-fgSubtle">
                  <span className="flex items-center gap-0.5 text-success">
                    <Plus className="w-2.5 h-2.5" />{diff.additions}
                  </span>
                  <span className="flex items-center gap-0.5 text-danger">
                    <Minus className="w-2.5 h-2.5" />{diff.deletions}
                  </span>
                  <span>#{diff.attempt}</span>
                </div>
              </button>
            ))
          )}
        </div>

        <div className="flex-1 overflow-auto">
          {diffDetail?.line_diff ? (
            <div className="font-mono text-xs">
              <div className="px-4 py-2 border-b border-borderDefault bg-canvasSubtle text-xs text-fgSubtle">
                {diffDetail.filename} — Attempt #{diffDetail.attempt}
              </div>
              {diffDetail.line_diff.map((line, i) => (
                <div
                  key={i}
                  className={`flex px-4 py-0.5 ${
                    line.type === 'added' ? 'bg-success/5 text-success' :
                    line.type === 'removed' ? 'bg-danger/5 text-danger' :
                    'text-fgDefault'
                  }`}
                >
                  <span className="w-10 text-right pr-3 text-fgSubble select-none text-[10px] text-fgSubtle">
                    {line.line_num}
                  </span>
                  <span className="w-4 select-none text-center">
                    {line.type === 'added' ? '+' : line.type === 'removed' ? '-' : ' '}
                  </span>
                  <span className="flex-1 whitespace-pre">{line.content || ' '}</span>
                </div>
              ))}
            </div>
          ) : diffDetail?.unified_diff ? (
            <pre className="p-4 font-mono text-xs text-fgDefault whitespace-pre-wrap">
              {diffDetail.unified_diff}
            </pre>
          ) : (
            <div className="flex-1 flex items-center justify-center text-fgSubtle text-sm">
              Select a diff to view changes
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
