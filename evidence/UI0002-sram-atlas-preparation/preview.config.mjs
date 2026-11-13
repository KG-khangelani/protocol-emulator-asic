import { defineConfig } from '../web/node_modules/@playwright/test/index.mjs';
import { fileURLToPath } from 'node:url';
export default defineConfig({
  testDir: './g2-sram-atlas-preparation-01', testMatch: 'preview.spec.mjs', workers: 1, timeout: 30000,
  outputDir: './g2-sram-atlas-preparation-01/browser-results',
  reporter: [['list'], ['json', { outputFile: './build/g2-sram-atlas-preparation-01/browser-results.json' }]],
  use: { baseURL: 'http://127.0.0.1:5179', browserName: 'chromium', viewport: { width: 1536, height: 960 } },
  webServer: { command: 'node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5179 --strictPort',
    cwd: fileURLToPath(new URL('../web', import.meta.url)), url: 'http://127.0.0.1:5179', timeout: 30000, reuseExistingServer: false },
});
