import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  timeout: 120_000,        // 2 min per test — LLM is slow
  expect: { timeout: 10_000 },
  use: {
    baseURL: 'http://localhost:3000',
    headless: true,
  },
  reporter: 'list',
})
