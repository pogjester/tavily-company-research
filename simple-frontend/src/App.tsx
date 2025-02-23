import React, { useState, useEffect, useRef } from "react";
import {
  Building2,
  Globe,
  MapPin,
  Factory,
  Search,
  Loader2,
  CheckCircle2,
  Github,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import rehypeRaw from 'rehype-raw';

type ResearchStatus = {
  step: string;
  message: string;
};

type ResearchOutput = {
  summary: string;
  details: Record<string, any>;
};

// Add new types for query updates
type Query = {
  text: string;
  number: number;
  category: string;
};

// Add a new type for streaming queries
type StreamingQuery = {
  text: string;
  number: number;
  category: string;
  isComplete: boolean;
};

// Add to ResearchState type
type DocCount = {
  initial: number;
  kept: number;
};

type DocCounts = {
  company: DocCount;
  industry: DocCount;
  financial: DocCount;
  news: DocCount;
};

type BriefingStatus = {
  company: boolean;
  industry: boolean;
  financial: boolean;
  news: boolean;
};

// Add new types for enrichment
type EnrichmentCounts = {
  company: { total: number; enriched: number };
  industry: { total: number; enriched: number };
  financial: { total: number; enriched: number };
  news: { total: number; enriched: number };
};

type ResearchState = {
  status: string;
  message: string;
  queries: Query[];
  streamingQueries: Record<string, StreamingQuery>;
  docCounts?: DocCounts;
  enrichmentCounts?: EnrichmentCounts;
  briefingStatus: BriefingStatus;
};

console.log("=== DIRECT CONSOLE TEST ===");

const API_URL = import.meta.env.VITE_API_URL;
const WS_URL = import.meta.env.VITE_WS_URL;

if (!API_URL || !WS_URL) {
  throw new Error(
    "Environment variables VITE_API_URL and VITE_WS_URL must be set"
  );
}

// Log environment variables immediately
console.log({
  mode: import.meta.env.MODE,
  api_url: API_URL,
  ws_url: WS_URL,
});

// Add this near your other console.logs
console.log("Environment:", {
  VITE_API_URL: import.meta.env.VITE_API_URL,
  VITE_WS_URL: import.meta.env.VITE_WS_URL,
  MODE: import.meta.env.MODE,
  DEV: import.meta.env.DEV,
  PROD: import.meta.env.PROD,
});

// Add a window load event
window.addEventListener("load", () => {
  console.log("=== Window Loaded ===");
  console.log("API URL (on load):", import.meta.env.VITE_API_URL);
});

function App() {
  // Add useEffect for component mount logging
  useEffect(() => {
    console.log("=== Component Mounted ===");
    console.log("Form ready for submission");
  }, []);

  const [formData, setFormData] = useState({
    companyName: "",
    companyUrl: "",
    companyHq: "",
    companyIndustry: "",
  });
  const [isResearching, setIsResearching] = useState(false);
  const [status, setStatus] = useState<ResearchStatus | null>(null);
  const [output, setOutput] = useState<ResearchOutput | null>(null);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const [isComplete, setIsComplete] = useState(false);
  const [researchState, setResearchState] = useState<ResearchState>({
    status: "idle",
    message: "",
    queries: [],
    streamingQueries: {},
    briefingStatus: {
      company: false,
      industry: false,
      financial: false,
      news: false
    }
  });

  // Add ref for status section
  const statusRef = useRef<HTMLDivElement>(null);

  // Add scroll helper function
  const scrollToStatus = () => {
    statusRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const connectWebSocket = (jobId: string) => {
    console.log("Initializing WebSocket connection for job:", jobId);
    const ws = new WebSocket(`${WS_URL}/research/ws/${jobId}`);

    ws.onopen = () => {
      console.log("WebSocket connection established for job:", jobId);
    };

    ws.onmessage = (event) => {
      const rawData = JSON.parse(event.data);
      console.log("WebSocket message received:", rawData);

      if (rawData.type === "status_update") {
        const statusData = rawData.data;
        console.log("Status update received:", statusData);

        // Handle enrichment-specific updates
        if (statusData.result?.step === "Enriching") {
          console.log("Enrichment status update:", statusData);
          
          // Initialize enrichment counts when starting a category
          if (statusData.status === "category_start") {
            const category = statusData.result.category?.replace('_data', '') as keyof EnrichmentCounts;
            if (category) {
              setResearchState((prev) => ({
                ...prev,
                enrichmentCounts: {
                  ...prev.enrichmentCounts,
                  [category]: {
                    total: statusData.result.count || 0,
                    enriched: 0
                  }
                } as EnrichmentCounts
              }));
            }
          }
          // Update enriched count when a document is processed
          else if (statusData.status === "extracted") {
            const category = statusData.result.category?.replace('_data', '') as keyof EnrichmentCounts;
            if (category) {
              setResearchState((prev) => {
                const currentCounts = prev.enrichmentCounts?.[category];
                if (currentCounts) {
                  return {
                    ...prev,
                    enrichmentCounts: {
                      ...prev.enrichmentCounts,
                      [category]: {
                        ...currentCounts,
                        enriched: currentCounts.enriched + 1
                      }
                    } as EnrichmentCounts
                  };
                }
                return prev;
              });
            }
          }
          // Update final counts when a category is complete
          else if (statusData.status === "category_complete") {
            const category = statusData.result.category?.replace('_data', '') as keyof EnrichmentCounts;
            if (category) {
              setResearchState((prev) => ({
                ...prev,
                enrichmentCounts: {
                  ...prev.enrichmentCounts,
                  [category]: {
                    total: statusData.result.total || 0,
                    enriched: statusData.result.enriched || 0
                  }
                } as EnrichmentCounts
              }));
            }
          }
        }

        // Handle curation-specific updates
        if (statusData.result?.step === "Curation") {
          console.log("Curation status update:", {
            status: statusData.status,
            docCounts: statusData.result.doc_counts
          });
          
          // Initialize doc counts when curation starts
          if (statusData.status === "processing" && statusData.result.doc_counts) {
            setResearchState((prev) => ({
              ...prev,
              docCounts: statusData.result.doc_counts as DocCounts
            }));
          }
          // Update initial count for a category
          else if (statusData.status === "category_start") {
            const docType = statusData.result?.doc_type as keyof DocCounts;
            if (docType) {
              setResearchState((prev) => ({
                ...prev,
                docCounts: {
                  ...prev.docCounts,
                  [docType]: {
                    initial: statusData.result.initial_count,
                    kept: 0
                  } as DocCount
                } as DocCounts
              }));
            }
          }
          // Increment the kept count for a specific category
          else if (statusData.status === "document_kept") {
            const docType = statusData.result?.doc_type as keyof DocCounts;
            setResearchState((prev) => {
              if (docType && prev.docCounts?.[docType]) {
                return {
                  ...prev,
                  docCounts: {
                    ...prev.docCounts,
                    [docType]: {
                      initial: prev.docCounts[docType].initial,
                      kept: prev.docCounts[docType].kept + 1
                    }
                  } as DocCounts
                };
              }
              return prev;
            });
          }
          // Update final doc counts when curation is complete
          else if (statusData.status === "curation_complete" && statusData.result.doc_counts) {
            setResearchState((prev) => ({
              ...prev,
              docCounts: statusData.result.doc_counts as DocCounts
            }));
          }
        }

        // Handle briefing status updates
        if (statusData.status === "briefing_start") {
          setStatus({
            step: "Briefing",
            message: statusData.message
          });
        } else if (statusData.status === "briefing_complete" && statusData.result?.category) {
          const category = statusData.result.category;
          setResearchState((prev) => ({
            ...prev,
            briefingStatus: {
              ...prev.briefingStatus,
              [category]: true
            }
          }));
        }

        // Handle query updates
        if (statusData.status === "query_generating") {
          setResearchState((prev) => {
            const key = `${statusData.result.category}-${statusData.result.query_number}`;
            return {
              ...prev,
              streamingQueries: {
                ...prev.streamingQueries,
                [key]: {
                  text: statusData.result.query,
                  number: statusData.result.query_number,
                  category: statusData.result.category,
                  isComplete: false
                }
              }
            };
          });
        } else if (statusData.status === "query_generated") {
          setResearchState((prev) => {
            // Remove from streaming queries and add to completed queries
            const key = `${statusData.result.category}-${statusData.result.query_number}`;
            const { [key]: _, ...remainingStreamingQueries } = prev.streamingQueries;
            
            return {
              ...prev,
              streamingQueries: remainingStreamingQueries,
              queries: [
                ...prev.queries,
                {
                  text: statusData.result.query,
                  number: statusData.result.query_number,
                  category: statusData.result.category,
                },
              ],
            };
          });
        }
        // Handle report streaming
        else if (statusData.status === "report_chunk") {
          setOutput((prev) => ({
            summary: "Generating report...",
            details: {
              report: prev?.details?.report
                ? prev.details.report + statusData.result.chunk
                : statusData.result.chunk,
            },
          }));
        }
        // Handle other status updates
        else if (statusData.status === "processing") {
          setIsComplete(false);
          // Only update status.step if we're not in curation or the new step is curation
          if (!status?.step || status.step !== "Curation" || statusData.result?.step === "Curation") {
            setStatus({
              step: statusData.result?.step || "Processing",
              message: statusData.message || "Processing...",
            });
          }
          
          // Reset briefing status when starting a new research
          if (statusData.result?.step === "Briefing") {
            setResearchState((prev) => ({
              ...prev,
              briefingStatus: {
                company: false,
                industry: false,
                financial: false,
                news: false
              }
            }));
          }
          
          scrollToStatus();
        } else if (statusData.status === "completed") {
          setIsComplete(true);
          setIsResearching(false);
          setOutput({
            summary: "Research completed",
            details: {
              report: statusData.result.report,
            },
          });
        } else if (
          statusData.status === "failed" ||
          statusData.status === "error"
        ) {
          setError(statusData.error || "Research failed");
          setIsResearching(false);
          setIsComplete(false);
        }
      }
    };

    ws.onclose = (event) => {
      console.log("WebSocket disconnected", {
        jobId,
        code: event.code,
        reason: event.reason,
        wasClean: event.wasClean
      });
      if (isResearching) {
        setError("Research connection lost. Please try again.");
        setIsResearching(false);
      }
    };

    ws.onerror = (event) => {
      console.error("WebSocket error:", {
        jobId,
        error: event
      });
      setError("WebSocket connection error");
      setIsResearching(false);
    };

    wsRef.current = ws;
  };

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    console.log("Form submitted");
    setIsResearching(true);

    try {
      const url = `${API_URL}/research`;
      console.log("Attempting fetch to:", url);

      // Log the request details
      const requestData = {
        company: formData.companyName,
        company_url: formData.companyUrl || undefined,
        industry: formData.companyIndustry || undefined,
        hq_location: formData.companyHq || undefined,
      };
      console.log("Request data:", requestData);

      const response = await fetch(url, {
        method: "POST",
        mode: "cors",
        credentials: "omit",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestData),
      }).catch((error) => {
        console.error("Fetch error:", error);
        throw error;
      });

      console.log("Response received:", {
        status: response.status,
        ok: response.ok,
        statusText: response.statusText,
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.log("Error response:", errorText);
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log("Response data:", data);

      if (data.job_id) {
        console.log("Connecting WebSocket with job_id:", data.job_id);
        connectWebSocket(data.job_id);
      } else {
        throw new Error("No job ID received");
      }
    } catch (err) {
      console.log("Caught error:", err);
      setError(err instanceof Error ? err.message : "Failed to start research");
      setIsResearching(false);
    }
  };

  // Add document count display component
  const DocumentStats = ({ docCounts }: { docCounts: Record<string, DocCount> }) => {
    if (!docCounts) return null;

    return (
      <div className="glass rounded-xl shadow-lg p-6 mt-4">
        <h2 className="text-lg font-semibold text-white mb-4">Document Curation Stats</h2>
        <div className="grid grid-cols-4 gap-4">
          {Object.entries(docCounts).map(([category, counts]: [string, DocCount]) => (
            <div key={category} className="text-center">
              <h3 className="text-sm font-medium text-gray-400 mb-2 capitalize">{category}</h3>
              <div className="text-white">
                <div className="text-2xl font-bold">{counts.kept}</div>
                <div className="text-sm text-gray-400">kept from {counts.initial}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  // Add BriefingProgress component
  const BriefingProgress = () => {
    const categories = [
      { key: 'company' as keyof BriefingStatus, icon: '🏢', label: 'Company Analysis' },
      { key: 'industry' as keyof BriefingStatus, icon: '🏭', label: 'Industry Analysis' },
      { key: 'financial' as keyof BriefingStatus, icon: '💰', label: 'Financial Analysis' },
      { key: 'news' as keyof BriefingStatus, icon: '📰', label: 'News Analysis' }
    ] as const;

    return (
      <div className="glass rounded-xl shadow-lg p-6 mt-4">
        <h2 className="text-lg font-semibold text-white mb-4">Research Briefings</h2>
        <div className="grid grid-cols-4 gap-4">
          {categories.map(({ key, icon, label }) => (
            <div key={key} className="text-center">
              <div className="flex items-center justify-center mb-2">
                <span className="mr-2">{icon}</span>
                <h3 className="text-sm font-medium text-gray-400">{label}</h3>
              </div>
              <div className="text-white">
                {researchState.briefingStatus[key] ? (
                  <div className="flex items-center justify-center text-green-400">
                    <CheckCircle2 className="h-6 w-6" />
                  </div>
                ) : (
                  <div className="flex items-center justify-center text-blue-400">
                    <Loader2 className="animate-spin h-6 w-6" />
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  // Add EnrichmentProgress component
  const EnrichmentProgress = () => {
    const categories = [
      { key: 'company', icon: '🏢', label: 'Company Documents' },
      { key: 'industry', icon: '🏭', label: 'Industry Documents' },
      { key: 'financial', icon: '💰', label: 'Financial Documents' },
      { key: 'news', icon: '📰', label: 'News Documents' }
    ] as const;

    return (
      <div className="glass rounded-xl shadow-lg p-6 mt-4">
        <h2 className="text-lg font-semibold text-white mb-4">Content Enrichment Progress</h2>
        <div className="grid grid-cols-4 gap-4">
          {categories.map(({ key, icon, label }) => {
            const counts = researchState.enrichmentCounts?.[key as keyof EnrichmentCounts];
            return (
              <div key={key} className="text-center">
                <div className="flex items-center justify-center mb-2">
                  <span className="mr-2">{icon}</span>
                  <h3 className="text-sm font-medium text-gray-400">{label}</h3>
                </div>
                <div className="text-white">
                  <div className="text-2xl font-bold">
                    {counts ? (
                      <span className="text-blue-400">{counts.enriched}</span>
                    ) : (
                      <Loader2 className="animate-spin h-6 w-6 mx-auto text-blue-400" />
                    )}
                  </div>
                  <div className="text-sm text-gray-400">
                    {counts ? (
                      `enriched from ${counts.total}`
                    ) : (
                      "waiting..."
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  // Add these styles at the top of the component, before the return statement
  const glassStyle = "backdrop-filter backdrop-blur-lg bg-white/5 border border-white/10 shadow-xl";
  const glassCardStyle = `${glassStyle} rounded-2xl p-6`;
  const glassInputStyle = `${glassStyle} pl-10 w-full rounded-lg py-3 px-4 text-white shadow-sm focus:border-blue-500/50 focus:outline-none focus:ring-1 focus:ring-blue-500/50 placeholder-gray-400 bg-white/5`;
  const glassButtonStyle = "w-full mt-6 inline-flex items-center justify-center rounded-lg bg-gradient-to-r from-blue-600 to-blue-500 px-6 py-3 text-sm font-semibold text-white shadow-lg hover:from-blue-500 hover:to-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:ring-offset-2 focus:ring-offset-gray-900 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 backdrop-blur-sm";

  return (
    <div className="min-h-screen bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-gray-900 via-[#0f1c3f] to-gray-900 p-8">
      <div className="max-w-5xl mx-auto space-y-8">
        {/* Header with GitHub Link */}
        <div className="relative mb-12">
          <div className="text-center">
            <h1 className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-blue-200 mb-3">
              Tavily Company Researcher
            </h1>
            <p className="text-gray-400 text-lg">
              Enter company details to begin research
            </p>
          </div>
          <a
            href="https://github.com/pogjester"
            target="_blank"
            rel="noopener noreferrer"
            className={`absolute top-0 right-0 text-gray-400 hover:text-white transition-colors ${glassStyle} p-2 rounded-lg`}
            aria-label="GitHub Profile"
          >
            <Github className="h-6 w-6" />
          </a>
        </div>

        {/* Form */}
        <form
          onSubmit={handleSubmit}
          className={`${glassCardStyle} space-y-6`}
        >
          <div className="space-y-6">
            {/* Company Name */}
            <div className="relative">
              <label
                htmlFor="companyName"
                className="block text-sm font-medium text-gray-300 mb-2"
              >
                Company Name *
              </label>
              <div className="relative">
                <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                <input
                  required
                  id="companyName"
                  type="text"
                  value={formData.companyName}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      companyName: e.target.value,
                    }))
                  }
                  className={glassInputStyle}
                  placeholder="Enter company name"
                />
              </div>
            </div>

            {/* Company URL */}
            <div>
              <label
                htmlFor="companyUrl"
                className="block text-sm font-medium text-gray-300 mb-2"
              >
                Company URL
              </label>
              <div className="relative">
                <Globe className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                <input
                  id="companyUrl"
                  type="url"
                  value={formData.companyUrl}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      companyUrl: e.target.value,
                    }))
                  }
                  className={glassInputStyle}
                  placeholder="https://example.com"
                />
              </div>
            </div>

            {/* Company HQ */}
            <div>
              <label
                htmlFor="companyHq"
                className="block text-sm font-medium text-gray-300 mb-2"
              >
                Company HQ
              </label>
              <div className="relative">
                <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                <input
                  id="companyHq"
                  type="text"
                  value={formData.companyHq}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      companyHq: e.target.value,
                    }))
                  }
                  className={glassInputStyle}
                  placeholder="City, Country"
                />
              </div>
            </div>

            {/* Company Industry */}
            <div>
              <label
                htmlFor="companyIndustry"
                className="block text-sm font-medium text-gray-300 mb-2"
              >
                Company Industry
              </label>
              <div className="relative">
                <Factory className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                <input
                  id="companyIndustry"
                  type="text"
                  value={formData.companyIndustry}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      companyIndustry: e.target.value,
                    }))
                  }
                  className={glassInputStyle}
                  placeholder="e.g. Technology, Healthcare"
                />
              </div>
            </div>
          </div>

          <button
            type="submit"
            disabled={isResearching || !formData.companyName}
            className={glassButtonStyle}
          >
            {isResearching ? (
              <>
                <Loader2 className="animate-spin -ml-1 mr-2 h-5 w-5" />
                Researching...
              </>
            ) : (
              <>
                <Search className="-ml-1 mr-2 h-5 w-5" />
                Start Research
              </>
            )}
          </button>
        </form>

        {/* Error Message */}
        {error && (
          <div className={`${glassCardStyle} border-red-500/30 bg-red-900/20`}>
            <p className="text-red-300">{error}</p>
          </div>
        )}

        {/* Status Box */}
        {status && (
          <div ref={statusRef} className={glassCardStyle}>
            <h2 className="text-xl font-semibold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-blue-200 mb-6">
              Research Status
            </h2>
            <div className="space-y-4">
              <div className="flex items-center space-x-4">
                <div className="flex-shrink-0">
                  {isComplete ? (
                    <div className={`${glassStyle} p-2 rounded-full`}>
                      <CheckCircle2 className="h-6 w-6 text-green-400" />
                    </div>
                  ) : (
                    <div className={`${glassStyle} p-2 rounded-full`}>
                      <Loader2 className="animate-spin h-6 w-6 text-blue-400" />
                    </div>
                  )}
                </div>
                <div className="flex-1">
                  <p className="font-medium text-white">{status.step}</p>
                  <p className="text-sm text-gray-400 whitespace-pre-wrap">
                    {status.message}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Progress Components - Update their styling */}
        {isResearching && status?.step === "Briefing" && (
          <div className={glassCardStyle}>
            <h2 className="text-xl font-semibold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-blue-200 mb-4">
              Research Briefings
            </h2>
            <div className="grid grid-cols-4 gap-4">
              {['company', 'industry', 'financial', 'news'].map((category) => (
                <div key={category} className={`${glassStyle} rounded-xl p-3`}>
                  <h3 className="text-sm font-medium text-gray-400 mb-2 capitalize">{category}</h3>
                  <div className="text-white">
                    {researchState.briefingStatus[category as keyof BriefingStatus] ? (
                      <div className="flex items-center justify-center text-green-400">
                        <CheckCircle2 className="h-6 w-6" />
                      </div>
                    ) : (
                      <div className="flex items-center justify-center text-blue-400">
                        <Loader2 className="animate-spin h-6 w-6" />
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Document Curation Stats */}
        {isResearching && status?.step === "Curation" && researchState.docCounts && (
          <div className={glassCardStyle}>
            <h2 className="text-xl font-semibold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-blue-200 mb-4">
              Document Curation Progress
            </h2>
            <div className="grid grid-cols-4 gap-4">
              {['company', 'industry', 'financial', 'news'].map((category) => {
                const counts = researchState.docCounts?.[category as keyof typeof researchState.docCounts];
                return (
                  <div key={category} className={`${glassStyle} rounded-xl p-3`}>
                    <h3 className="text-sm font-medium text-gray-400 mb-2 capitalize">{category}</h3>
                    <div className="text-white">
                      <div className="text-2xl font-bold mb-1">
                        {counts ? (
                          <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-blue-300">
                            {counts.kept}
                          </span>
                        ) : (
                          <Loader2 className="animate-spin h-6 w-6 mx-auto text-blue-400" />
                        )}
                      </div>
                      <div className="text-sm text-gray-400">
                        {counts ? (
                          `kept from ${counts.initial}`
                        ) : (
                          "waiting..."
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Enrichment Progress */}
        {isResearching && status?.step === "Enriching" && (
          <div className={glassCardStyle}>
            <h2 className="text-xl font-semibold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-blue-200 mb-4">
              Content Enrichment Progress
            </h2>
            <div className="grid grid-cols-4 gap-4">
              {['company', 'industry', 'financial', 'news'].map((category) => {
                const counts = researchState.enrichmentCounts?.[category as keyof EnrichmentCounts];
                return (
                  <div key={category} className={`${glassStyle} rounded-xl p-3`}>
                    <h3 className="text-sm font-medium text-gray-400 mb-2 capitalize">{category}</h3>
                    <div className="text-white">
                      <div className="text-2xl font-bold mb-1">
                        {counts ? (
                          <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-blue-300">
                            {counts.enriched}
                          </span>
                        ) : (
                          <Loader2 className="animate-spin h-6 w-6 mx-auto text-blue-400" />
                        )}
                      </div>
                      <div className="text-sm text-gray-400">
                        {counts ? (
                          `enriched from ${counts.total}`
                        ) : (
                          "waiting..."
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Query Display Section */}
        {researchState.queries.length > 0 && (
          <div className={glassCardStyle}>
            <h2 className="text-xl font-semibold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-blue-200 mb-4">
              Generated Research Queries
            </h2>
            <div className="grid grid-cols-2 gap-4">
              {['company', 'industry', 'financial', 'news'].map((category) => (
                <div key={category} className={`${glassStyle} rounded-xl p-3`}>
                  <h3 className="text-sm font-medium text-gray-400 flex items-center mb-3">
                    <span className="mr-2">{
                      category === 'company' ? '🏢' :
                      category === 'industry' ? '🏭' :
                      category === 'financial' ? '💰' : '📰'
                    }</span>
                    {category.charAt(0).toUpperCase() + category.slice(1)} Analysis
                  </h3>
                  <div className="space-y-2">
                    {researchState.queries
                      .filter((q) => q.category === `${category}_analyzer`)
                      .map((query, idx) => (
                        <div key={idx} className={`${glassStyle} rounded-lg p-2`}>
                          <span className="text-gray-300">{query.text}</span>
                        </div>
                      ))}
                    {Object.entries(researchState.streamingQueries)
                      .filter(([key]) => key.startsWith(`${category}_analyzer`))
                      .map(([key, query]) => (
                        <div key={key} className={`${glassStyle} rounded-lg p-2`}>
                          <span className="text-gray-300">{query.text}</span>
                          <span className="animate-pulse ml-1 text-blue-400">|</span>
                        </div>
                      ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Output Box */}
        {output && output.details && (
          <div className={glassCardStyle}>
            <h2 className="text-xl font-semibold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-blue-200 mb-4">
              Research Results
            </h2>
            <div className="prose prose-invert prose-lg max-w-none">
              <p className="text-gray-300">{output.summary}</p>
              <div className={`mt-4 ${glassStyle} rounded-xl p-4 overflow-x-auto`}>
                <ReactMarkdown
                  rehypePlugins={[rehypeRaw]}
                  components={{
                    div: ({node, ...props}) => (
                      <div className="space-y-4 text-gray-200" {...props} />
                    ),
                    h1: ({node, ...props}) => (
                      <h1 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-blue-200 mt-8 mb-4" {...props} />
                    ),
                    h2: ({node, ...props}) => (
                      <h2 className="text-xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-blue-200 mt-6 mb-3" {...props} />
                    ),
                    h3: ({node, ...props}) => (
                      <h3 className="text-lg font-semibold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-blue-200 mt-4 mb-2" {...props} />
                    ),
                    p: ({node, ...props}) => (
                      <p className="text-gray-200 my-2" {...props} />
                    ),
                    ul: ({node, ...props}) => (
                      <ul className="text-gray-200 space-y-1 list-disc pl-6" {...props} />
                    ),
                    li: ({node, ...props}) => (
                      <li className="text-gray-200" {...props} />
                    ),
                    a: ({node, ...props}) => (
                      <a className="text-blue-400 hover:text-blue-300 transition-colors" {...props} />
                    ),
                  }}
                >
                  {output.details.report || "No report available"}
                </ReactMarkdown>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
