import React from 'react';
import { motion } from 'framer-motion';
import { Network, Terminal, ShieldAlert, Cpu, Database, Wrench, ArrowRight, Sparkles, Zap } from 'lucide-react';

export default function LandingPage({ onEnter }) {
  const agents = [
    { name: "Manager AI", icon: <Cpu className="w-5 h-5 text-cyan-400" />, desc: "Central Orchestrator. Plans, routes tasks, and synthesizes output.", model: "llama3:8b", color: "cyan" },
    { name: "Coder Agent", icon: <Terminal className="w-5 h-5 text-purple-400" />, desc: "Autonomous developer. Writes, debugs, and refactors complex code.", model: "deepseek-coder:6.7b", color: "purple" },
    { name: "Analyst", icon: <ChartBar className="w-5 h-5 text-green-400" />, desc: "Data processing specialist. Summarizes and extracts insights.", model: "phi3:mini", color: "green" },
    { name: "Critic", icon: <ShieldAlert className="w-5 h-5 text-amber-400" />, desc: "Quality assurance. Evaluates code and logic for security and performance.", model: "llama3:latest", color: "amber" },
    { name: "Tool Agent", icon: <Wrench className="w-5 h-5 text-pink-400" />, desc: "Filesystem interaction layer. Reads, writes, and searches local project files.", model: "Internal · FS", color: "pink" },
    { name: "Executor", icon: <Database className="w-5 h-5 text-blue-400" />, desc: "Python sandbox execution engine. Securely runs generated code in subprocess.", model: "Internal · Sandbox", color: "blue" },
  ];

  const colorMap = {
    cyan: { border: 'hover:border-cyan-400/40', glow: 'hover:shadow-[0_0_30px_rgba(0,240,255,0.2)]', bg: 'hover:bg-cyan-500/5' },
    purple: { border: 'hover:border-purple-400/40', glow: 'hover:shadow-[0_0_30px_rgba(168,85,247,0.2)]', bg: 'hover:bg-purple-500/5' },
    green: { border: 'hover:border-green-400/40', glow: 'hover:shadow-[0_0_30px_rgba(34,197,94,0.2)]', bg: 'hover:bg-green-500/5' },
    amber: { border: 'hover:border-amber-400/40', glow: 'hover:shadow-[0_0_30px_rgba(245,158,11,0.2)]', bg: 'hover:bg-amber-500/5' },
    pink: { border: 'hover:border-pink-400/40', glow: 'hover:shadow-[0_0_30px_rgba(236,72,153,0.2)]', bg: 'hover:bg-pink-500/5' },
    blue: { border: 'hover:border-blue-400/40', glow: 'hover:shadow-[0_0_30px_rgba(59,130,246,0.2)]', bg: 'hover:bg-blue-500/5' },
  };

  return (
    <div className="relative w-full min-h-screen bg-black overflow-y-auto flex flex-col items-center font-sans text-white">
      {/* Animated Gradient Background (replaces broken video) */}
      <div className="absolute inset-0 bg-gradient-to-br from-black via-[#0a0a1a] to-black">
        <motion.div
          animate={{ opacity: [0.3, 0.5, 0.3], scale: [1, 1.1, 1] }}
          transition={{ duration: 8, repeat: Infinity }}
          className="absolute top-1/3 left-1/3 w-[500px] h-[500px] bg-cyan-500/10 rounded-full blur-[150px]"
        />
        <motion.div
          animate={{ opacity: [0.2, 0.4, 0.2], scale: [1, 1.15, 1] }}
          transition={{ duration: 10, repeat: Infinity }}
          className="absolute bottom-1/3 right-1/3 w-[500px] h-[500px] bg-purple-500/10 rounded-full blur-[150px]"
        />
        <motion.div
          animate={{ opacity: [0.1, 0.2, 0.1], scale: [1, 1.1, 1] }}
          transition={{ duration: 12, repeat: Infinity }}
          className="absolute top-1/2 left-1/2 w-[400px] h-[400px] bg-pink-500/5 rounded-full blur-[120px]"
        />
      </div>
      
      {/* Grid Overlay */}
      <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0wIDBoNDB2NDBIMHoiIGZpbGw9Im5vbmUiIC8+CjxwYXRoIGQ9Ik0zOSAzOUgwVjBoMzl2Mzl6IiBzdHJva2U9InJnYmEoMjU1LDI1NSwyNTUsMC4wMSkiIGZpbGw9Im5vbmUiIC8+Cjwvc3ZnPg==')] opacity-50 z-0 select-none pointer-events-none animate-cyber-grid" />

      {/* Floating Particles */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        {[...Array(20)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-1 h-1 rounded-full bg-cyan-400/30"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
            }}
            animate={{
              y: [0, -30, 0],
              x: [0, Math.random() * 20 - 10, 0],
              scale: [1, 1.5, 1],
              opacity: [0.2, 0.6, 0.2],
            }}
            transition={{
              duration: 3 + Math.random() * 4,
              repeat: Infinity,
              delay: Math.random() * 2,
            }}
          />
        ))}
      </div>

      {/* Main Content */}
      <div className="relative z-10 container mx-auto px-6 lg:px-12 flex flex-col items-center text-center py-24">
         
         {/* Hero Title */}
         <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className="max-w-4xl"
         >
            <motion.div 
              whileHover={{ scale: 1.05 }}
              className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-cyan-400 text-xs uppercase tracking-widest font-bold mb-6 animate-border-glow"
            >
               <Network className="w-3.5 h-3.5" />
               <Sparkles className="w-3 h-3 animate-pulse" />
               v2.0 Local Orchestrator Active
            </motion.div>
            
            <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6">
               <span className="bg-gradient-to-br from-white via-gray-300 to-gray-600 bg-clip-text text-transparent">
                  Unlock the Power of AI <br /> 
               </span>
               <span className="bg-gradient-to-r from-cyan-400 via-purple-500 to-pink-500 bg-clip-text text-transparent animate-gradient-shift bg-[length:200%_200%]">
                  For Your Workspace
               </span>
            </h1>
            
            <motion.p 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
              className="text-lg text-gray-400 mb-10 max-w-2xl mx-auto leading-relaxed"
            >
               A completely local, privacy-first multi-agent operating system. 
               Deploy specialized models to write code, analyze data, and execute tasks autonomously.
            </motion.p>
            
            <motion.button 
               whileHover={{ scale: 1.05, boxShadow: "0 0 40px rgba(0,240,255,0.5), 0 0 80px rgba(168,85,247,0.3)" }}
               whileTap={{ scale: 0.95 }}
               onClick={onEnter}
               className="group relative flex items-center gap-3 px-8 py-4 bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-400/30 text-cyan-300 rounded-full font-bold text-lg transition-all mx-auto overflow-hidden"
            >
               <motion.div 
                 className="absolute inset-0 bg-gradient-to-r from-cyan-500/20 via-purple-500/20 to-pink-500/20"
                 animate={{ x: ['-100%', '100%'] }}
                 transition={{ duration: 2, repeat: Infinity }}
               />
               <span className="relative z-10">Enter Dashboard</span>
               <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform relative z-10" />
            </motion.button>
         </motion.div>
         
         {/* Agents Showcase Carousel */}
         <motion.div 
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1, delay: 0.3, ease: "easeOut" }}
            className="w-full max-w-6xl mt-24 mb-12"
         >
            <div className="text-left mb-6 ml-2 flex items-center justify-between opacity-70">
                <span className="text-xs font-bold uppercase tracking-[0.2em] text-gray-500 flex items-center gap-2">
                  <Zap className="w-3 h-3 text-cyan-400" />
                  Autonomous Fleet (Local Models)
                </span>
                <motion.span 
                  animate={{ opacity: [0.5, 1, 0.5] }}
                  transition={{ duration: 2, repeat: Infinity }}
                  className="text-[10px] text-green-400 font-mono flex items-center gap-1"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
                  Status: Connected
                </motion.span>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
               {agents.map((agent, index) => (
                  <motion.div 
                     key={index}
                     initial={{ opacity: 0, y: 20 }}
                     animate={{ opacity: 1, y: 0 }}
                     transition={{ delay: 0.1 * index }}
                     whileHover={{ y: -8, transition: { duration: 0.2 } }}
                     className={`text-left p-6 rounded-2xl bg-[#08080c]/80 border border-white/[0.05] shadow-[0_8px_30px_rgb(0,0,0,0.5)] transition-all duration-300 cursor-default ${colorMap[agent.color].border} ${colorMap[agent.color].glow} ${colorMap[agent.color].bg}`}
                  >
                     <div className="flex items-center justify-between mb-4">
                        <motion.div 
                          whileHover={{ rotate: 360 }}
                          transition={{ duration: 0.5 }}
                          className="w-10 h-10 rounded-lg bg-black/50 border border-white/5 flex items-center justify-center"
                        >
                           {agent.icon}
                        </motion.div>
                        <span className="text-[10px] font-mono text-gray-500 bg-white/[0.03] px-2 py-1 rounded-md border border-white/[0.05]">
                           {agent.model}
                        </span>
                     </div>
                     <h3 className="text-lg font-bold text-gray-200 mb-2">{agent.name}</h3>
                     <p className="text-sm text-gray-400 leading-relaxed font-light">{agent.desc}</p>
                  </motion.div>
               ))}
            </div>
         </motion.div>
         
         {/* Futuristic Stats Bar */}
         <motion.div
           initial={{ opacity: 0, y: 20 }}
           animate={{ opacity: 1, y: 0 }}
           transition={{ delay: 0.8 }}
           className="w-full max-w-4xl mb-16"
         >
           <div className="flex items-center justify-center gap-8 p-4 rounded-2xl bg-white/[0.02] border border-white/[0.05] backdrop-blur-sm">
             {[
               { label: 'Agents', value: '6', icon: <Cpu className="w-4 h-4 text-cyan-400" /> },
               { label: 'Models', value: 'Local', icon: <Database className="w-4 h-4 text-purple-400" /> },
               { label: 'Privacy', value: '100%', icon: <ShieldAlert className="w-4 h-4 text-green-400" /> },
               { label: 'Latency', value: '<100ms', icon: <Zap className="w-4 h-4 text-amber-400" /> },
             ].map((stat, i) => (
               <div key={i} className="text-center">
                 <div className="flex items-center justify-center mb-1">{stat.icon}</div>
                 <div className="text-lg font-bold text-white">{stat.value}</div>
                 <div className="text-[10px] text-gray-500 uppercase tracking-wider">{stat.label}</div>
               </div>
             ))}
           </div>
         </motion.div>
         
      </div>
    </div>
  );
}

// Ensure ChartBar is available
function ChartBar(props) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M3 3v18h18" />
      <path d="M18 17V9" />
      <path d="M13 17V5" />
      <path d="M8 17v-3" />
    </svg>
  );
}
