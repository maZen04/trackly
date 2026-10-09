import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The Django API has no CORS headers, so in development we proxy /api to it.
// Change the target if your Django server runs somewhere else.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_TARGET || 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
