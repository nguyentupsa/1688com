import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    proxy: {
      '/novnc': {
        target: 'http://localhost:6901',   // ⚠ dùng localhost (hoặc IP máy thật)
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/novnc/, ''),
      },
    },
  },
})
