const DEFAULT_TIMEOUT_MS = 10_000;

export type AiSearchRequest = {
  query: string;
  limit?: number;
  retrieval?: {
    strategy?: "full_text" | "semantic" | "hybrid";
    rrf_constant?: number;
  };
};

export type AiRecommendation = {
  file_id: string;
  chunk_id: string;
  text: string;
  chunk_ordinal: number;
  page_number: number | null;
  sheet_name: string | null;
  section_name: string | null;
  retrieval_score: number;
  fused_score: number | null;
  reranking_score: number;
  retrieval_sources: string[];
  explanation: string;
};

export type AiSearchResponse = {
  trace_id: string;
  query: string;
  execution_status: string;
  strategy: string;
  recommendations: AiRecommendation[];
  execution_summary: string;
  tool_calls: number;
  refinement_attempted: boolean;
};

export type SearchFetchLike = (
  input: string | URL | Request,
  init?: RequestInit,
) => Promise<Response>;

function getBaseUrl(): string {
  const baseUrl = process.env.AI_SERVICE_BASE_URL;
  if (!baseUrl) {
    throw new AiServiceError(
      "AI_SERVICE_BASE_URL is not configured",
      "configuration",
    );
  }
  try {
    return new URL(baseUrl).toString().replace(/\/$/, "");
  } catch {
    throw new AiServiceError("AI_SERVICE_BASE_URL is invalid", "configuration");
  }
}

export class AiServiceError extends Error {
  readonly code: "configuration" | "timeout" | "connection" | "http";
  readonly statusCode?: number;

  constructor(
    message: string,
    code: "configuration" | "timeout" | "connection" | "http",
    statusCode?: number,
  ) {
    super(message);
    this.name = "AiServiceError";
    this.code = code;
    this.statusCode = statusCode;
  }
}

function isResponse(value: unknown): value is AiSearchResponse {
  return (
    typeof value === "object" &&
    value !== null &&
    "trace_id" in value &&
    typeof value.trace_id === "string" &&
    "recommendations" in value &&
    Array.isArray(value.recommendations)
  );
}

export async function searchAi(
  request: AiSearchRequest,
  fetchImpl: SearchFetchLike = fetch,
  timeoutMs = DEFAULT_TIMEOUT_MS,
): Promise<AiSearchResponse> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  const apiKey = process.env.AI_SERVICE_API_KEY;
  try {
    const response = await fetchImpl(`${getBaseUrl()}/api/v1/search`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...(apiKey ? { "X-AI-Service-Key": apiKey } : {}),
      },
      body: JSON.stringify(request),
      signal: controller.signal,
      cache: "no-store",
    });
    if (!response.ok) {
      throw new AiServiceError(
        `AI search returned HTTP ${response.status}`,
        "http",
        response.status,
      );
    }
    const body: unknown = await response.json();
    if (!isResponse(body)) {
      throw new AiServiceError("AI search response has an invalid shape", "http");
    }
    return body;
  } catch (error) {
    if (error instanceof AiServiceError) throw error;
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new AiServiceError("AI search timed out", "timeout");
    }
    throw new AiServiceError("AI service could not be reached", "connection");
  } finally {
    clearTimeout(timeout);
  }
}
