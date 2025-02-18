import { motion, AnimatePresence } from "framer-motion";
import {
  TrendingUp,
  Building2,
  Newspaper,
  FileText,
  FileEdit,
  RefreshCw,
  Download,
  BookOpen,
} from "lucide-react";
import { cn } from "../lib/utils";
import { useEffect, useRef } from "react";
import type { ResearchStatus } from "../lib/types";

interface ProcessProps {
  isActive: boolean;
  currentStep: number;
  darkMode: boolean;
  onReset: () => void;
  status: ResearchStatus | null;
}

export function ResearchProcess({
  isActive,
  currentStep,
  darkMode,
  onReset,
  status,
}: ProcessProps) {
  const resultRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Helper function to extract queries for each analyst
  const getQueriesForAnalyst = (analyst: string) => {
    if (!status) return [];

    // If we have completed research, use the structured queries
    if (status.status === "completed" && status.result?.analyst_queries) {
      return (
        status.result.analyst_queries[
          analyst as keyof typeof status.result.analyst_queries
        ] || []
      );
    }

    // Otherwise, extract from debug messages for real-time updates
    return status.debug_info
      .filter((info) => info.message.includes(analyst))
      .map((info) => {
        const match = info.message.match(/Used queries:\s*(.+)/);
        if (match) {
          return match[1]
            .split("•")
            .map((q) => q.trim())
            .filter(Boolean);
        }
        return [];
      })
      .flat();
  };

  const processes = [
    {
      name: "Financial Analyst",
      icon: TrendingUp,
      gradientFrom: darkMode ? "from-blue-600/40" : "from-blue-500/40",
      gradientTo: darkMode ? "to-blue-500/20" : "to-blue-400/20",
      borderColor: darkMode ? "border-blue-400/20" : "border-blue-300/30",
      queries: getQueriesForAnalyst("Financial Analyst"),
    },
    {
      name: "Industry Analyst",
      icon: Building2,
      gradientFrom: darkMode ? "from-green-600/40" : "from-green-500/40",
      gradientTo: darkMode ? "to-green-500/20" : "to-green-400/20",
      borderColor: darkMode ? "border-green-400/20" : "border-green-300/30",
      queries: getQueriesForAnalyst("Industry Analyst"),
    },
    {
      name: "Company Analyst",
      icon: FileText,
      gradientFrom: darkMode ? "from-purple-600/40" : "from-purple-500/40",
      gradientTo: darkMode ? "to-purple-500/20" : "to-purple-400/20",
      borderColor: darkMode ? "border-purple-400/20" : "border-purple-300/30",
      queries: getQueriesForAnalyst("Company Analyst"),
    },
    {
      name: "News Scanner",
      icon: Newspaper,
      gradientFrom: darkMode ? "from-orange-600/40" : "from-orange-500/40",
      gradientTo: darkMode ? "to-orange-500/20" : "to-orange-400/20",
      borderColor: darkMode ? "border-orange-400/20" : "border-orange-300/30",
      queries: getQueriesForAnalyst("News Scanner"),
    },
  ];

  useEffect(() => {
    if (isActive && containerRef.current) {
      containerRef.current.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }
  }, [isActive]);

  useEffect(() => {
    if (currentStep === 2 && resultRef.current) {
      resultRef.current.style.opacity = "1";
    }
  }, [currentStep]);

  const getTransitionLine = () => {
    return "M 50 0 L 50 100";
  };

  return (
    <div className="w-full max-w-6xl mx-auto mt-8 space-y-8" ref={containerRef}>
      <AnimatePresence>
        {isActive && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="relative"
          >
            {/* Initial Transition Line */}
            <div className="relative h-[60px] mb-4">
              <svg
                className="absolute top-0 left-0 w-full h-full"
                preserveAspectRatio="xMidYMid meet"
                viewBox="0 0 100 100"
                style={{ pointerEvents: "none" }}
              >
                <motion.path
                  d={getTransitionLine()}
                  stroke={darkMode ? "#4B5563" : "#D1D5DB"}
                  strokeWidth="0.5"
                  fill="none"
                  initial={{ pathLength: 0, opacity: 0 }}
                  animate={{ pathLength: 1, opacity: 1 }}
                  transition={{ duration: 0.5, ease: "easeInOut" }}
                />
                <motion.circle
                  cx="50"
                  cy="100"
                  r="2"
                  fill={darkMode ? "#4B5563" : "#D1D5DB"}
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: 0.5, duration: 0.3 }}
                />
              </svg>
            </div>

            {/* Process Cards */}
            <div className="grid grid-cols-4 gap-4">
              {processes.map((process, index) => (
                <motion.div
                  key={process.name}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{
                    delay: 0.7 + index * 0.1,
                    duration: 0.5,
                    ease: "easeOut",
                  }}
                  className="space-y-4"
                >
                  <div
                    className={cn(
                      "p-6 rounded-lg backdrop-blur-md shadow-lg",
                      "bg-gradient-to-br",
                      process.gradientFrom,
                      process.gradientTo,
                      "border",
                      process.borderColor,
                      "transition-all duration-300",
                      darkMode ? "text-white/90" : "text-gray-800"
                    )}
                  >
                    <div
                      className={cn(
                        "w-12 h-12 rounded-full flex items-center justify-center mb-4",
                        "bg-white/10 backdrop-blur-sm"
                      )}
                    >
                      <process.icon className="w-6 h-6" />
                    </div>
                    <h3 className="font-semibold text-lg mb-3">
                      {process.name}
                    </h3>
                    <AnimatePresence>
                      {currentStep >= 1 && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: "auto" }}
                          exit={{ opacity: 0, height: 0 }}
                          transition={{ delay: 1 + index * 0.1 }}
                          className="space-y-2 text-sm"
                        >
                          {process.queries.map((query, qIndex) => (
                            <motion.div
                              key={qIndex}
                              initial={{ opacity: 0, x: -10 }}
                              animate={{ opacity: 1, x: 0 }}
                              transition={{
                                delay: 1.2 + index * 0.1 + qIndex * 0.1,
                              }}
                              className={cn(
                                "p-2 rounded backdrop-blur-sm",
                                darkMode ? "bg-white/5" : "bg-black/5"
                              )}
                            >
                              {query}
                            </motion.div>
                          ))}
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </motion.div>
              ))}
            </div>

            {/* Source Curation Card */}
            {currentStep >= 1 && (
              <>
                <div className="relative h-[60px] my-4">
                  <svg
                    className="absolute top-0 left-0 w-full h-full"
                    preserveAspectRatio="xMidYMid meet"
                    viewBox="0 0 100 100"
                    style={{ pointerEvents: "none" }}
                  >
                    <motion.path
                      d={getTransitionLine()}
                      stroke={darkMode ? "#4B5563" : "#D1D5DB"}
                      strokeWidth="0.5"
                      fill="none"
                      initial={{ pathLength: 0, opacity: 0 }}
                      animate={{ pathLength: 1, opacity: 1 }}
                      transition={{ duration: 0.5, delay: 1.5 }}
                    />
                    <motion.circle
                      cx="50"
                      cy="100"
                      r="2"
                      fill={darkMode ? "#4B5563" : "#D1D5DB"}
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ delay: 2, duration: 0.3 }}
                    />
                  </svg>
                </div>

                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 2, duration: 0.5 }}
                  className="max-w-xl mx-auto"
                >
                  <div
                    className={cn(
                      "p-6 rounded-lg backdrop-blur-md shadow-lg",
                      "bg-gradient-to-br",
                      darkMode
                        ? "from-teal-600/40 to-teal-500/20"
                        : "from-teal-500/40 to-teal-400/20",
                      "border",
                      darkMode ? "border-teal-400/20" : "border-teal-300/30",
                      "transition-all duration-300",
                      darkMode ? "text-white/90" : "text-gray-800"
                    )}
                  >
                    <div
                      className={cn(
                        "w-12 h-12 rounded-full flex items-center justify-center mb-4",
                        "bg-white/10 backdrop-blur-sm"
                      )}
                    >
                      <BookOpen className="w-6 h-6" />
                    </div>
                    <h3 className="font-semibold text-lg mb-3">
                      Source Curation & Briefing
                    </h3>
                    <div className="space-y-2 text-sm">
                      <div
                        className={cn(
                          "p-2 rounded backdrop-blur-sm",
                          darkMode ? "bg-white/5" : "bg-black/5"
                        )}
                      >
                        Validating information sources
                      </div>
                      <div
                        className={cn(
                          "p-2 rounded backdrop-blur-sm",
                          darkMode ? "bg-white/5" : "bg-black/5"
                        )}
                      >
                        Cross-referencing data points
                      </div>
                      <div
                        className={cn(
                          "p-2 rounded backdrop-blur-sm",
                          darkMode ? "bg-white/5" : "bg-black/5"
                        )}
                      >
                        Generating preliminary briefing
                      </div>
                    </div>
                  </div>
                </motion.div>

                {/* Editing Card */}
                <div className="relative h-[60px] my-4">
                  <svg
                    className="absolute top-0 left-0 w-full h-full"
                    preserveAspectRatio="xMidYMid meet"
                    viewBox="0 0 100 100"
                    style={{ pointerEvents: "none" }}
                  >
                    <motion.path
                      d={getTransitionLine()}
                      stroke={darkMode ? "#4B5563" : "#D1D5DB"}
                      strokeWidth="0.5"
                      fill="none"
                      initial={{ pathLength: 0, opacity: 0 }}
                      animate={{ pathLength: 1, opacity: 1 }}
                      transition={{ duration: 0.5, delay: 2.5 }}
                    />
                    <motion.circle
                      cx="50"
                      cy="100"
                      r="2"
                      fill={darkMode ? "#4B5563" : "#D1D5DB"}
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ delay: 3, duration: 0.3 }}
                    />
                  </svg>
                </div>

                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 3, duration: 0.5 }}
                  className="max-w-xl mx-auto"
                >
                  <div
                    className={cn(
                      "p-6 rounded-lg backdrop-blur-md shadow-lg",
                      "bg-gradient-to-br",
                      darkMode
                        ? "from-indigo-600/40 to-indigo-500/20"
                        : "from-indigo-500/40 to-indigo-400/20",
                      "border",
                      darkMode
                        ? "border-indigo-400/20"
                        : "border-indigo-300/30",
                      "transition-all duration-300",
                      darkMode ? "text-white/90" : "text-gray-800"
                    )}
                  >
                    <div
                      className={cn(
                        "w-12 h-12 rounded-full flex items-center justify-center mb-4",
                        "bg-white/10 backdrop-blur-sm"
                      )}
                    >
                      <FileEdit className="w-6 h-6" />
                    </div>
                    <h3 className="font-semibold text-lg mb-3">
                      Editing Report
                    </h3>
                    <div className="space-y-2 text-sm">
                      <div
                        className={cn(
                          "p-2 rounded backdrop-blur-sm",
                          darkMode ? "bg-white/5" : "bg-black/5"
                        )}
                      >
                        Compiling analysis results
                      </div>
                      <div
                        className={cn(
                          "p-2 rounded backdrop-blur-sm",
                          darkMode ? "bg-white/5" : "bg-black/5"
                        )}
                      >
                        Formatting document structure
                      </div>
                      <div
                        className={cn(
                          "p-2 rounded backdrop-blur-sm",
                          darkMode ? "bg-white/5" : "bg-black/5"
                        )}
                      >
                        Generating executive summary
                      </div>
                    </div>
                  </div>
                </motion.div>

                {/* Connection to Final Report */}
                {currentStep >= 2 && (
                  <div className="relative h-[60px] my-4">
                    <svg
                      className="absolute top-0 left-0 w-full h-full"
                      preserveAspectRatio="xMidYMid meet"
                      viewBox="0 0 100 100"
                      style={{ pointerEvents: "none" }}
                    >
                      <motion.path
                        d={getTransitionLine()}
                        stroke={darkMode ? "#4B5563" : "#D1D5DB"}
                        strokeWidth="0.5"
                        fill="none"
                        initial={{ pathLength: 0, opacity: 0 }}
                        animate={{ pathLength: 1, opacity: 1 }}
                        transition={{ duration: 0.5, delay: 3.5 }}
                      />
                      <motion.circle
                        cx="50"
                        cy="100"
                        r="2"
                        fill={darkMode ? "#4B5563" : "#D1D5DB"}
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ delay: 4, duration: 0.3 }}
                      />
                    </svg>
                  </div>
                )}
              </>
            )}
          </motion.div>
        )}

        {/* Final Report Section */}
        {currentStep >= 2 && (
          <motion.div
            ref={resultRef}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className={cn(
              "mt-8 p-8 rounded-xl backdrop-blur-md shadow-xl",
              darkMode
                ? "bg-gray-800/40 border border-gray-700/50"
                : "bg-white/40 border border-gray-200/50"
            )}
          >
            <h2
              className={cn(
                "text-2xl font-bold mb-6",
                darkMode ? "text-white" : "text-gray-800"
              )}
            >
              Analysis Report
            </h2>

            <div
              className={cn("prose max-w-none", darkMode ? "prose-invert" : "")}
            >
              <p className="text-lg mb-4">
                Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do
                eiusmod tempor incididunt ut labore et dolore magna aliqua.
              </p>

              <h3 className="text-xl font-semibold mt-6 mb-4">Key Findings</h3>
              <ul className="list-disc pl-6 space-y-2">
                <li>
                  Market position analysis reveals strong competitive advantage
                </li>
                <li>
                  Financial metrics indicate sustainable growth trajectory
                </li>
                <li>Recent news sentiment shows positive market reception</li>
              </ul>

              <div className="flex gap-4 mt-8">
                <button
                  onClick={() => {}}
                  className={cn(
                    "flex items-center gap-2 px-4 py-2 rounded-md transition-colors",
                    darkMode
                      ? "bg-blue-600/80 hover:bg-blue-700/80 text-white backdrop-blur-sm"
                      : "bg-blue-500/80 hover:bg-blue-600/80 text-white backdrop-blur-sm"
                  )}
                >
                  <Download className="w-4 h-4" />
                  Export Report
                </button>

                <button
                  onClick={onReset}
                  className={cn(
                    "flex items-center gap-2 px-4 py-2 rounded-md transition-colors backdrop-blur-sm",
                    darkMode
                      ? "bg-gray-700/50 hover:bg-gray-600/50 text-white"
                      : "bg-gray-200/50 hover:bg-gray-300/50 text-gray-800"
                  )}
                >
                  <RefreshCw className="w-4 h-4" />
                  Start Over
                </button>
              </div>
            </div>

            {/* Error State */}
            {status?.status === "failed" && status.error && (
              <div
                className={cn(
                  "mt-4 p-4 rounded",
                  darkMode
                    ? "bg-red-900/50 text-red-200"
                    : "bg-red-50 text-red-700"
                )}
              >
                <h3 className="font-medium mb-2">Error Occurred</h3>
                <p>{status.error}</p>
                <button
                  onClick={onReset}
                  className={cn(
                    "flex items-center gap-2 px-4 py-2 rounded-md transition-colors mt-4",
                    darkMode
                      ? "bg-red-800/50 hover:bg-red-700/50 text-white"
                      : "bg-red-100/50 hover:bg-red-200/50 text-red-800"
                  )}
                >
                  <RefreshCw className="w-4 h-4" />
                  Try Again
                </button>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
