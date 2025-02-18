// hooks/useResearch.ts
import { useResearchStore } from "../store/ResearchContext";
import { WebSocketService } from "../services/websocketService";
import { ResearchStateHandler } from "./stateHandler";
import { useRef, useEffect, useState } from "react";
import axios from "axios"; // Add axios for HTTP requests

// Create API service instance
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  headers: {
    "Content-Type": "application/json",
  },
});

type ResearchParams = {
  company: string;
  company_url?: string;
  industry?: string;
  hq_location?: string;
};

export const useResearch = () => {
  const { dispatch } = useResearchStore();
  const handlerRef = useRef<ResearchStateHandler>();
  const wsServiceRef = useRef<WebSocketService>();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  const startResearch = async (params: ResearchParams) => {
    setIsLoading(true);
    setError(null);
    try {
      dispatch({ type: "RESET_RESEARCH" });

      // Start research job using axios
      const response = await api.post<{ job_id: string }>("/research", params);

      const jobId = response.data.job_id;

      // Initialize WebSocket connection
      const wsUrl = `${
        import.meta.env.VITE_WS_URL || "ws://localhost:8000"
      }/research/ws/${jobId}`;

      handlerRef.current = new ResearchStateHandler(useResearchStore);

      wsServiceRef.current = new WebSocketService(wsUrl, {
        onMessage: (msg) => handlerRef.current?.handleMessage(msg),
        onError: (error) => {
          const errorMessage = error.message || "Failed to start research";
          setError(errorMessage);
          dispatch({
            type: "HANDLE_NODE_UPDATE",
            message: {
              type: "node_error",
              node: "grounding",
              timestamp: new Date().toISOString(),
              error: errorMessage,
            },
          });
        },
        onStatusChange: (status) => setStatus(status),
      });

      wsServiceRef.current.connect();
      setStatus("Research started successfully");
    } catch (error) {
      const errorMessage = "Failed to start research";
      setError(errorMessage);
      dispatch({
        type: "HANDLE_NODE_UPDATE",
        message: {
          type: "node_error",
          node: "grounding",
          timestamp: new Date().toISOString(),
          error: errorMessage,
        },
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    return () => {
      wsServiceRef.current?.disconnect();
    };
  }, []);

  return {
    startResearch,
    isLoading,
    error,
    status,
  };
};
