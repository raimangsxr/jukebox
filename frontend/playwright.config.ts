import { defineConfig, devices } from '@playwright/test';

const baseURL = process.env.E2E_BASE_URL ?? 'http://127.0.0.1:4300';

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  retries: 0,
  fullyParallel: false,
  workers: 1,
  use: {
    ...devices['Desktop Chrome'],
    baseURL,
    trace: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      testMatch: 'autoplay-policy.spec.ts',
    },
    {
      name: 'kiosk-chromium',
      testMatch: 'kiosk-playback-audio.spec.ts',
      use: {
        launchOptions: {
          args: ['--autoplay-policy=no-user-gesture-required'],
        },
      },
    },
  ],
  reporter: [['list']],
});
