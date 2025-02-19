import React, { useState, useEffect } from "react";
import axios from "axios";

function App() {
  const [formData, setFormData] = useState({
    company: "",
    company_url: "",
    hq_location: "",
    industry: "",
  });
  const [jobId, setJobId] = useState("");
  const [wsUrl, setWsUrl] = useState("");
  const [statusUpdates, setStatusUpdates] = useState<string[]>([]);
  const [finalReport, setFinalReport] = useState("");

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      // POST to the research endpoint
      const res = await axios.post("http://localhost:8000/research", formData);
      setJobId(res.data.job_id);
      // Construct WebSocket URL
      setWsUrl(`ws://localhost:8000/research/ws/${res.data.job_id}`);
    } catch (error) {
      console.error("Failed to start research:", error);
    }
  };

  useEffect(() => {
    if (!wsUrl) return;
    const ws = new WebSocket(wsUrl);
    ws.onopen = () => {
      console.log("WebSocket connected");
    };
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setStatusUpdates((prev) => [...prev, JSON.stringify(data)]);
      // When research is complete, assume there is a report in the result
      if (data.status === "completed" && data.result) {
        setFinalReport(data.result.report);
      }
    };
    ws.onerror = (err) => console.error("WebSocket error:", err);
    ws.onclose = () => console.log("WebSocket closed");
    return () => ws.close();
  }, [wsUrl]);

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col items-center py-10">
      <h1 className="text-4xl font-bold mb-6">Company Research Assistant</h1>
      <form
        onSubmit={handleSubmit}
        className="bg-white p-6 rounded shadow-md w-full max-w-md"
      >
        <div className="mb-4">
          <label htmlFor="company" className="block mb-1 font-semibold">
            Company Name *
          </label>
          <input
            type="text"
            id="company"
            name="company"
            value={formData.company}
            onChange={handleChange}
            required
            className="w-full border rounded px-3 py-2"
          />
        </div>
        <div className="mb-4">
          <label htmlFor="company_url" className="block mb-1 font-semibold">
            Company URL
          </label>
          <input
            type="url"
            id="company_url"
            name="company_url"
            value={formData.company_url}
            onChange={handleChange}
            className="w-full border rounded px-3 py-2"
          />
        </div>
        <div className="mb-4">
          <label htmlFor="hq_location" className="block mb-1 font-semibold">
            HQ Location
          </label>
          <input
            type="text"
            id="hq_location"
            name="hq_location"
            value={formData.hq_location}
            onChange={handleChange}
            className="w-full border rounded px-3 py-2"
          />
        </div>
        <div className="mb-4">
          <label htmlFor="industry" className="block mb-1 font-semibold">
            Industry
          </label>
          <input
            type="text"
            id="industry"
            name="industry"
            value={formData.industry}
            onChange={handleChange}
            className="w-full border rounded px-3 py-2"
          />
        </div>
        <button
          type="submit"
          className="w-full bg-blue-500 text-white py-2 rounded hover:bg-blue-600"
        >
          Start Research
        </button>
      </form>
      <div className="mt-8 w-full max-w-md">
        <h2 className="text-xl font-semibold mb-4">Status Updates</h2>
        <div className="bg-white p-4 rounded shadow h-64 overflow-auto">
          {statusUpdates.map((update, idx) => (
            <p key={idx} className="text-sm">
              {update}
            </p>
          ))}
        </div>
      </div>
      {finalReport && (
        <div className="mt-8 w-full max-w-md">
          <h2 className="text-xl font-semibold mb-4">Final Research Report</h2>
          <div className="bg-white p-4 rounded shadow">
            <pre className="text-sm whitespace-pre-wrap">{finalReport}</pre>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
