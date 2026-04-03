/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        darkBg: '#09090b',
        panelBg: 'rgba(24, 24, 27, 0.65)',
        cyanGlow: '#00f0ff',
        purpleGlow: '#a855f7',
        neonCyan: '#00f0ff',
        neonPurple: '#a855f7',
        neonPink: '#ec4899',
        neonGreen: '#22c55e',
        neonAmber: '#f59e0b',
        deepSpace: '#050505',
        voidBlack: '#030305',
        cyberDark: '#0a0a0f',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 8s linear infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
        'float': 'float 6s ease-in-out infinite',
        'gradient-shift': 'gradient-shift 8s ease infinite',
        'neon-pulse': 'neon-pulse 2s ease-in-out infinite',
        'border-glow': 'border-glow 4s ease-in-out infinite',
        'text-shimmer': 'text-shimmer 3s linear infinite',
        'cyber-grid': 'cyber-grid 6s ease-in-out infinite',
        'particle-float': 'particle-float 4s ease-in-out infinite',
        'matrix-rain': 'matrix-rain 3s linear infinite',
        'orbit': 'orbit 6s linear infinite',
        'pulse-ring': 'pulse-ring 1.5s cubic-bezier(0.215, 0.61, 0.355, 1) infinite',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 5px currentColor, 0 0 10px currentColor' },
          '100%': { boxShadow: '0 0 10px currentColor, 0 0 20px currentColor, 0 0 30px currentColor' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-6px)' },
        },
        'gradient-shift': {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
        'neon-pulse': {
          '0%, 100%': { opacity: '1', filter: 'brightness(1)' },
          '50%': { opacity: '0.8', filter: 'brightness(1.3)' },
        },
        'border-glow': {
          '0%, 100%': { borderColor: 'rgba(0, 240, 255, 0.1)' },
          '25%': { borderColor: 'rgba(168, 85, 247, 0.3)' },
          '50%': { borderColor: 'rgba(0, 240, 255, 0.3)' },
          '75%': { borderColor: 'rgba(236, 72, 153, 0.2)' },
        },
        'text-shimmer': {
          '0%': { backgroundPosition: '-200% center' },
          '100%': { backgroundPosition: '200% center' },
        },
        'cyber-grid': {
          '0%, 100%': { opacity: '0.03' },
          '50%': { opacity: '0.08' },
        },
        'particle-float': {
          '0%, 100%': { transform: 'translateY(0) translateX(0) scale(1)', opacity: '0.3' },
          '25%': { transform: 'translateY(-20px) translateX(10px) scale(1.2)', opacity: '0.6' },
          '50%': { transform: 'translateY(-40px) translateX(-5px) scale(0.8)', opacity: '0.4' },
          '75%': { transform: 'translateY(-20px) translateX(15px) scale(1.1)', opacity: '0.7' },
        },
        'matrix-rain': {
          '0%': { transform: 'translateY(-100%)', opacity: '0' },
          '10%': { opacity: '1' },
          '90%': { opacity: '1' },
          '100%': { transform: 'translateY(100%)', opacity: '0' },
        },
        orbit: {
          '0%': { transform: 'rotate(0deg) translateX(60px) rotate(0deg)' },
          '100%': { transform: 'rotate(360deg) translateX(60px) rotate(-360deg)' },
        },
        'pulse-ring': {
          '0%': { transform: 'scale(0.8)', opacity: '1' },
          '100%': { transform: 'scale(2)', opacity: '0' },
        },
      },
      backdropBlur: {
        xs: '2px',
      },
      boxShadow: {
        'neon-cyan': '0 0 20px rgba(0, 240, 255, 0.3), 0 0 40px rgba(0, 240, 255, 0.1)',
        'neon-purple': '0 0 20px rgba(168, 85, 247, 0.3), 0 0 40px rgba(168, 85, 247, 0.1)',
        'neon-pink': '0 0 20px rgba(236, 72, 153, 0.3), 0 0 40px rgba(236, 72, 153, 0.1)',
        'neon-green': '0 0 20px rgba(34, 197, 94, 0.3), 0 0 40px rgba(34, 197, 94, 0.1)',
        'holo': '0 0 30px rgba(0, 240, 255, 0.15), 0 0 60px rgba(168, 85, 247, 0.1), 0 0 90px rgba(236, 72, 153, 0.05)',
      },
      backgroundImage: {
        'holo-gradient': 'linear-gradient(135deg, rgba(0,240,255,0.1) 0%, rgba(168,85,247,0.1) 50%, rgba(236,72,153,0.1) 100%)',
        'cyber-gradient': 'linear-gradient(135deg, #00f0ff 0%, #a855f7 50%, #ec4899 100%)',
      },
    },
  },
  plugins: [],
}
