/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: '#0d1117',
        canvasInset: '#010409',
        canvasSubtle: '#161b22',
        borderDefault: '#30363d',
        borderMuted: '#21262d',
        fgDefault: '#c9d1d9',
        fgMuted: '#8b949e',
        fgSubtle: '#484f58',
        accent: '#58a6ff',
        accentFg: '#ffffff',
        success: '#3fb950',
        successFg: '#ffffff',
        danger: '#f85149',
        dangerFg: '#ffffff',
        attention: '#d29922',
        done: '#a371f7',
        sponsors: '#db61a2',
      },
      animation: {
        'fade-in': 'fade-in 0.2s ease-out',
        'slide-in-left': 'slide-in-left 0.2s ease-out',
        'pulse-dot': 'pulse-dot 2s ease-in-out infinite',
      },
      keyframes: {
        'fade-in': {
          'from': { opacity: '0', transform: 'translateY(4px)' },
          'to': { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-in-left': {
          'from': { opacity: '0', transform: 'translateX(-8px)' },
          'to': { opacity: '1', transform: 'translateX(0)' },
        },
        'pulse-dot': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.4' },
        },
      },
      boxShadow: {
        'panel': '0 1px 3px rgba(0,0,0,0.3), 0 1px 2px rgba(0,0,0,0.4)',
        'dropdown': '0 8px 24px rgba(0,0,0,0.4)',
      },
    },
  },
  plugins: [],
}
