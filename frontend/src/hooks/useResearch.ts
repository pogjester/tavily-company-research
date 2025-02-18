import { useState, useEffect, useCallback } from "react";
import {
  ResearchRequest,
  ResearchResponse,
  ResearchStatus,
} from "../lib/types";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export function useResearch() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<ResearchStatus | null>(null);

  // Start research
  const startResearch = async (data: ResearchRequest) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/research`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        throw new Error("Failed to start research");
      }

      const result: ResearchResponse = await response.json();
      setJobId(result.job_id);
      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  // Set up SSE connection when jobId changes
  useEffect(() => {
    if (!jobId) return;

    const eventSource = new EventSource(
      `${API_BASE_URL}/research/stream/${jobId}`
    );

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        // Update status based on the SSE data
        setStatus((prevStatus) => ({
          status: data.status,
          progress: data.progress,
          debug_info: [
            ...(prevStatus?.debug_info || []),
            ...(data.message
              ? [{ timestamp: data.timestamp, message: data.message }]
              : []),
          ],
          last_update: data.timestamp,
          result: data.result,
          error: data.error,
        }));

        // Update loading state
        setIsLoading(data.status === "processing");

        // Update error state
        setError(data.error || null);

        // Close connection if research is complete or failed
        if (data.status === "completed" || data.status === "failed") {
          eventSource.close();
        }
      } catch (err) {
        console.error("Error parsing SSE data:", err);
      }
    };

    eventSource.onerror = (err) => {
      console.error("SSE connection error:", err);
      setError("Lost connection to research status updates");
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [jobId]);

  // Download PDF
  const downloadPdf = async (pdfUrl: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}${pdfUrl}`);
      if (!response.ok) {
        throw new Error("Failed to download PDF");
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "research-report.pdf";
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to download PDF");
      throw err;
    }
  };

  return {
    isLoading,
    error,
    status,
    startResearch,
    downloadPdf,
  };
}
