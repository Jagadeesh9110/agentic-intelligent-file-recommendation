import assert from "node:assert/strict";
import test from "node:test";

import {
  AiServiceError,
  getAiHealth,
  type FetchLike,
} from "../../lib/ai-client/health.ts";

const jsonResponse = (body: unknown, status = 200): Response =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

test("getAiHealth returns the FastAPI health response", async () => {
  process.env.AI_SERVICE_BASE_URL = "http://127.0.0.1:8000";
  let requestedUrl = "";

  const fetchMock: FetchLike = async (input) => {
    requestedUrl = String(input);
    return jsonResponse({ status: "ok" });
  };

  await assert.doesNotReject(() => getAiHealth(fetchMock));
  assert.equal(requestedUrl, "http://127.0.0.1:8000/health");
});

test("getAiHealth converts connection failures to AiServiceError", async () => {
  process.env.AI_SERVICE_BASE_URL = "http://127.0.0.1:8000";
  const fetchMock: FetchLike = async () => {
    throw new TypeError("fetch failed");
  };

  await assert.rejects(() => getAiHealth(fetchMock), (error: unknown) => {
    assert.ok(error instanceof AiServiceError);
    assert.equal(error.code, "connection");
    return true;
  });
});
