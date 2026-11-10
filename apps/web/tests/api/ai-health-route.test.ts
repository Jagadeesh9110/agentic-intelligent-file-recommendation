import assert from "node:assert/strict";
import test from "node:test";

import { GET } from "../../app/api/health/ai/route.ts";

test("AI health route returns 503 when FastAPI is unavailable", async () => {
  process.env.AI_SERVICE_BASE_URL = "http://127.0.0.1:1";
  const response = await GET();

  assert.equal(response.status, 503);
  assert.deepEqual(await response.json(), {
    service: "ai",
    status: "error",
    error: "AI service is unavailable",
  });
});
