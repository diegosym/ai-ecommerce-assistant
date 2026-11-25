import { tmpdir } from "node:os";
import { join } from "node:path";

// Root-owned runner: config and specs must share one Playwright installation.
import { defineConfig, devices } from "../node_modules/@playwright/test";

export default defineConfig({
  testDir: "../tests/e2e",
  fullyParallel: false,
  workers: 1,
  reporter: "list",
  outputDir: join(tmpdir(), "ai-ecommerce-assistant-playwright"),
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile-chromium", use: { ...devices["Pixel 5"] } },
  ],
  webServer: [
    {
      command:
        "cd .. && AI_PROVIDER=fake uv run uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 18000",
      url: "http://127.0.0.1:18000/openapi.json",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: "ASSISTANT_API_URL=http://127.0.0.1:18000/api/v1 npm run dev",
      url: "http://127.0.0.1:3000",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
