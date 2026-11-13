"use client";

import { FormEvent, useState } from "react";

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

export default function HomePage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!query.trim() || loading) return;
    setLoading(true);
    setError("");
    setResults(null);
    try {
      const response = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query.trim(), limit: 10 }),
      });
      const body: unknown = await response.json();
      if (!response.ok) {
        throw new Error(
          typeof body === "object" &&
            body !== null &&
            "error" in body &&
            typeof body.error === "string"
            ? body.error
            : "Search is unavailable",
        );
      }
      setResults(body as SearchResponse);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Search is unavailable");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ margin: "0 auto", maxWidth: 900, padding: "4rem 1.5rem" }}>
      <h1>Intelligent File Recommendation</h1>
      <p>Search your files using natural language.</p>
      <form onSubmit={submit} style={{ display: "flex", gap: 8, marginTop: 24 }}>
        <label htmlFor="file-search" style={{ position: "absolute", left: -10000 }}>
          Search files
        </label>
        <input
          id="file-search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="e.g. project architecture decisions"
          disabled={loading}
          style={{ flex: 1, padding: 12 }}
        />
        <button type="submit" disabled={loading || !query.trim()}>
          {loading ? "Searching..." : "Search"}
        </button>
      </form>
      {error && <p role="alert">{error}</p>}
      {loading && <p aria-live="polite">Searching your files...</p>}
      {!loading && results && results.recommendations.length === 0 && (
        <p role="status">{results.execution_summary}</p>
      )}
      {!loading && results && results.recommendations.length > 0 && (
        <section aria-label="Recommendations" style={{ marginTop: 32 }}>
          <p role="status">{results.execution_summary}</p>
          {results.recommendations.map((result) => (
            <article
              key={result.chunk_id}
              style={{ borderTop: "1px solid #ddd", padding: "1rem 0" }}
            >
              <h2 style={{ fontSize: "1.1rem" }}>{result.file.filename}</h2>
              <p>
                {result.file.extension ?? result.file.mimeType ?? "File"} ·
                reranking score {result.reranking_score.toFixed(3)}
              </p>
              <p>{result.text}</p>
              <small>
                {result.page_number ? `Page ${result.page_number} · ` : ""}
                {result.sheet_name ? `Sheet ${result.sheet_name} · ` : ""}
                {result.section_name ? `Section ${result.section_name} · ` : ""}
                Sources: {result.retrieval_sources.join(", ")}
              </small>
              <p>{result.explanation}</p>
              <small>File opening is not available in the current catalog UI.</small>
            </article>
          ))}
          <small>Trace ID: {results.trace_id}</small>
        </section>
      )}
    </main>
  );
}
