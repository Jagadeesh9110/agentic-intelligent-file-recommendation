import {
  AiServiceError,
  getAiHealth,
} from "../../../../lib/ai-client/health.ts";

export async function GET() {
  try {
    const health = await getAiHealth();

    return Response.json({
      service: "ai",
      status: "ok",
      ai: health,
    });
  } catch (error) {
    if (error instanceof AiServiceError) {
      console.error("AI service health check failed", {
        code: error.code,
        statusCode: error.statusCode,
      });
    } else {
      console.error("Unexpected AI service health check failure", error);
    }

    return Response.json(
      {
        service: "ai",
        status: "error",
        error: "AI service is unavailable",
      },
      { status: 503 },
    );
  }
}
