import type { ResearchStatus } from "../lib/types";
import { cn } from "../lib/utils";
import { useDarkMode } from "../hooks/useDarkMode";

interface Props {
  status: ResearchStatus | null;
  onDownloadPdf?: (pdfUrl: string) => void;
}

export function ResearchStatus({ status, onDownloadPdf }: Props) {
  const { darkMode } = useDarkMode();
  if (!status) return null;

  return (
    <div
      className={cn(
        "space-y-4 p-6 border rounded-lg shadow transition-colors duration-200",
        darkMode ? "bg-gray-800 border-gray-700" : "bg-white border-gray-200"
      )}
    >
      {/* Status Header */}
      <div className="flex items-center justify-between">
        <h3
          className={cn(
            "text-lg font-semibold",
            darkMode ? "text-white" : "text-gray-900"
          )}
        >
          Research Status: {status.status}
        </h3>
        <span
          className={cn(
            "text-sm",
            darkMode ? "text-gray-400" : "text-gray-500"
          )}
        >
          Last update: {new Date(status.last_update).toLocaleTimeString()}
        </span>
      </div>

      {/* Progress Bar */}
      <div
        className={cn(
          "w-full rounded-full h-2.5",
          darkMode ? "bg-gray-700" : "bg-gray-200"
        )}
      >
        <div
          className="bg-blue-600 h-2.5 rounded-full transition-all duration-500"
          style={{ width: `${status.progress}%` }}
        />
      </div>
      <div
        className={cn(
          "text-sm text-center",
          darkMode ? "text-gray-300" : "text-gray-600"
        )}
      >
        {status.progress}% Complete
      </div>

      {/* Debug Info */}
      <div className="mt-4 space-y-2">
        <h4
          className={cn(
            "font-medium",
            darkMode ? "text-gray-200" : "text-gray-900"
          )}
        >
          Progress Updates:
        </h4>
        <div className="max-h-40 overflow-y-auto space-y-2">
          {status.debug_info.map((info, index) => (
            <div
              key={index}
              className={cn(
                "text-sm p-2 rounded",
                darkMode ? "bg-gray-700" : "bg-gray-50"
              )}
            >
              <span className={darkMode ? "text-gray-400" : "text-gray-500"}>
                {new Date(info.timestamp).toLocaleTimeString()}:{" "}
              </span>
              <span className={darkMode ? "text-gray-200" : "text-gray-700"}>
                {info.message}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Results */}
      {status.status === "completed" && status.result && (
        <div className="mt-4">
          <h4
            className={cn(
              "font-medium",
              darkMode ? "text-gray-200" : "text-gray-900"
            )}
          >
            Results:
          </h4>
          <div className="mt-2 space-y-2">
            <div
              className={cn(
                "text-sm",
                darkMode ? "text-gray-300" : "text-gray-600"
              )}
            >
              Sections completed: {status.result.sections_completed.join(", ")}
            </div>
            <div
              className={cn(
                "text-sm",
                darkMode ? "text-gray-300" : "text-gray-600"
              )}
            >
              Total references: {status.result.total_references}
            </div>
            {onDownloadPdf && (
              <button
                onClick={() => onDownloadPdf(status.result!.pdf_url)}
                className="mt-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Download PDF Report
              </button>
            )}
          </div>
        </div>
      )}

      {/* Error */}
      {status.status === "failed" && status.error && (
        <div
          className={cn(
            "mt-4 p-3 rounded",
            darkMode ? "bg-red-900/50 text-red-200" : "bg-red-50 text-red-700"
          )}
        >
          <h4 className="font-medium">Error:</h4>
          <p className="text-sm mt-1">{status.error}</p>
        </div>
      )}
    </div>
  );
}
