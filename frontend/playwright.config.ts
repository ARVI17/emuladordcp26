import { defineConfig, devices } from '@playwright/test'
const externalBaseUrl = process.env.PLAYWRIGHT_BASE_URL
export default defineConfig({
  testDir: './e2e', workers: 1, use: { baseURL: externalBaseUrl || 'http://127.0.0.1:5173', trace: 'on-first-retry' },
  webServer: externalBaseUrl ? undefined : { command: 'npm run dev', port: 5173, reuseExistingServer: true },
  projects: [
    {name:'Móvil Chromium',use:{...devices['iPhone 13'],browserName:'chromium'}},
    {name:'Escritorio Chromium',use:{...devices['Desktop Chrome'],viewport:{width:1280,height:900}}},
  ],
})
