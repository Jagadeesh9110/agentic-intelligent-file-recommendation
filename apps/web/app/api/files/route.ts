
import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export const runtime = "nodejs";

export async function GET() {
  try {
    const files = await prisma.file.findMany({
      where: { catalogStatus: "ACTIVE" },
      orderBy: { createdAt: "desc" },
      select: {
        id: true,
        filename: true,
        extension: true,
        mimeType: true,
        sizeBytes: true,
        checksum: true,
        createdAt: true,
      },
    });

    return NextResponse.json({
      files: files.map((file) => ({
        ...file,
        sizeBytes: file.sizeBytes.toString(),
      })),
    });
  } catch (error) {
    console.error("File listing failed:", error);

    return NextResponse.json(
      { error: "Could not load files." },
      { status: 500 },
    );
  }
}
