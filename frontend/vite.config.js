import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import basicSsl from '@vitejs/plugin-basic-ssl'

export default defineConfig({
  plugins: [react(), basicSsl()],
  server: {
    proxy: {
      '/ws': {
        target: 'ws://127.0.0.1:8888',
        ws: true,
      },
      '/agent': {
        target: 'http://127.0.0.1:8888',
      },
      '/prompts': {
        target: 'http://127.0.0.1:8888',
      },
      '/run': {
        target: 'http://127.0.0.1:8888',
      },
      '/health': {
        target: 'http://127.0.0.1:8888',
      },
      '/scheduler': {
        target: 'http://127.0.0.1:8888',
      },
      '/workspace': {
        target: 'http://127.0.0.1:8888',
      },
      '/metrics': {
        target: 'http://127.0.0.1:8888',
      },
      '/custom-agents': {
        target: 'http://127.0.0.1:8888',
      },
      '/memory': {
        target: 'http://127.0.0.1:8888',
      },
      '/chat': {
        target: 'http://127.0.0.1:8888',
      },
      '/mcp': {
        target: 'http://127.0.0.1:8888',
      },
      '/agents': {
        target: 'http://127.0.0.1:8888',
      },
      '/canvas': {
        target: 'http://127.0.0.1:8888',
      },
      '/session': {
        target: 'http://127.0.0.1:8888',
      },
      '/sessions': {
        target: 'http://127.0.0.1:8888',
      },
      '/executors': {
        target: 'http://127.0.0.1:8888',
      },
      '/stop': {
        target: 'http://127.0.0.1:8888',
      },
      '/persona': {
        target: 'http://127.0.0.1:8888',
      },
      '/execute': {
        target: 'http://127.0.0.1:8888',
      },
      '/config': {
        target: 'http://127.0.0.1:8888',
      },
      '/run-node': {
        target: 'http://127.0.0.1:8888',
      },
      '/run-legacy': {
        target: 'http://127.0.0.1:8888',
      },
      '/transcribe': {
        target: 'http://127.0.0.1:8888',
      },
    },
  },
})
