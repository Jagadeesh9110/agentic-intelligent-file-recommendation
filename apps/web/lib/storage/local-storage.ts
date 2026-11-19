import {
  createHash,
  randomUUID,
} from "node:crypto";
import {
  mkdir,
  rename,
  rm,
  writeFile,
} from "node:fs/promises";
import path from "node:path";

const MAX_FILE_SIZE = 25 * 1024 * 1024;

const ALLOWED_EXTENSIONS = new Set([
  ".pdf",
  ".docx",
  ".xlsx",
  ".csv",
  ".txt",
]);

export class FileStorageError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "FileStorageError";
  }
}

export interface StoredFile {
  fileId: string;
  filename: string;
  extension: string;
  sizeBytes: number;
  checksum: string;
  relativePath: string;
}

function getStorageRoot(): string {
  const configuredPath = process.env.FILE_STORAGE_DIR;

  return configuredPath
    ? path.resolve(configuredPath)
    : path.resolve(process.cwd(), "../../storage/uploads");
}

function sanitizeFilename(originalName: string): string {
  const basename = path.basename(originalName);
  const sanitized = basename
    .normalize("NFKC")
    .replace(/[^\p{L}\p{N}._ -]/gu, "_")
    .replace(/^[. ]+|[. ]+$/g, "")
    .slice(0, 180);

  if (!sanitized || sanitized === "." || sanitized === "..") {
    throw new FileStorageError("Invalid filename.");
  }

  return sanitized;
}

export async function storeUploadedFile(
  file: File,
  fileId: string = randomUUID(),
): Promise<StoredFile> {
  if (!file || file.size === 0) {
    throw new FileStorageError("Uploaded file is empty.");
  }

  if (file.size > MAX_FILE_SIZE) {
    throw new FileStorageError("Maximum upload size is 25 MB.");
  }

  const filename = sanitizeFilename(file.name);
  const extension = path.extname(filename).toLowerCase();

  if (!ALLOWED_EXTENSIONS.has(extension)) {
    throw new FileStorageError("Unsupported file format.");
  }

  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(fileId)) {
    throw new FileStorageError("Invalid file identifier.");
  }

  const content = Buffer.from(await file.arrayBuffer());

  if (content.length !== file.size) {
    throw new FileStorageError("Uploaded file size mismatch.");
  }

  const checksum = createHash("sha256")
    .update(content)
    .digest("hex");

  const root = getStorageRoot();
  const relativePath = path.posix.join(fileId, filename);
  const destinationDirectory = path.join(root, fileId);
  const destinationPath = path.join(destinationDirectory, filename);
  const temporaryPath = path.join(
    destinationDirectory,
    `.upload-${randomUUID()}.tmp`,
  );

  await mkdir(destinationDirectory, { recursive: true });

  try {
    await writeFile(temporaryPath, content, { flag: "wx" });
    await rename(temporaryPath, destinationPath);
  } catch (error) {
    await rm(temporaryPath, { force: true }).catch(() => undefined);

    throw new FileStorageError(
      `Could not store uploaded file: ${
        error instanceof Error ? error.message : "Unknown storage error"
      }`,
    );
  }

  return {
    fileId,
    filename,
    extension,
    sizeBytes: content.length,
    checksum,
    relativePath,
  };
}