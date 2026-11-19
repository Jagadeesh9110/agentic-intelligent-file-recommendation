
import { NextResponse } from "next/server";
import { randomUUID } from "node:crypto";
import { prisma } from "@/lib/prisma";
import {
  FileStorageError,
  storeUploadedFile,
} from "@/lib/storage/local-storage";
import { ingestFile } from "@/lib/ai-client/ingest";

export const runtime = "nodejs";

const MAX_FILE_SIZE = 25 * 1024 * 1024;

const ALLOWED_EXTENSIONS = new Set([
  ".pdf",
  ".docx",
  ".xlsx",
  ".csv",
  ".txt",
]);

export async function POST(request: Request) {
  let storedFile: Awaited<ReturnType<typeof storeUploadedFile>> | null = null;

  try {
    const formData = await request.formData();
    const file = formData.get("file");

    if (!(file instanceof File)) {
      return NextResponse.json(
        { error: "A file is required." },
        { status: 400 },
      );
    }

    if (file.size === 0) {
      return NextResponse.json(
        { error: "The uploaded file is empty." },
        { status: 400 },
      );
    }

    if (file.size > MAX_FILE_SIZE) {
      return NextResponse.json(
        { error: "Maximum upload size is 25 MB." },
        { status: 413 },
      );
    }

    const extension = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();

    if (!ALLOWED_EXTENSIONS.has(extension)) {
      return NextResponse.json(
        { error: "Supported formats: PDF, DOCX, XLSX, CSV and TXT." },
        { status: 415 },
      );
    }

    const fileId = randomUUID();

    storedFile = await storeUploadedFile(file, fileId);

    const ingestion = await ingestFile({ fileId, file });

    const record = await prisma.file.create({
      data: {
        id: fileId,
        relativePath: storedFile.relativePath,
        filename: storedFile.filename,
        extension: storedFile.extension,
        mimeType: file.type || "application/octet-stream",
        sizeBytes: BigInt(storedFile.sizeBytes),
        checksum: storedFile.checksum,
        catalogStatus: "ACTIVE",
      },
      select: {
        id: true,
        filename: true,
        extension: true,
        sizeBytes: true,
        createdAt: true,
      },
    });

    return NextResponse.json(
      {
        file: {
          ...record,
          sizeBytes: record.sizeBytes.toString(),
        },
        ingestion,
      },
      { status: 201 },
    );
  } catch (error) {
    console.error("File upload failed:", error);

    if (error instanceof FileStorageError) {
      return NextResponse.json(
        { error: error.message },
        { status: 400 },
      );
    }

    return NextResponse.json(
      {
        error: error instanceof Error
          ? error.message
          : "File upload failed.",
      },
      { status: 500 },
    );
  }
}
