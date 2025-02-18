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
    console.log("[WebSocket] Connecting to:", wsUrl);

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log("[WebSocket] Connection established");
    };

    ws.onclose = (event) => {
      console.log("[WebSocket] Connection closed", {
        code: event.code,
        reason: event.reason,
        wasClean: event.wasClean,
      });
    };

    ws.onerror = (error) => {
      console.error("[WebSocket] Error occurred:", error);
    };

    ws.onmessage = (event) => {
      try {
        console.log("[WebSocket] Raw message received:", event.data);
        const data = JSON.parse(event.data);
        console.log("[WebSocket] Parsed message:", data);

        if (data.type === "status_update") {
          const update = data.data;
          console.log("[WebSocket] Processing status update:", update);

          setStatus((prevStatus) => {
            const newStatus = {
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
            };
            console.log("[WebSocket] Updated status:", newStatus);
            return newStatus;
          });

          setIsLoading(update.status === "processing");
          setError(update.error || null);

          if (update.status === "completed" || update.status === "failed") {
            console.log(
              "[WebSocket] Research completed/failed, closing connection"
            );
            ws.close();
          }
        } else if (data.type === "analyst_update") {
          const update = data.data;
          console.log("[WebSocket] Processing analyst update:", update);

          setStatus((prevStatus) => {
            if (!prevStatus) {
              console.log("[WebSocket] No previous status");
              return null;
            }

            const currentResult = prevStatus.result || {
              results: [],
              report: "",
              pdf_url: "",
              sections_completed: [],
              total_references: 0,
              completion_time: new Date().toISOString(),
              analyst_queries: {
                "Financial Analyst": [],
                "Industry Analyst": [],
                "Company Analyst": [],
                "News Scanner": [],
              },
            };

            const newStatus = {
              ...prevStatus,
              result: {
                ...currentResult,
                analyst_queries: {
                  ...currentResult.analyst_queries,
                  [update.analyst]: update.queries,
                },
              },
            };
            console.log(
              "[WebSocket] Updated status with analyst data:",
              newStatus
            );
            return newStatus;
          });
        }
      } catch (err) {
        console.error("[WebSocket] Error processing message:", err);
        console.error("[WebSocket] Problem message:", event.data);
      }
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
