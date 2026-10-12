import {defineConfig} from 'vitest/config'
import react from '@vitejs/plugin-react'
import {VitePWA} from 'vite-plugin-pwa'

export default defineConfig({
  plugins:[react(),VitePWA({
    registerType:'autoUpdate',
    manifest:{name:'Club Lab FC27',short_name:'FC27 Lab',description:'Tu club, tus equipos y tu Galería local de FC 27',theme_color:'#090e1a',background_color:'#090e1a',display:'standalone',lang:'es',icons:[{src:'/icon.svg',sizes:'any',type:'image/svg+xml',purpose:'any maskable'}]},
    workbox:{navigateFallbackDenylist:[/^\/api(?:\/|$)/]},
  })],
  server:{proxy:{'/api':{target:'http://127.0.0.1:8000',changeOrigin:true,rewrite:path=>path.replace(/^\/api/,'')}}},
  test:{environment:'jsdom',setupFiles:'./src/test/setup.ts',globals:true,include:['src/**/*.test.{ts,tsx}']},
})
