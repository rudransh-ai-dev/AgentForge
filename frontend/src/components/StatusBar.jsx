import React from 'react';
import { Wifi, WifiOff, Loader2, Activity } from 'lucide-react';

export default function StatusBar({ health, wsStatus, sysStats, isSystemActive }) {
  const ollamaStatus = health.ollama === 'connected'
    ? { icon: <Wifi className="w-3 h-3" />, color: 'text-success', label: 'Ollama' }
    : health.ollama === 'disconnected'
      ? { icon: <WifiOff className="w-3 h-3" />, color: 'text-danger', label: 'Offline' }
      : { icon: <Loader2 className="w-3 h-3 animate-spin" />, color: 'text-attention', label: 'Checking' };

  const wsLabel = wsStatus === 'connected' ? 'WS' : wsStatus === 'connecting' ? 'WS...' : 'WS!';
  const wsColor = wsStatus === 'connected' ? 'text-success' : wsStatus === 'connecting' ? 'text-attention' : 'text-danger';

  return (
    <div className="h-6 glass-strong border-t border-borderDefault/50 flex items-center justify-between px-3 text-xs shrink-0">
      <div className="flex items-center gap-3">
        <div className={`flex items-center gap-1 ${ollamaStatus.color}`}>
          {ollamaStatus.icon}
          <span>{ollamaStatus.label}</span>
          {health.models?.length > 0 && (
            <span className="text-fgSubtle">{health.models.length} models</span>
          )}
        </div>
        <div className={`flex items-center gap-1 ${wsColor}`}>
          <div className={`w-1.5 h-1.5 rounded-full ${wsStatus === 'connected' ? 'bg-success shadow-[0_0_4px_rgba(63,185,80,0.5)]' : wsStatus === 'connecting' ? 'bg-attention' : 'bg-danger'} animate-pulse-dot`} />
          <span>{wsLabel}</span>
        </div>
      </div>

      <div className="flex items-center gap-3 text-fgSubtle">
        <span>{sysStats.total_runs} runs</span>
        <span>{sysStats.success_rate}% success</span>
        <div className="flex items-center gap-1">
          <Activity className="w-3 h-3" />
          <span className={isSystemActive ? 'text-accent' : 'text-success'}>
            {isSystemActive ? 'Running' : 'Idle'}
          </span>
        </div>
      </div>
    </div>
  );
}
