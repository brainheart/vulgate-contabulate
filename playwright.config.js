const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',
  timeout: 30000,
  retries: 0,
  workers: 2,
  use: {
    baseURL: 'http://localhost:8781',
    headless: true,
  },
  webServer: {
    command: 'python3 -m http.server 8781 -d docs',
    port: 8781,
    stdout: 'ignore',
    stderr: 'ignore',
    reuseExistingServer: false,
  },
});
