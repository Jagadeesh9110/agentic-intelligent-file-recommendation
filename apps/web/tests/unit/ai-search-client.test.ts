import assert from "node:assert/strict";
import test from "node:test";

import {
  AiServiceError,
  searchAi,
  type SearchFetchLike,
} from "../../lib/ai-client/search.ts";

const response = (body: unknown, status = 200): Response =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

test("searchAi sends the internal search request and validates the response", async () => {
  process.env.AI_SERVICE_BASE_URL = "http://127.0.0.1:8000";
  let requestBody = "";
  const fetchMock: SearchFetchLike = async (input, init) => {
    assert.equal(String(input), "http://127.0.0.1:8000/api/v1/search");
    requestBody = String(init?.body);
    return response({
      trace_id: "trace",
      query: "architecture",
      execution_status: "completed",
      strategy: "hybrid",
      recommendations: [],
      execution_summary: "No relevant files were found.",
      tool_calls: 3,
      refinement_attempted: false,
    });
  };

  const result = await searchAi({ query: "architecture" }, fetchMock);
  assert.equal(result.trace_id, "trace");
  assert.deepEqual(JSON.parse(requestBody), { query: "architecture" });
});

test("searchAi converts unavailable service responses to a typed error", async () => {
  process.env.AI_SERVICE_BASE_URL = "http://127.0.0.1:8000";
  const fetchMock: SearchFetchLike = async () => response({}, 503);

  await assert.rejects(() => searchAi({ query: "query" }, fetchMock), (error) => {
    assert.ok(error instanceof AiServiceError);
    assert.equal(error.code, "http");
    assert.equal(error.statusCode, 503);
    return true;
  });
});
