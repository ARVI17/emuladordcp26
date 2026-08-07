import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [react(), VitePWA({ registerType: 'autoUpdate', manifest: { name: 'Asistente FC 26', short_name: 'FC26', description: 'Inventario y optimizador DCP local', theme_color: '#111827', background_color: '#0b1120', display: 'standalone', lang: 'es', icons: [{ src: '/icon.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'any maskable' }] } })],
  test: { environment: 'jsdom', setupFiles: './src/test/setup.ts', globals: true, include: ['src/**/*.test.{ts,tsx}'] },
})
