import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],

  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },

    // Required for MediaPipe WASM (SharedArrayBuffer + GPU delegate)
    headers: {
      'Cross-Origin-Opener-Policy':   'same-origin',
      'Cross-Origin-Embedder-Policy': 'require-corp',
    },
  },

  // Allow MediaPipe WASM assets to be fetched cross-origin
  optimizeDeps: {
    exclude: ['@mediapipe/tasks-vision'],
  },
})
