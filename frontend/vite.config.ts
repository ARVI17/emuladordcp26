import {defineConfig} from 'vitest/config'
import react from '@vitejs/plugin-react'
import {VitePWA} from 'vite-plugin-pwa'
import {loadEnv} from 'vite'
const buildEnv=loadEnv('', '.', 'BUILD_')
const buildInfo={edition:'FC27',revision:buildEnv.BUILD_REVISION||'unknown',built_at:buildEnv.BUILD_DATE||'unknown',environment:buildEnv.BUILD_ENVIRONMENT||'development',source_dirty:buildEnv.BUILD_DIRTY==='true'}

export default defineConfig({
  define:{__BUILD_INFO__:JSON.stringify(buildInfo)},
  plugins:[{name:'build-info',generateBundle(){this.emitFile({type:'asset',fileName:'build.json',source:JSON.stringify(buildInfo)})}},react(),VitePWA({
    registerType:'autoUpdate',
    manifest:{name:'Club Lab FC27',short_name:'FC27 Lab',description:'Tu club, tus equipos y tu Galería local de FC 27',theme_color:'#090e1a',background_color:'#090e1a',display:'standalone',lang:'es',icons:[{src:'/icon.svg',sizes:'any',type:'image/svg+xml',purpose:'any maskable'}]},
    workbox:{navigateFallbackDenylist:[/^\/api(?:\/|$)/]},
  })],
  server:{proxy:{'/api':{target:'http://127.0.0.1:8000',changeOrigin:true,rewrite:path=>path.replace(/^\/api/,'')}}},
  test:{maxWorkers:2,environment:'jsdom',setupFiles:'./src/test/setup.ts',globals:true,include:['src/**/*.test.{ts,tsx}']},
})
