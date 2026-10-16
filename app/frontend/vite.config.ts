import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// base=/words/：生产挂错题本同域子路径；开发代理到本地后端 8001
export default defineConfig({
  base: '/words/',
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/words/api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
    },
  },
})
