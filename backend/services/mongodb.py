from pymongo import MongoClient
from datetime import datetime
from typing import Dict, Any, Optional
import os
import certifi

class MongoDBService:
    def __init__(self, uri: str):
        # Use certifi for SSL certificate verification with updated options
        self.client = MongoClient(
            uri,
            tlsCAFile=certifi.where(),
            retryWrites=True,
            w='majority'
        )
        self.db = self.client.get_database('tavily_research')
        self.jobs = self.db.jobs
        self.reports = self.db.reports

    def create_job(self, job_id: str, inputs: Dict[str, Any]) -> None:
        """Create a new research job record."""
        self.jobs.insert_one({
            "job_id": job_id,
            "inputs": inputs,
            "status": "pending",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })

    def update_job(self, job_id: str, 
                  status: str = None,
                  result: Dict[str, Any] = None,
                  error: str = None) -> None:
        """Update a research job with results or status."""
        update_data = {"updated_at": datetime.utcnow()}
        if status:
            update_data["status"] = status
        if result:
            update_data["result"] = result
        if error:
            update_data["error"] = error

        self.jobs.update_one(
            {"job_id": job_id},
            {"$set": update_data}
        )

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a job by ID."""
        return self.jobs.find_one({"job_id": job_id})

    def store_report(self, job_id: str, report_data: Dict[str, Any]) -> None:
        """Store the finalized research report."""
        self.reports.insert_one({
            "job_id": job_id,
            "report_content": report_data.get("report", ""),
            "references": report_data.get("references", []),
            "sections": report_data.get("sections_completed", []),
            "analyst_queries": report_data.get("analyst_queries", {}),
            "created_at": datetime.utcnow()
        })

    def get_report(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a report by job ID."""
        return self.reports.find_one({"job_id": job_id}) 