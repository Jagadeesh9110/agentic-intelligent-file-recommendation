
import { NextResponse } from "next/server";

import {
  AiServiceError,
  searchAi,
} from "../../../lib/ai-client/search";
import { prisma } from "../../../lib/prisma";
import { parseSearchRequest } from "../../../lib/search-validation";

export const runtime = "nodejs";

export async function POST(request: Request) {
  let body: unknown;

  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { error: "Invalid JSON request" },
      { status: 400 },
    );
  }

  const parsed = parseSearchRequest(body);

  if (!parsed) {
    return NextResponse.json(
      { error: "A non-empty query is required" },
      { status: 400 },
    );
  }

  try {
    const aiResponse = await searchAi({
      query: parsed.query.trim(),
      limit: parsed.limit,
      retrieval: parsed.retrieval as
        | {
            strategy?: "full_text" | "semantic" | "hybrid";
            rrf_constant?: number;
          }
        | undefined,
    });

    // Get unique file IDs from the AI recommendations.
    const ids = [
      ...new Set(
        aiResponse.recommendations.map((item) => item.file_id),
      ),
    ];

    // Only include active files from the application catalog.
    const visibleFiles = await prisma.file.findMany({
      where: {
        id: { in: ids },
        catalogStatus: "ACTIVE",
      },
      select: {
        id: true,
        filename: true,
        extension: true,
        mimeType: true,
      },
    });

    const filesById = new Map(
      visibleFiles.map((file) => [file.id, file]),
    );

    // Keep only one recommendation per active file.
    const seenFileIds = new Set<string>();

    const recommendations = aiResponse.recommendations.flatMap((item) => {
      const file = filesById.get(item.file_id);

      if (!file || seenFileIds.has(item.file_id)) {
        return [];
      }

      seenFileIds.add(item.file_id);

      return [
        {
          ...item,
          file,
        },
      ];
    });

    // Recalculate the count after filtering and deduplication.
    return NextResponse.json({
      ...aiResponse,
      recommendations,
      summary: `Found ${recommendations.length} recommendation(s).`,
    });
  } catch (error) {
    if (error instanceof AiServiceError) {
      const status =
        error.code === "http" && error.statusCode === 422 ? 502 : 503;

      return NextResponse.json(
        { error: "AI search service is unavailable" },
        { status },
      );
    }

    console.error("Search route failed", error);

    return NextResponse.json(
      { error: "Search failed" },
      { status: 500 },
    );
  }
}
