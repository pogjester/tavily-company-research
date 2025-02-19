import { useResearchStore } from "../store/ResearchContext";
import { ResearchMessage } from "../lib/types";

export class ResearchStateHandler {
  constructor(private store: typeof useResearchStore) {}

  handleMessage(message: ResearchMessage) {
    // Update store with raw message
    this.store.getState().handleNodeUpdate(message);

    // Add node-specific logic
    switch (message.node) {
      case "grounding":
        this.handleGrounding(message);
        break;
      case "financial_analyst":
        this.handleFinancialAnalyst(message);
        break;
      // Add handlers for other nodes...
    }
  }

  private handleGrounding(message: ResearchMessage) {
    const { setNodeState } = this.store.getState();

    switch (message.type) {
      case "scraping_start":
        setNodeState("grounding", {
          status: "processing",
          progress: 0,
          data: { url: message.url },
        });
        break;

      case "scraping_progress":
        setNodeState("grounding", {
          progress: message.progress,
          data: { contentPreview: message.contentPreview },
        });
        break;
    }
  }

  private handleFinancialAnalyst(message: ResearchMessage) {
    const { setNodeState } = this.store.getState();

    switch (message.type) {
      case "query_generation":
        setNodeState("financial_analyst", {
          data: { queries: message.queries },
        });
        break;

      case "document_analysis":
        setNodeState("financial_analyst", {
          progress: message.documentsProcessed,
        });
        break;

      case "queries_generated":
        setNodeState("financial_analyst", {
          data: { financial_queries: message.queries },
        });
        break;
    }
  }

  // Add similar handlers for other nodes...
}
