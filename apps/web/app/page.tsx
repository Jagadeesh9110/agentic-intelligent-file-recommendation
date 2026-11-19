
"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";

type SearchResult = {
  file_id: string;
  chunk_id: string;
  text: string;
  page_number: number | null;
  sheet_name: string | null;
  section_name: string | null;
  reranking_score: number;
  retrieval_sources: string[];
  explanation: string;
  file: {
    filename: string;
    extension: string | null;
    mimeType: string | null;
  };
};

type SearchResponse = {
  trace_id: string;
  recommendations: SearchResult[];
  execution_summary: string;
};

type UploadResponse = {
  file?: { filename: string };
  error?: string;
};

type DeleteResponse = {
  success?: boolean;
  error?: string;
};

type LibraryFile = {
  id: string;
  filename: string;
  extension: string | null;
  mimeType: string | null;
  sizeBytes: string;
  createdAt: string;
};

export default function HomePage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [deletingFileId, setDeletingFileId] = useState<string | null>(null);
  const [uploadMessage, setUploadMessage] = useState("");
  const [files, setFiles] = useState<LibraryFile[]>([]);
  const [filesLoading, setFilesLoading] = useState(true);

  const fileInput = useRef<HTMLInputElement>(null);

  async function loadFiles() {
    const response = await fetch("/api/files", {
      cache: "no-store",
    });

    if (!response.ok) {
      throw new Error("Could not load your file library.");
    }

    const data: { files: LibraryFile[] } = await response.json();
    setFiles(data.files);
  }

  useEffect(() => {
    let active = true;

    async function initializeLibrary() {
      try {
        const response = await fetch("/api/files", {
          cache: "no-store",
        });

        if (!response.ok) {
          throw new Error("Could not load your file library.");
        }

        const data: { files: LibraryFile[] } = await response.json();

        if (active) {
          setFiles(data.files);
        }
      } catch (caught) {
        console.error("File library loading failed:", caught);
      } finally {
        if (active) {
          setFilesLoading(false);
        }
      }
    }

    void initializeLibrary();

    return () => {
      active = false;
    };
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!query.trim() || loading) return;

    setLoading(true);
    setError("");
    setResults(null);

    try {
      const response = await fetch("/api/search", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: query.trim(),
          limit: 10,
        }),
      });

      const body: unknown = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof body === "object" &&
            body !== null &&
            "error" in body &&
            typeof body.error === "string"
            ? body.error
            : "Search is unavailable.",
        );
      }

      setResults(body as SearchResponse);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Search failed.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const file = fileInput.current?.files?.[0];

    if (!file || uploading) return;

    setUploading(true);
    setError("");
    setUploadMessage("");

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch("/api/files/upload", {
        method: "POST",
        body: formData,
      });

      const body = (await response.json()) as UploadResponse;

      if (!response.ok) {
        throw new Error(body.error ?? "File upload failed.");
      }

      await loadFiles();

      setUploadMessage(
        `${body.file?.filename ?? file.name} uploaded and processed successfully.`,
      );

      if (fileInput.current) {
        fileInput.current.value = "";
      }
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Upload failed.",
      );
    } finally {
      setUploading(false);
    }
  }

  async function deleteFile(fileId: string, filename: string) {
    if (
      !window.confirm(
        `Delete "${filename}"? This cannot be undone.`,
      )
    ) {
      return;
    }

    setDeletingFileId(fileId);
    setError("");
    setUploadMessage("");

    try {
      const response = await fetch(`/api/files/${fileId}`, {
        method: "DELETE",
      });

      const data = (await response.json()) as DeleteResponse;

      if (!response.ok) {
        throw new Error(data.error ?? "Could not delete file.");
      }

      setFiles((current) =>
        current.filter((file) => file.id !== fileId),
      );

      setResults((current) =>
        current
          ? {
              ...current,
              recommendations: current.recommendations.filter(
                (item) => item.file_id !== fileId,
              ),
            }
          : null,
      );

      setUploadMessage(`${filename} deleted successfully.`);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Could not delete file.",
      );

      try {
        await loadFiles();
      } catch (refreshError) {
        console.error("File library refresh failed:", refreshError);
      }
    } finally {
      setDeletingFileId(null);
    }
  }

  return (
    <main
      style={{
        margin: "0 auto",
        maxWidth: 900,
        padding: "4rem 1.5rem",
      }}
    >
      <h1>Intelligent File Recommendation</h1>

      <p>
        Upload your documents and discover relevant files using natural
        language.
      </p>

      <section style={{ marginTop: 32 }}>
        <h2>Upload documents</h2>

        <form
          onSubmit={upload}
          style={{
            display: "flex",
            gap: 12,
            flexWrap: "wrap",
            marginTop: 16,
          }}
        >
          <input
            ref={fileInput}
            type="file"
            accept=".pdf,.docx,.xlsx,.csv,.txt"
            required
            disabled={uploading}
          />

          <button type="submit" disabled={uploading}>
            {uploading ? "Uploading and processing..." : "Upload"}
          </button>
        </form>

        <small>
          PDF, DOCX, XLSX, CSV and TXT · Maximum 25 MB
        </small>
      </section>

      {uploadMessage && (
        <p role="status" style={{ marginTop: 12 }}>
          {uploadMessage}
        </p>
      )}

      {error && (
        <p role="alert" style={{ color: "red", marginTop: 12 }}>
          {error}
        </p>
      )}

      <hr style={{ margin: "32px 0" }} />

      <section>
        <h2>Your File Library</h2>

        {filesLoading && <p>Loading files...</p>}

        {!filesLoading && files.length === 0 && (
          <p>No files uploaded yet.</p>
        )}

        {files.map((file) => (
          <article
            key={file.id}
            style={{
              borderTop: "1px solid #ddd",
              padding: "12px 0",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: 12,
              flexWrap: "wrap",
            }}
          >
            <div>
              <strong>{file.filename}</strong>

              <p style={{ margin: "4px 0", fontSize: 13 }}>
                {file.extension ?? file.mimeType ?? "File"} ·{" "}
                {(Number(file.sizeBytes) / 1024).toFixed(1)} KB
              </p>
            </div>

            <div style={{ display: "flex", gap: 12 }}>
              <a href={`/api/files/${file.id}/download`}>
                Download
              </a>

              <button
                type="button"
                onClick={() => deleteFile(file.id, file.filename)}
                disabled={deletingFileId !== null}
                style={{
                  color: "red",
                  cursor:
                    deletingFileId !== null ? "not-allowed" : "pointer",
                }}
              >
                {deletingFileId === file.id ? "Deleting..." : "Delete"}
              </button>
            </div>
          </article>
        ))}
      </section>

      <hr style={{ margin: "32px 0" }} />

      <section>
        <h2>Search your files</h2>

        <form
          onSubmit={submit}
          style={{
            display: "flex",
            gap: 8,
            marginTop: 16,
          }}
        >
          <label
            htmlFor="file-search"
            style={{
              position: "absolute",
              left: -10000,
            }}
          >
            Search files
          </label>

          <input
            id="file-search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="e.g. project architecture decisions"
            disabled={loading}
            style={{
              flex: 1,
              padding: 12,
            }}
          />

          <button
            type="submit"
            disabled={loading || !query.trim()}
          >
            {loading ? "Searching..." : "Search"}
          </button>
        </form>

        {loading && (
          <p aria-live="polite">Searching your files...</p>
        )}

        {!loading &&
          results &&
          results.recommendations.length === 0 && (
            <p role="status">{`Found ${results.recommendations.length} recommendation(s).`}</p>
          )}

        {!loading &&
          results &&
          results.recommendations.length > 0 && (
            <section
              aria-label="Recommendations"
              style={{ marginTop: 32 }}
            >
              <p role="status">{`Found ${results.recommendations.length} recommendation(s).`}</p>

              {results.recommendations.map((result) => (
                <article
                  key={result.chunk_id}
                  style={{
                    borderTop: "1px solid #ddd",
                    padding: "1rem 0",
                  }}
                >
                  <h3>{result.file.filename}</h3>

                  <p>
                    {result.file.extension ??
                      result.file.mimeType ??
                      "File"}{" "}
                    · Reranking score:{" "}
                    {result.reranking_score.toFixed(3)}
                  </p>

                  <p>{result.text}</p>

                  <small>
                    {result.page_number
                      ? `Page ${result.page_number} · `
                      : ""}
                    {result.sheet_name
                      ? `Sheet ${result.sheet_name} · `
                      : ""}
                    {result.section_name
                      ? `Section ${result.section_name} · `
                      : ""}
                    Sources: {result.retrieval_sources.join(", ")}
                  </small>

                  <p>{result.explanation}</p>

                  <a
                    href={`/api/files/${result.file_id}/download`}
                  >
                    Download recommended file
                  </a>
                </article>
              ))}

              <small>Trace ID: {results.trace_id}</small>
            </section>
          )}
      </section>
    </main>
  );
}
