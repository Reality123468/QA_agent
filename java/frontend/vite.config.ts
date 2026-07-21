import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api/auth':      'http://localhost:8080',
      '/api/documents':  'http://localhost:8081',
      '/api/chat':       'http://localhost:8082',
      '/api/audit':      'http://localhost:8083'
    }
  },
  build: {
    outDir: 'spring/src/main/resources/static',
    emptyOutDir: true
  }
})
