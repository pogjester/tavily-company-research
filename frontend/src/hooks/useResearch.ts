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

  // Poll status
  const pollStatus = useCallback(async (id: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/research/status/${id}`);
      if (!response.ok) {
        throw new Error("Failed to fetch status");
      }
      const result: ResearchStatus = await response.json();
      setStatus(result);
      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
      throw err;
    }
  }, []);

  // Auto-polling effect
  useEffect(() => {
    let intervalId: ReturnType<typeof setInterval>;

    if (jobId) {
      // Initial poll
      pollStatus(jobId);

      // Set up polling interval
      intervalId = setInterval(async () => {
        try {
          const result = await pollStatus(jobId);
          // Stop polling if research is complete or failed
          if (result.status === "completed" || result.status === "failed") {
            clearInterval(intervalId);
          }
        } catch (err) {
          clearInterval(intervalId);
        }
      }, 2000); // Poll every 2 seconds
    }

    // Cleanup
    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [jobId, pollStatus]);

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
