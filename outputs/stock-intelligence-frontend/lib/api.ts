import type { AnalyzeResponse } from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type AnalyzeStockOptions = {
  concallTranscript?: string;
  concallTranscriptUrl?: string;
};

export async function analyzeStock(
  stock: string,
  options: AnalyzeStockOptions = {}
): Promise<AnalyzeResponse> {

  const controller = new AbortController();

  const timeoutId = setTimeout(() => {
    controller.abort();
  }, 20000);

  try {
    const response = await fetch(
      `${API_BASE_URL}/analyze`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        signal: controller.signal,
        body: JSON.stringify({
          stock,
          concall_transcript:
            options.concallTranscript || undefined,
          concall_transcript_url:
            options.concallTranscriptUrl || undefined
        })
      }
    );

    clearTimeout(timeoutId);

    if (!response.ok) {
      const errorBody = await response.json().catch(() => null);
      const message =
        errorBody?.error?.message ??
        "Unable to analyze stock";
      throw new Error(message);
    }

    return response.json();
  }
  catch (error) {
    clearTimeout(timeoutId);

    if (error instanceof DOMException &&
        error.name === "AbortError") {
      throw new Error(
        "Analysis timed out after 20 seconds"
      );
    }

    throw error;
  }
}