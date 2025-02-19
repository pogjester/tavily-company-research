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

type ResearchStatus = {
  step: string;
  message: string;
};

type ResearchOutput = {
  summary: string;
  details: Record<string, any>;
};

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000";

function App() {
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

        if (statusData.status === "processing") {
          setIsComplete(false);
          setStatus({
            step: statusData.result?.step || "Processing",
            message: statusData.message || "Processing...",
          });
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
    setIsResearching(true);
    setStatus({
      step: "Initializing",
      message: "Starting company research...",
    });
    setOutput(null);
    setError(null);

    try {
      const response = await fetch(`${API_URL}/research`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          company: formData.companyName,
          company_url: formData.companyUrl || undefined,
          industry: formData.companyIndustry || undefined,
          hq_location: formData.companyHq || undefined,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log("Research started:", data);

      if (data.job_id) {
        connectWebSocket(data.job_id);
      } else {
        throw new Error("No job ID received");
      }
    } catch (err) {
      console.error("Error starting research:", err);
      setError(err instanceof Error ? err.message : "Failed to start research");
      setIsResearching(false);
    }
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
          <div className="glass rounded-xl shadow-lg p-6">
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
                  className="text-gray-300 prose-ul:list-disc prose-li:ml-4"
                  components={{
                    ul: ({ children }) => (
                      <ul className="list-disc space-y-1 ml-4">{children}</ul>
                    ),
                    li: ({ children }) => (
                      <li className="text-gray-300">{children}</li>
                    ),
                    h2: ({ children }) => (
                      <h2 className="text-xl font-semibold text-white mt-8 mb-4">
                        {children}
                      </h2>
                    ),
                    hr: () => <hr className="border-t border-gray-700 my-4" />,
                    a: ({ href, children }) => (
                      <a
                        href={href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-400 hover:text-blue-300 underline"
                      >
                        {children}
                      </a>
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
