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

  // Set up WebSocket connection when jobId changes
  useEffect(() => {
    if (!jobId) return;

    // Convert http(s) to ws(s) and construct WebSocket URL
    const wsProtocol = API_BASE_URL.startsWith("https") ? "wss" : "ws";
    const wsUrl = `${wsProtocol}://${API_BASE_URL.replace(
      /^https?:\/\//,
      ""
    )}/research/ws/${jobId}`;
    console.log("Connecting to WebSocket:", wsUrl);

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log("WebSocket connection established");
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === "status_update") {
          const update = data.data;

          // Update status based on the WebSocket data
          setStatus((prevStatus) => ({
            status: update.status,
            progress: update.progress,
            debug_info: [
              ...(prevStatus?.debug_info || []),
              ...(update.message
                ? [{ timestamp: data.timestamp, message: update.message }]
                : []),
            ],
            last_update: data.timestamp,
            result: update.result,
            error: update.error,
          }));

          // Update loading state
          setIsLoading(update.status === "processing");

          // Update error state
          setError(update.error || null);

          // Close connection if research is complete or failed
          if (update.status === "completed" || update.status === "failed") {
            ws.close();
          }
        }
      } catch (err) {
        console.error("Error parsing WebSocket data:", err);
      }
    };

    ws.onerror = (err) => {
      console.error("WebSocket error:", err);
      setError("Lost connection to research status updates");
    };

    ws.onclose = () => {
      console.log("WebSocket connection closed");
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
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
