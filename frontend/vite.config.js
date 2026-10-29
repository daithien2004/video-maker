import { defineConfig } from 'vite'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [tailwindcss()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  server: {
    port: 5173,
    proxy: { '/api': 'http://127.0.0.1:7860' },
  },
  build: {
    target: 'es2022',
    rollupOptions: {
      onwarn(warning, warn) {
        // Client-only Vite builds do not need the RSC marker used by Radix.
        if (warning.code === 'MODULE_LEVEL_DIRECTIVE' && warning.message.includes('use client')) return
        warn(warning)
      },
    },
  },
  esbuild: { jsx: 'automatic' },
})
