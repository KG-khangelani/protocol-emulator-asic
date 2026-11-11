// SPDX-License-Identifier: Apache-2.0
import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests', timeout: 30000, fullyParallel: false, workers: 1,
  outputDir: '../build/atlas-qa/results', reporter: [['list'], ['json', { outputFile: '../build/atlas-qa/results.json' }]],
  use: { baseURL: 'http://127.0.0.1:5179', browserName: 'chromium', viewport: { width: 1536, height: 960 }, trace: 'retain-on-failure' },
  webServer: { command: 'npm run dev', url: 'http://127.0.0.1:5179', timeout: 30000, reuseExistingServer: false },
});
