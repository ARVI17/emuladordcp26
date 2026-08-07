import { defineConfig, devices } from '@playwright/test'
const externalBaseUrl = process.env.PLAYWRIGHT_BASE_URL
export default defineConfig({
  testDir: './e2e', use: { baseURL: externalBaseUrl || 'http://localhost:8080', trace: 'on-first-retry' },
  webServer: externalBaseUrl ? undefined : { command: 'npm run dev', port: 5173, reuseExistingServer: true },
  projects: [{ name: 'iPhone', use: { ...devices['iPhone 13'] } }],
})
