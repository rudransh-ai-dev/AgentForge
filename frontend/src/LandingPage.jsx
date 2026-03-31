import React from 'react';
import { motion } from 'framer-motion';
import { Network, Terminal, ShieldAlert, Cpu, Database, Wrench, ArrowRight } from 'lucide-react';

export default function LandingPage({ onEnter }) {
  const agents = [
    { name: "Manager AI", icon: <Cpu className="w-5 h-5 text-cyan-400" />, desc: "Central Orchestrator. Plans, routes tasks, and synthesizes output.", model: "llama3:8b" },
    { name: "Coder Agent", icon: <Terminal className="w-5 h-5 text-purple-400" />, desc: "Autonomous developer. Writes, debugs, and refactors complex code.", model: "deepseek-coder:6.7b" },
    { name: "Analyst", icon: <ChartBar className="w-5 h-5 text-green-400" />, desc: "Data processing specialist. Summarizes and extracts insights.", model: "phi3:mini" },
    { name: "Critic", icon: <ShieldAlert className="w-5 h-5 text-amber-400" />, desc: "Quality assurance. Evaluates code and logic for security and performance.", model: "llama3:latest" },
    { name: "Tool Agent", icon: <Wrench className="w-5 h-5 text-pink-400" />, desc: "Filesystem interaction layer. Reads, writes, and searches local project files.", model: "Internal · FS" },
    { name: "Executor", icon: <Database className="w-5 h-5 text-blue-400" />, desc: "Python sandbox execution engine. Securely runs generated code in subprocess.", model: "Internal · Sandbox" },
  ];

  return (
    <div className="relative w-full min-h-screen bg-black overflow-y-auto flex flex-col items-center font-sans text-white">
      {/* Background Video (Reusing the cinematic effect) */}
      <video
         autoPlay
         loop
         muted
         playsInline
         className="absolute inset-0 w-full h-full object-cover opacity-30 select-none pointer-events-none filter blur-[2px]"
      >
        <source src="https://d25rnvqbxsf9to.cloudfront.net/output_4.mp4" type="video/mp4" />
      </video>
      
      {/* Ambient Glows */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-[120px] pointer-events-none" />

      {/* Grid Overlay */}
      <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0wIDBoNDB2NDBIMHoiIGZpbGw9Im5vbmUiIC8+CjxwYXRoIGQ9Ik0zOSAzOUgwVjBoMzl2Mzl6IiBzdHJva2U9InJnYmEoMjU1LDI1NSwyNTUsMC4wMSkiIGZpbGw9Im5vbmUiIC8+Cjwvc3ZnPg==')] opacity-50 z-0 select-none pointer-events-none" />

      {/* Main Content */}
      <div className="relative z-10 container mx-auto px-6 lg:px-12 flex flex-col items-center text-center py-24">
         
         {/* Hero Title */}
         <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className="max-w-4xl"
         >
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-cyan-400 text-xs uppercase tracking-widest font-bold mb-6">
               <Network className="w-3.5 h-3.5" />
               v2.0 Local Orchestrator Active
            </div>
            
            <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6 bg-gradient-to-br from-white via-gray-300 to-gray-600 bg-clip-text text-transparent">
               Unlock the Power of AI <br /> 
               <span className="bg-gradient-to-r from-cyan-400 to-purple-500 bg-clip-text text-transparent">For Your Workspace</span>
            </h1>
            
            <p className="text-lg text-gray-400 mb-10 max-w-2xl mx-auto leading-relaxed">
               A completely local, privacy-first multi-agent operating system. 
               Deploy specialized models to write code, analyze data, and execute tasks autonomously.
            </p>
            
            <motion.button 
               whileHover={{ scale: 1.05, boxShadow: "0 0 30px rgba(0,240,255,0.4)" }}
               whileTap={{ scale: 0.95 }}
               onClick={onEnter}
               className="group flex items-center gap-3 px-8 py-4 bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-400/30 text-cyan-300 rounded-full font-bold text-lg transition-all mx-auto shadow-[0_0_15px_rgba(0,240,255,0.15)]"
            >
               Enter Dashboard
               <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
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
                <span className="text-xs font-bold uppercase tracking-[0.2em] text-gray-500">Autonomous Fleet (Local Models)</span>
                <span className="text-[10px] text-gray-600 font-mono">Status: Connected</span>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
               {agents.map((agent, index) => (
                  <motion.div 
                     key={index}
                     whileHover={{ y: -5, borderColor: "rgba(255,255,255,0.2)", backgroundColor: "rgba(255,255,255,0.03)" }}
                     className="glass-panel text-left p-6 rounded-2xl bg-[#08080c]/80 border border-white/[0.05] shadow-[0_8px_30px_rgb(0,0,0,0.5)] transition-all cursor-default"
                  >
                     <div className="flex items-center justify-between mb-4">
                        <div className="w-10 h-10 rounded-lg bg-black/50 border border-white/5 flex items-center justify-center">
                           {agent.icon}
                        </div>
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
