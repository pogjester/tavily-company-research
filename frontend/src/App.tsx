import { useState } from "react";
import { ResearchProcess } from "./components/ResearchProcess";
import { useDarkMode } from "./hooks/useDarkMode";
import { useResearch } from "./hooks/useResearch";
import { cn } from "./lib/utils";
import type { ResearchRequest } from "./lib/types";

export default function App() {
  const { darkMode } = useDarkMode();
  const { startResearch, isLoading, error, status } = useResearch();
  const [isProcessActive, setIsProcessActive] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [formData, setFormData] = useState<ResearchRequest>({
    company: "",
    company_url: "",
    industry: "",
    hq_location: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      // Only start if we have required fields
      if (!formData.company) {
        return;
      }

      // Reset any previous state
      setIsProcessActive(false);
      setCurrentStep(0);

      // Start research with form data
      await startResearch(formData);

      // Update UI state after successful API call
      setIsProcessActive(true);
      setCurrentStep(1);
    } catch (err) {
      console.error("Failed to start research:", err);
      setIsProcessActive(false);
      setCurrentStep(0);
    }
  };

  const handleReset = () => {
    setIsProcessActive(false);
    setCurrentStep(0);
    setFormData({
      company: "",
      company_url: "",
      industry: "",
      hq_location: "",
    });
  };

  return (
    <div
      className={cn(
        "min-h-screen w-full transition-colors duration-200",
        darkMode ? "bg-gray-900" : "bg-gray-50"
      )}
    >
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-2xl mx-auto">
          <h1
            className={cn(
              "text-4xl font-bold mb-8 text-center",
              darkMode ? "text-white" : "text-gray-900"
            )}
          >
            Company Research Assistant
          </h1>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label
                htmlFor="company"
                className={cn(
                  "block text-sm font-medium mb-2",
                  darkMode ? "text-gray-200" : "text-gray-700"
                )}
              >
                Company Name *
              </label>
              <input
                type="text"
                id="company"
                value={formData.company}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, company: e.target.value }))
                }
                className={cn(
                  "w-full px-4 py-2 rounded-lg border focus:ring-2 focus:ring-blue-500 focus:outline-none transition-colors duration-200",
                  darkMode
                    ? "bg-gray-800 border-gray-700 text-white"
                    : "bg-white border-gray-300 text-gray-900"
                )}
                required
              />
            </div>

            <div>
              <label
                htmlFor="company_url"
                className={cn(
                  "block text-sm font-medium mb-2",
                  darkMode ? "text-gray-200" : "text-gray-700"
                )}
              >
                Company Website
              </label>
              <input
                type="url"
                id="company_url"
                value={formData.company_url}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    company_url: e.target.value,
                  }))
                }
                className={cn(
                  "w-full px-4 py-2 rounded-lg border focus:ring-2 focus:ring-blue-500 focus:outline-none transition-colors duration-200",
                  darkMode
                    ? "bg-gray-800 border-gray-700 text-white"
                    : "bg-white border-gray-300 text-gray-900"
                )}
              />
            </div>

            <div>
              <label
                htmlFor="industry"
                className={cn(
                  "block text-sm font-medium mb-2",
                  darkMode ? "text-gray-200" : "text-gray-700"
                )}
              >
                Industry
              </label>
              <input
                type="text"
                id="industry"
                value={formData.industry}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, industry: e.target.value }))
                }
                className={cn(
                  "w-full px-4 py-2 rounded-lg border focus:ring-2 focus:ring-blue-500 focus:outline-none transition-colors duration-200",
                  darkMode
                    ? "bg-gray-800 border-gray-700 text-white"
                    : "bg-white border-gray-300 text-gray-900"
                )}
              />
            </div>

            <div>
              <label
                htmlFor="hq_location"
                className={cn(
                  "block text-sm font-medium mb-2",
                  darkMode ? "text-gray-200" : "text-gray-700"
                )}
              >
                HQ Location
              </label>
              <input
                type="text"
                id="hq_location"
                value={formData.hq_location}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    hq_location: e.target.value,
                  }))
                }
                className={cn(
                  "w-full px-4 py-2 rounded-lg border focus:ring-2 focus:ring-blue-500 focus:outline-none transition-colors duration-200",
                  darkMode
                    ? "bg-gray-800 border-gray-700 text-white"
                    : "bg-white border-gray-300 text-gray-900"
                )}
              />
            </div>

            <button
              type="submit"
              disabled={!formData.company || isLoading}
              className={cn(
                "w-full py-3 px-4 rounded-lg font-medium transition-colors duration-200",
                !formData.company || isLoading
                  ? "bg-gray-400 cursor-not-allowed"
                  : darkMode
                  ? "bg-blue-600 hover:bg-blue-700 text-white"
                  : "bg-blue-500 hover:bg-blue-600 text-white"
              )}
            >
              {isLoading ? "Starting Research..." : "Start Research"}
            </button>
          </form>

          {error && (
            <div className="mt-4 p-4 bg-red-50 text-red-700 rounded-md border border-red-200">
              {error}
            </div>
          )}
        </div>

        <ResearchProcess
          isActive={isProcessActive}
          currentStep={currentStep}
          darkMode={darkMode}
          onReset={handleReset}
          status={status}
        />
      </div>
    </div>
  );
}
