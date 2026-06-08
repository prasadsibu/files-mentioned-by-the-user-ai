import type { AnalyzeResponse } from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type AnalyzeStockOptions = {
  concallTranscript?: string;
  concallTranscriptUrl?: string;
};

export async function analyzeStock(stock: string, options: AnalyzeStockOptions = {}): Promise<AnalyzeResponse> {
  const response = await fetch(`${API_BASE_URL}/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      stock,
      concall_transcript: options.concallTranscript || undefined,
      concall_transcript_url: options.concallTranscriptUrl || undefined
    })
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    const message = errorBody?.error?.message ?? "Unable to analyze stock";
    throw new Error(message);
  }

  return response.json();
}
