import React from 'react';
import { motion } from 'framer-motion';
import { Network, Terminal, ShieldAlert, Cpu, Database, Wrench, ArrowRight, Zap } from 'lucide-react';

export default function LandingPage({ onEnter }) {
  const agents = [
    { name: "Manager", icon: <Cpu className="w-5 h-5" />, desc: "Central orchestrator. Plans, routes tasks, and synthesizes output.", model: "qwen2.5:14b", color: "accent" },
    { name: "Coder", icon: <Terminal className="w-5 h-5" />, desc: "Autonomous developer. Writes, debugs, and refactors code.", model: "deepseek-coder-v2:16b", color: "done" },
    { name: "Analyst", icon: <Database className="w-5 h-5" />, desc: "Data processing specialist. Summarizes and extracts insights.", model: "qwen2.5:14b", color: "success" },
    { name: "Critic", icon: <ShieldAlert className="w-5 h-5" />, desc: "Quality assurance. Evaluates code for security and performance.", model: "devstral:24b", color: "attention" },
    { name: "Tool Agent", icon: <Wrench className="w-5 h-5" />, desc: "Filesystem interaction. Reads, writes, and manages project files.", model: "Internal", color: "sponsors" },
    { name: "Executor", icon: <Zap className="w-5 h-5" />, desc: "Sandbox execution engine. Runs generated code securely.", model: "Internal", color: "accent" },
  ];

  const colorMap = {
    accent: { text: 'text-accent', bg: 'bg-accent/10', border: 'border-accent/20' },
    done: { text: 'text-done', bg: 'bg-done/10', border: 'border-done/20' },
    success: { text: 'text-success', bg: 'bg-success/10', border: 'border-success/20' },
    attention: { text: 'text-attention', bg: 'bg-attention/10', border: 'border-attention/20' },
    sponsors: { text: 'text-sponsors', bg: 'bg-sponsors/10', border: 'border-sponsors/20' },
  };

  const particles = Array.from({ length: 20 }, (_, i) => ({
    id: i,
    left: Math.random() * 100,
    delay: Math.random() * 10,
    duration: 10 + Math.random() * 20,
    size: 1 + Math.random() * 2,
    opacity: 0.1 + Math.random() * 0.3,
  }));

  const floatingIcons = [
    { icon: <Cpu className="w-6 h-6" />, color: '#58a6ff', x: '10%', y: '20%', delay: 0 },
    { icon: <Terminal className="w-6 h-6" />, color: '#a371f7', x: '85%', y: '15%', delay: 1 },
    { icon: <Database className="w-6 h-6" />, color: '#3fb950', x: '75%', y: '70%', delay: 2 },
    { icon: <ShieldAlert className="w-6 h-6" />, color: '#d29922', x: '15%', y: '75%', delay: 3 },
    { icon: <Zap className="w-6 h-6" />, color: '#db61a2', x: '50%', y: '10%', delay: 4 },
  ];

  return (
    <div className="relative w-full min-h-screen bg-canvas overflow-y-auto flex flex-col items-center font-sans">
      <div className="absolute inset-0 gradient-bg-animated pointer-events-none" />
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        {particles.map(p => (
          <div
            key={p.id}
            className="absolute rounded-full bg-accent"
            style={{
              left: `${p.left}%`,
              bottom: '-10px',
              width: `${p.size}px`,
              height: `${p.size}px`,
              opacity: p.opacity,
              animation: `particle-float ${p.duration}s linear ${p.delay}s infinite`,
            }}
          />
        ))}
      </div>

      {floatingIcons.map((fi, i) => (
        <motion.div
          key={i}
          className="absolute pointer-events-none opacity-[0.06]"
          style={{ left: fi.x, top: fi.y, color: fi.color }}
          animate={{ y: [0, -15, 0], rotate: [0, 5, -5, 0] }}
          transition={{ duration: 6 + i, repeat: Infinity, ease: 'easeInOut', delay: fi.delay }}
        >
          {fi.icon}
        </motion.div>
      ))}

      <div className="relative z-10 container mx-auto px-6 lg:px-12 flex flex-col items-center text-center py-24">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="max-w-4xl"
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-canvasSubtle/80 backdrop-blur-sm border border-borderDefault text-fgMuted text-xs font-medium mb-6 animate-border-glow"
          >
            <Network className="w-3.5 h-3.5" />
            v3.1 Local Orchestrator
          </motion.div>

          <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6">
            <span className="text-gradient">AI Agent IDE</span>
          </h1>

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="text-lg text-fgMuted mb-10 max-w-2xl mx-auto leading-relaxed"
          >
            A completely local, privacy-first multi-agent orchestration platform.
            Deploy specialized models to write code, analyze data, and execute tasks autonomously.
            No cloud. No API keys. Complete control.
          </motion.p>

          <motion.button
            whileHover={{ scale: 1.02, boxShadow: '0 0 25px rgba(88, 166, 255, 0.3)' }}
            whileTap={{ scale: 0.98 }}
            onClick={onEnter}
            className="group inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-accent to-accent/80 hover:from-accent/90 hover:to-accent/70 text-white rounded-md font-medium text-base transition-all cursor-pointer shadow-[0_0_15px_rgba(88,166,255,0.2)]"
          >
            Enter Dashboard
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </motion.button>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 0.3, ease: "easeOut" }}
          className="w-full max-w-6xl mt-24 mb-12"
        >
          <div className="text-left mb-6 ml-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-fgSubtle">Agent Fleet</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {agents.map((agent, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 * index }}
                whileHover={{ y: -4, transition: { duration: 0.2 } }}
                className="p-5 rounded-lg glass border border-borderDefault hover:border-borderMuted transition-all duration-300 card-hover relative overflow-hidden group"
              >
                <div className="absolute inset-0 bg-gradient-to-br from-transparent to-transparent group-hover:from-accent/[0.03] group-hover:to-transparent transition-all duration-500" />
                <div className="relative z-10">
                  <div className="flex items-center justify-between mb-3">
                    <motion.div
                      className={`w-9 h-9 rounded-md ${colorMap[agent.color].bg} ${colorMap[agent.color].border} border flex items-center justify-center ${colorMap[agent.color].text}`}
                      whileHover={{ scale: 1.1 }}
                      animate={{ y: [0, -2, 0] }}
                      transition={{ duration: 2, repeat: Infinity, delay: index * 0.3 }}
                    >
                      {agent.icon}
                    </motion.div>
                    <span className="text-xs font-mono text-fgSubtle bg-canvas px-2 py-0.5 rounded border border-borderMuted">
                      {agent.model}
                    </span>
                  </div>
                  <h3 className="text-base font-semibold text-fgDefault mb-1">{agent.name}</h3>
                  <p className="text-sm text-fgMuted leading-relaxed">{agent.desc}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8 }}
          className="w-full max-w-3xl mb-16"
        >
          <div className="flex items-center justify-center gap-10 p-4 rounded-lg glass border border-borderDefault">
            {[
              { label: 'Agents', value: '6' },
              { label: 'Models', value: 'Local' },
              { label: 'Privacy', value: '100%' },
              { label: 'Latency', value: '<2s' },
            ].map((stat, i) => (
              <motion.div
                key={i}
                className="text-center"
                whileHover={{ scale: 1.05 }}
              >
                <div className="text-lg font-semibold text-gradient-accent">{stat.value}</div>
                <div className="text-xs text-fgSubtle uppercase tracking-wider">{stat.label}</div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  );
}
