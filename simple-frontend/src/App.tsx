import React, { useState, useEffect, useRef } from "react";
import {
  Building2,
  Globe,
  MapPin,
  Factory,
  Search,
  Loader2,
  CheckCircle2,
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

type ResearchState = {
  status: string;
  message: string;
  queries: Query[];
  streamingQueries: Record<string, StreamingQuery>;  // Track queries being typed
  // ... other existing state properties
  docCounts?: {
    company: DocCount;
    industry: DocCount;
    financial: DocCount;
    news: DocCount;
  };
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
    // ... other state
  });

  // Add ref for status section
  const statusRef = useRef<HTMLDivElement>(null);

  // Add scroll helper function
  const scrollToStatus = () => {
    statusRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const connectWebSocket = (jobId: string) => {
    const ws = new WebSocket(`${WS_URL}/research/ws/${jobId}`);

    ws.onopen = () => {
      console.log("WebSocket connected");
    };

    ws.onmessage = (event) => {
      const rawData = JSON.parse(event.data);
      console.log("WebSocket message received:", rawData);

      if (rawData.type === "status_update") {
        const statusData = rawData.data;

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
          setStatus({
            step: statusData.result?.step || "Processing",
            message: statusData.message || "Processing...",
          });
          scrollToStatus(); // Add scroll on status update
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
        } else if (statusData.status === "curation_complete") {
          setResearchState((prev) => ({
            ...prev,
            docCounts: statusData.result.doc_counts
          }));
        }
      }
    };

    ws.onerror = (event) => {
      console.error("WebSocket error:", event);
      setError("WebSocket connection error");
      setIsResearching(false);
    };

    ws.onclose = (event) => {
      console.log("WebSocket disconnected", event);
      if (isResearching) {
        setError("Research connection lost. Please try again.");
        setIsResearching(false);
      }
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 p-6">
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-3xl font-bold text-white mb-2">
            Company Researcher
          </h1>
          <p className="text-gray-400">
            Enter company details to begin research
          </p>
        </div>

        {/* Form */}
        <form
          onSubmit={handleSubmit}
          className="glass rounded-xl shadow-lg p-6 space-y-4"
        >
          <div className="space-y-4">
            {/* Company Name */}
            <div className="relative">
              <label
                htmlFor="companyName"
                className="block text-sm font-medium text-gray-300 mb-1"
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
                  className="pl-10 w-full rounded-lg bg-gray-800/50 border border-gray-700 text-white py-2 px-3 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 placeholder-gray-500"
                  placeholder="Enter company name"
                />
              </div>
            </div>

            {/* Company URL */}
            <div>
              <label
                htmlFor="companyUrl"
                className="block text-sm font-medium text-gray-300 mb-1"
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
                  className="pl-10 w-full rounded-lg bg-gray-800/50 border border-gray-700 text-white py-2 px-3 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 placeholder-gray-500"
                  placeholder="https://example.com"
                />
              </div>
            </div>

            {/* Company HQ */}
            <div>
              <label
                htmlFor="companyHq"
                className="block text-sm font-medium text-gray-300 mb-1"
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
                  className="pl-10 w-full rounded-lg bg-gray-800/50 border border-gray-700 text-white py-2 px-3 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 placeholder-gray-500"
                  placeholder="City, Country"
                />
              </div>
            </div>

            {/* Company Industry */}
            <div>
              <label
                htmlFor="companyIndustry"
                className="block text-sm font-medium text-gray-300 mb-1"
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
                  className="pl-10 w-full rounded-lg bg-gray-800/50 border border-gray-700 text-white py-2 px-3 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 placeholder-gray-500"
                  placeholder="e.g. Technology, Healthcare"
                />
              </div>
            </div>
          </div>

          <button
            type="submit"
            disabled={isResearching || !formData.companyName}
            className="w-full mt-6 inline-flex items-center justify-center rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-900 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
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
          <div className="glass rounded-xl shadow-lg p-6 bg-red-900/50 border border-red-700">
            <p className="text-red-300">{error}</p>
          </div>
        )}

        {/* Status Box */}
        {status && (
          <div ref={statusRef} className="glass rounded-xl shadow-lg p-6">
            <h2 className="text-lg font-semibold text-white mb-4">
              Research Status
            </h2>
            <div className="space-y-4">
              <div className="flex items-center space-x-3">
                <div className="flex-shrink-0">
                  {isComplete ? (
                    <CheckCircle2 className="h-5 w-5 text-green-400" />
                  ) : (
                    <Loader2 className="animate-spin h-5 w-5 text-blue-400" />
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

        {/* Output Box */}
        {output && (
          <div className="glass rounded-xl shadow-lg p-6">
            <h2 className="text-lg font-semibold text-white mb-4">
              Research Results
            </h2>
            <div className="prose prose-invert prose-lg max-w-none">
              <p className="text-gray-300">{output.summary}</p>
              <div className="mt-4 bg-gray-800/50 p-6 rounded-lg overflow-x-auto border border-gray-700">
                <ReactMarkdown
                  rehypePlugins={[rehypeRaw]}
                  components={{
                    // Main container with consistent spacing
                    div: ({node, ...props}) => (
                      <div className="space-y-6" {...props} />
                    ),
                    // Main title (h1)
                    h1: ({node, ...props}) => (
                      <h1 className="text-3xl font-bold text-white mt-10 mb-6" {...props} />
                    ),
                    // Main sections (##)
                    h2: ({node, ...props}) => (
                      <h2 className="text-2xl font-bold text-white mt-8 mb-4" {...props} />
                    ),
                    // Subsections (###)
                    h3: ({node, ...props}) => (
                      <h3 className="text-xl font-semibold text-white mt-6 mb-3" {...props} />
                    ),
                    // Regular lists
                    ul: ({node, ...props}: {node?: any, children?: React.ReactNode}) => (
                      <ul className="space-y-2 my-4">{props.children}</ul>
                    ),
                    // Regular list items
                    li: ({node, children}: {node?: any, children?: React.ReactNode}) => (
                      <li className="ml-6 text-gray-300 relative before:absolute before:content-['•'] before:text-gray-500 before:left-[-1.25em] before:top-[0.125em]">
                        <div className="inline-block pl-4">{children}</div>
                      </li>
                    ),
                    // Paragraphs that might contain subsections and bullet points
                    p: ({node, children}: {node?: any, children?: React.ReactNode}) => {
                      if (typeof children === 'string') {
                        // Check if this is a bullet point list (even without newlines)
                        if (children.trim().startsWith('•') || children.trim().startsWith('*')) {
                          const bulletPoints = children
                            .split('\n')
                            .filter(line => line.trim())
                            .map(line => line.replace(/^[•\*]\s*/, '').trim());

                          return (
                            <ul className="space-y-2 my-4">
                              {bulletPoints.map((point, i) => (
                                <li key={i} className="ml-6 text-gray-300 relative before:absolute before:content-['•'] before:text-gray-500 before:left-[-1.25em] before:top-[0.125em]">
                                  <div className="inline-block pl-4">{point}</div>
                                </li>
                              ))}
                            </ul>
                          );
                        }

                        // Split content by double newlines to separate sections
                        const sections = children.split('\n\n');
                        
                        return (
                          <div className="space-y-6">
                            {sections.map((section, idx) => {
                              // Check if this is a subsection with bold header
                              const headerMatch = section.match(/^\*\*(.*?)\*\*\n/);
                              
                              if (headerMatch) {
                                const [fullMatch, headerText] = headerMatch;
                                const bulletPoints = section
                                  .slice(fullMatch.length)
                                  .split('\n')
                                  .filter(line => line.trim())
                                  .map(line => line.replace(/^[•\*]\s*/, '').trim());

                                return (
                                  <div key={idx} className="space-y-3">
                                    <h3 className="text-xl font-semibold text-white">{headerText}</h3>
                                    <ul className="space-y-2">
                                      {bulletPoints.map((point, i) => (
                                        <li key={i} className="ml-6 text-gray-300 relative before:absolute before:content-['•'] before:text-gray-500 before:left-[-1.25em] before:top-[0.125em]">
                                          <div className="inline-block pl-4">{point}</div>
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                );
                              }

                              // Check if this section is a bullet point list
                              if (section.trim().startsWith('•') || section.trim().startsWith('*')) {
                                const bulletPoints = section
                                  .split('\n')
                                  .filter(line => line.trim())
                                  .map(line => line.replace(/^[•\*]\s*/, '').trim());

                                return (
                                  <ul key={idx} className="space-y-2 my-4">
                                    {bulletPoints.map((point, i) => (
                                      <li key={i} className="ml-6 text-gray-300 relative before:absolute before:content-['•'] before:text-gray-500 before:left-[-1.25em] before:top-[0.125em]">
                                        <div className="inline-block pl-4">{point}</div>
                                      </li>
                                    ))}
                                  </ul>
                                );
                              }

                              // Regular paragraph
                              return (
                                <p key={idx} className="text-gray-300 leading-relaxed">
                                  {section}
                                </p>
                              );
                            })}
                          </div>
                        );
                      }
                      
                      return <p className="text-gray-300 leading-relaxed">{children}</p>;
                    },
                    // Other text elements
                    text: ({children}: {children?: React.ReactNode}) => (
                      <span className="text-gray-300">{children}</span>
                    ),
                    strong: ({node, ...props}) => (
                      <strong className="text-gray-300 font-semibold" {...props} />
                    ),
                    // Links
                    a: ({node, href, ...props}) => (
                      <a 
                        href={href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-400 hover:text-blue-300 transition-colors"
                        {...props}
                      />
                    )
                  }}
                >
                  {output.details.report || "No report available"}
                </ReactMarkdown>
              </div>
            </div>
          </div>
        )}

        {/* Query Display Section */}
        {researchState.queries.length > 0 && (
          <div className="glass rounded-xl shadow-lg p-6">
            <h2 className="text-lg font-semibold text-white mb-4">
              Generated Research Queries
            </h2>
            <div className="grid grid-cols-2 gap-6">
              {/* Company Analysis */}
              <div className="space-y-2">
                <h3 className="text-sm font-medium text-gray-400 flex items-center">
                  <span className="mr-2">🏢</span>
                  Company Analysis
                </h3>
                {researchState.queries
                  .filter((q) => q.category === "company_analyzer")
                  .map((query, idx) => (
                    <div key={idx} className="p-3 bg-gray-800/50 rounded-lg border border-gray-700 text-sm">
                      <span className="text-gray-400">{query.text}</span>
                    </div>
                  ))}
                {Object.entries(researchState.streamingQueries)
                  .filter(([key]) => key.startsWith("company_analyzer"))
                  .map(([key, query]) => (
                    <div key={key} className="p-3 bg-gray-800/50 rounded-lg border border-gray-700 text-sm">
                      <span className="text-gray-400">{query.text}</span>
                      <span className="animate-pulse ml-1">|</span>
                    </div>
                  ))}
              </div>

              {/* Industry Analysis */}
              <div className="space-y-2">
                <h3 className="text-sm font-medium text-gray-400 flex items-center">
                  <span className="mr-2">🏭</span>
                  Industry Analysis
                </h3>
                {researchState.queries
                  .filter((q) => q.category === "industry_analyzer")
                  .map((query, idx) => (
                    <div key={idx} className="p-3 bg-gray-800/50 rounded-lg border border-gray-700 text-sm">
                      <span className="text-gray-400">{query.text}</span>
                    </div>
                  ))}
                {Object.entries(researchState.streamingQueries)
                  .filter(([key]) => key.startsWith("industry_analyzer"))
                  .map(([key, query]) => (
                    <div key={key} className="p-3 bg-gray-800/50 rounded-lg border border-gray-700 text-sm">
                      <span className="text-gray-400">{query.text}</span>
                      <span className="animate-pulse ml-1">|</span>
                    </div>
                  ))}
              </div>

              {/* Financial Analysis */}
              <div className="space-y-2">
                <h3 className="text-sm font-medium text-gray-400 flex items-center">
                  <span className="mr-2">💰</span>
                  Financial Analysis
                </h3>
                {researchState.queries
                  .filter((q) => q.category === "financial_analyzer")
                  .map((query, idx) => (
                    <div key={idx} className="p-3 bg-gray-800/50 rounded-lg border border-gray-700 text-sm">
                      <span className="text-gray-400">{query.text}</span>
                    </div>
                  ))}
                {Object.entries(researchState.streamingQueries)
                  .filter(([key]) => key.startsWith("financial_analyzer"))
                  .map(([key, query]) => (
                    <div key={key} className="p-3 bg-gray-800/50 rounded-lg border border-gray-700 text-sm">
                      <span className="text-gray-400">{query.text}</span>
                      <span className="animate-pulse ml-1">|</span>
                    </div>
                  ))}
              </div>

              {/* News Analysis */}
              <div className="space-y-2">
                <h3 className="text-sm font-medium text-gray-400 flex items-center">
                  <span className="mr-2">📰</span>
                  News Analysis
                </h3>
                {researchState.queries
                  .filter((q) => q.category === "news_analyzer")
                  .map((query, idx) => (
                    <div key={idx} className="p-3 bg-gray-800/50 rounded-lg border border-gray-700 text-sm">
                      <span className="text-gray-400">{query.text}</span>
                    </div>
                  ))}
                {Object.entries(researchState.streamingQueries)
                  .filter(([key]) => key.startsWith("news_analyzer"))
                  .map(([key, query]) => (
                    <div key={key} className="p-3 bg-gray-800/50 rounded-lg border border-gray-700 text-sm">
                      <span className="text-gray-400">{query.text}</span>
                      <span className="animate-pulse ml-1">|</span>
                    </div>
                  ))}
              </div>
            </div>
          </div>
        )}

        {/* Document Curation Stats */}
        {researchState.docCounts && (
          <DocumentStats docCounts={researchState.docCounts} />
        )}
      </div>
    </div>
  );
}

export default App;
