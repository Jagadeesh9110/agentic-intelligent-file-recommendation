
import { NextResponse } from "next/server";
import { rm } from "node:fs/promises";
import path from "node:path";
import { prisma } from "@/lib/prisma";

export const runtime = "nodejs";

const STORAGE_ROOT = path.resolve(
  process.env.FILE_STORAGE_DIR ??
    path.resolve(process.cwd(), "../../storage/uploads"),
);

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ fileId: string }> },
) {
  try {
    const { fileId } = await params;

    if (
      !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(fileId)
    ) {
      return NextResponse.json({ error: "Invalid file ID." }, { status: 400 });
    }

    const file = await prisma.file.findFirst({
      where: { id: fileId, catalogStatus: "ACTIVE" },
      select: { id: true, relativePath: true },
    });

    if (!file) {
      return NextResponse.json({ error: "File not found." }, { status: 404 });
    }

    await prisma.file.update({
      where: { id: fileId },
      data: {
        catalogStatus: "DELETED",
        deletedAt: new Date(),
        deletionReason: "Deleted by user",
      },
    });

    const filePath = path.resolve(STORAGE_ROOT, file.relativePath);
    const relative = path.relative(STORAGE_ROOT, filePath);

    if (relative.startsWith("..") || path.isAbsolute(relative)) {
      console.error("Unsafe storage path for file:", fileId);
      return NextResponse.json(
        { error: "File removed from library, but storage cleanup failed." },
        { status: 500 },
      );
    }

    await rm(filePath, { force: true });

    return NextResponse.json({ success: true, fileId });
  } catch (error) {
    console.error("File deletion failed:", error);

    return NextResponse.json(
      { error: "Could not delete file." },
      { status: 500 },
    );
  }
}
