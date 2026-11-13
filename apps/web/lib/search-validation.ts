export type ValidSearchRequest = {
  query: string;
  limit?: number;
  retrieval?: { strategy?: string; rrf_constant?: number };
};

export function parseSearchRequest(
  body: unknown,
): ValidSearchRequest | null {
  if (typeof body !== "object" || body === null || !("query" in body)) {
    return null;
  }
  const value = body as {
    query?: unknown;
    limit?: unknown;
    retrieval?: unknown;
  };
  if (
    typeof value.query !== "string" ||
    value.query.trim().length === 0 ||
    value.query.length > 2000 ||
    (value.limit !== undefined &&
      (typeof value.limit !== "number" ||
        !Number.isInteger(value.limit) ||
        value.limit < 1 ||
        value.limit > 50))
  ) {
    return null;
  }
  return {
    query: value.query,
    limit: value.limit as number | undefined,
    retrieval:
      typeof value.retrieval === "object" && value.retrieval !== null
        ? (value.retrieval as { strategy?: string; rrf_constant?: number })
        : undefined,
  };
}
