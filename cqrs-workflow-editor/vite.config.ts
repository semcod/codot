import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    open: true,
    proxy: {
      '/api/v1/workflows': {
        target: 'http://localhost:18001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      '/api/v1/examples': {
        target: 'http://localhost:18001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      '/api': {
        target: 'http://localhost:18080',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      '/data': {
        target: 'http://localhost:18091',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/data/, ''),
      },
      '/schemas': {
        target: 'http://localhost:18090',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/schemas/, ''),
      },
    },
  },
  root: '.',
  build: {
    outDir: 'dist'
  }
})
