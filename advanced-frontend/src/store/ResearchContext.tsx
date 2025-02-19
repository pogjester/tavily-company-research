import React, { createContext, useReducer, useContext, ReactNode } from "react";
import { ResearchNode, NodeStatus, ResearchMessage } from "../lib/types";

type NodeState = {
  status: NodeStatus;
  data?: any;
  error?: string;
  lastUpdated: string;
};

type ResearchState = {
  nodes: Record<ResearchNode, NodeState>;
  globalStatus: "idle" | "running" | "paused" | "completed" | "error";
  timeline: ResearchMessage[];
  errors: Array<{ message: string; timestamp: string }>;
};

type ResearchAction =
  | { type: "HANDLE_NODE_UPDATE"; message: ResearchMessage }
  | { type: "RESET_RESEARCH" }
  | { type: "PAUSE_RESEARCH" };

const initialNodeState: NodeState = {
  status: "idle",
  lastUpdated: new Date().toISOString(),
};

const initialState: ResearchState = {
  nodes: {
    grounding: initialNodeState,
    financial_analyst: initialNodeState,
    industry_analyst: initialNodeState,
    company_analyst: initialNodeState,
    news_scanner: initialNodeState,
    collector: initialNodeState,
    curator: initialNodeState,
    enricher: initialNodeState,
    briefing: initialNodeState,
    editor: initialNodeState,
    output: initialNodeState,
  },
  globalStatus: "idle",
  timeline: [],
  errors: [],
};

const ResearchContext = createContext<{
  state: ResearchState;
  dispatch: React.Dispatch<ResearchAction>;
}>({ state: initialState, dispatch: () => null });

const researchReducer = (
  state: ResearchState,
  action: ResearchAction
): ResearchState => {
  switch (action.type) {
    case "HANDLE_NODE_UPDATE": {
      const { message } = action;
      const newState = { ...state };
      newState.timeline.push(message);

      const nodeState = newState.nodes[message.node];
      nodeState.lastUpdated = message.timestamp;

      switch (message.type) {
        case "node_start":
          nodeState.status = "processing";
          break;
        case "node_complete":
          nodeState.status = "completed";
          nodeState.data = message.result;
          break;
        case "node_error":
          nodeState.status = "error";
          nodeState.error = message.error;
          newState.errors.push({
            message: `${message.node} error: ${message.error}`,
            timestamp: message.timestamp,
          });
          newState.globalStatus = "error";
          break;
        case "scraping_start":
          newState.nodes.grounding.data = {
            url: message.url,
            content: "",
          };
          break;
        case "scraping_progress":
          newState.nodes.grounding.data.content += message.contentPreview;
          break;
        case "query_generation":
          newState.nodes.financial_analyst.data = {
            queries: message.queries,
          };
          break;
        case "queries_generated":
          // Save subqueries for the node; for financial, we use "financial_queries"
          if (message.node === "financial_analyst") {
            newState.nodes.financial_analyst.data = {
              ...newState.nodes.financial_analyst.data,
              financial_queries: message.queries,
            };
          }
          // (Add similar logic for other nodes if needed)
          break;
        case "market_research":
          newState.nodes.industry_analyst.data = {
            insights: message.insights,
          };
          break;
      }

      if (newState.globalStatus === "idle" && message.type === "node_start") {
        newState.globalStatus = "running";
      }

      return newState;
    }
    case "RESET_RESEARCH":
      return initialState;
    case "PAUSE_RESEARCH":
      return { ...state, globalStatus: "paused" };
    default:
      return state;
  }
};

export const ResearchProvider = ({ children }: { children: ReactNode }) => {
  const [state, dispatch] = useReducer(researchReducer, initialState);
  return (
    <ResearchContext.Provider value={{ state, dispatch }}>
      {children}
    </ResearchContext.Provider>
  );
};

export const useResearchStore = () => useContext(ResearchContext);
