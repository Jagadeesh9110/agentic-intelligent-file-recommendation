import assert from "node:assert/strict";
import test from "node:test";

import { parseSearchRequest } from "../../lib/search-validation.ts";

test("search request validation rejects empty queries before contacting AI", () => {
  assert.equal(parseSearchRequest({ query: " " }), null);
  assert.equal(parseSearchRequest({ query: "query", limit: 51 }), null);
  assert.deepEqual(parseSearchRequest({ query: " query ", limit: 5 }), {
    query: " query ",
    limit: 5,
    retrieval: undefined,
  });
});
