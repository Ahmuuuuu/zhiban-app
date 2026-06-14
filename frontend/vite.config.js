import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      '/static': 'http://127.0.0.1:2221',
      '/ai_chat': 'http://127.0.0.1:2221',
      '/ai_portrait': 'http://127.0.0.1:2221',
      '/path': 'http://127.0.0.1:2221',
      '/learning_path': 'http://127.0.0.1:2221',
      '/resource': 'http://127.0.0.1:2221',
      '/image': 'http://127.0.0.1:2221',
      '/knowledge': 'http://127.0.0.1:2221',
      '/user': 'http://127.0.0.1:2221',
      '/admin': 'http://127.0.0.1:2221',
      '/exam': 'http://127.0.0.1:2221',
      '/video': 'http://127.0.0.1:2221',
      '/study': 'http://127.0.0.1:2221',
      '/presentation': 'http://127.0.0.1:2221',
      '/notification': 'http://127.0.0.1:2221',
      '/annotation': 'http://127.0.0.1:2221',
      '/debug': 'http://127.0.0.1:2221',
    },
  },
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: `@use "@/assets/styles/base-style.scss" as *;`
      }
    }
  }
})