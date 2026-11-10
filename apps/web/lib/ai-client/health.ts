const DEFAULT_TIMEOUT_MS = 3_000;

export type AiHealthResponse = {
  status: string;
};

export type FetchLike = (
  input: string | URL | Request,
  init?: RequestInit,
) => Promise<Response>;

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
    throw new AiServiceError(
      "AI_SERVICE_BASE_URL is invalid",
      "configuration",
    );
  }
}

export async function getAiHealth(
  fetchImpl: FetchLike = fetch,
  timeoutMs = DEFAULT_TIMEOUT_MS,
): Promise<AiHealthResponse> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  const apiKey = process.env.AI_SERVICE_API_KEY;

  try {
    const response = await fetchImpl(`${getBaseUrl()}/health`, {
      headers: {
        Accept: "application/json",
        ...(apiKey ? { "X-AI-Service-Key": apiKey } : {}),
      },
      signal: controller.signal,
      cache: "no-store",
    });

    if (!response.ok) {
      throw new AiServiceError(
        `AI service health check returned HTTP ${response.status}`,
        "http",
        response.status,
      );
    }

    const body: unknown = await response.json();

    if (
      typeof body !== "object" ||
      body === null ||
      !("status" in body) ||
      typeof body.status !== "string"
    ) {
      throw new AiServiceError(
        "AI service health response has an invalid shape",
        "http",
      );
    }

    return { status: body.status };
  } catch (error) {
    if (error instanceof AiServiceError) {
      throw error;
    }

    if (error instanceof DOMException && error.name === "AbortError") {
      throw new AiServiceError(
        "AI service health check timed out",
        "timeout",
      );
    }

    throw new AiServiceError(
      "AI service could not be reached",
      "connection",
    );
  } finally {
    clearTimeout(timeout);
  }
}
