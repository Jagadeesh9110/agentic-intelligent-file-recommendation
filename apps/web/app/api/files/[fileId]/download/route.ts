
import { NextResponse } from "next/server";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { prisma } from "@/lib/prisma";

export const runtime = "nodejs";

const STORAGE_ROOT = path.resolve(
  process.env.FILE_STORAGE_DIR ??
    path.resolve(process.cwd(), "../../storage/uploads"),
);

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ fileId: string }> },
) {
  try {
    const { fileId } = await params;

    if (
      !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
        fileId,
      )
    ) {
      return NextResponse.json({ error: "Invalid file ID." }, { status: 400 });
    }

    const file = await prisma.file.findFirst({
      where: { id: fileId, catalogStatus: "ACTIVE" },
      select: {
        filename: true,
        relativePath: true,
        mimeType: true,
      },
    });

    if (!file) {
      return NextResponse.json({ error: "File not found." }, { status: 404 });
    }

    const filePath = path.resolve(STORAGE_ROOT, file.relativePath);
    const relative = path.relative(STORAGE_ROOT, filePath);

    if (
      relative.startsWith("..") ||
      path.isAbsolute(relative)
    ) {
      return NextResponse.json({ error: "Invalid storage path." }, { status: 400 });
    }

    const content = await readFile(filePath);

    return new Response(new Uint8Array(content), {
      headers: {
        "Content-Type": file.mimeType ?? "application/octet-stream",
        "Content-Disposition": `attachment; filename*=UTF-8''${encodeURIComponent(file.filename)}`,
        "Content-Length": String(content.length),
        "X-Content-Type-Options": "nosniff",
      },
    });
  } catch (error) {
    console.error("File download failed:", error);

    return NextResponse.json(
      { error: "Could not download file." },
      { status: 500 },
    );
  }
}
