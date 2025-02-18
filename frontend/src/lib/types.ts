// Request interface - matches the data structure sent to /research POST endpoint
export interface ResearchRequest {
  company: string;
  company_url?: string;
  industry?: string;
  hq_location?: string;
}

// Response from initial research request
export interface ResearchResponse {
  status: string;
  job_id: string;
  message: string;
  polling_url: string;
}

// Debug information structure for progress updates
export interface DebugInfo {
  timestamp: string;
  message: string;
}

// Research results structure when job is completed
export interface ResearchResult {
  results: string[];
  report: string;
  pdf_url: string;
  sections_completed: string[];
  total_references: number;
  completion_time: string;
}

// Status response from /research/status/<job_id> endpoint
export interface ResearchStatus {
  status: "pending" | "processing" | "completed" | "failed";
  progress: number;
  debug_info: DebugInfo[];
  last_update: string;
  result: ResearchResult | null;
  error: string | null;
}
