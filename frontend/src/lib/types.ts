// Base WebSocket message structure
export interface WebSocketMessage {
  type: string;
  timestamp: string;
  [key: string]: unknown;
}

export interface ApiError {
  detail: string;
  code?: number;
  context?: Record<string, unknown>;
}

// Phase and type definitions

export type GroundingUpdateSubtype =
  | "site_scrape_start"
  | "site_scrape_progress"
  | "site_scrape_complete"
  | "site_scrape_error"
  | "site_scrape_skip"
  | "grounding_complete"
  | "research_start";

export type ResearchPhase =
  | "idle"
  | "initializing"
  | "grounding"
  | "researching"
  | "analyzing"
  | "generating"
  | "completed"
  | "error";

export type ResearchNode =
  | "grounding"
  | "financial_analyst"
  | "industry_analyst"
  | "company_analyst"
  | "news_scanner"
  | "collector"
  | "curator"
  | "enricher"
  | "briefing"
  | "editor"
  | "output";

export type NodeStatus =
  | "idle"
  | "processing"
  | "completed"
  | "error"
  | "skipped";

export type ResearchMessage = {
  timestamp: string;
  node: ResearchNode;
} & ( // Grounding Node Messages
  | { type: "scraping_start"; url: string }
  | { type: "scraping_progress"; progress: number; contentPreview: string }
  | { type: "scraping_complete"; contentLength: number }
  | { type: "scraping_error"; error: string }

  // Financial Analyst Messages
  | { type: "query_generation"; queries: string[] }
  | { type: "document_analysis"; documentsProcessed: number }

  // Industry Analyst Messages
  | { type: "market_research"; insights: string[] }

  // Collector Node Messages
  | { type: "data_collection"; totalSources: number }

  // Curator Node Messages
  | { type: "data_filtering"; relevantSources: number }

  // Common Messages
  | { type: "node_start" }
  | { type: "node_complete"; result: any }
  | { type: "node_error"; error: string }
  | { type: "node_progress"; progress: number }
);
