
interface IngestFileInput {
  fileId: string;
  file: File;
}

interface IngestFileResult {
  status: string;
  checksum: string;
  chunk_count: number;
  embedding_count: number;
}

export async function ingestFile({
  fileId,
  file,
}: IngestFileInput): Promise<IngestFileResult> {
  const baseUrl = process.env.AI_SERVICE_BASE_URL;
  const apiKey = process.env.AI_SERVICE_API_KEY;

  if (!baseUrl) {
    throw new Error("AI service URL is not configured.");
  }

  if (!apiKey) {
    throw new Error("AI service API key is not configured.");
  }

  const formData = new FormData();
  formData.append("file_id", fileId);
  formData.append("file", file);

  const response = await fetch(`${baseUrl}/api/v1/files/ingest`, {
    method: "POST",
    headers: {
      "X-AI-Service-Key": apiKey,
    },
    body: formData,
    cache: "no-store",
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(
      error?.detail ?? `AI ingestion failed (${response.status}).`,
    );
  }

  return response.json() as Promise<IngestFileResult>;
}
