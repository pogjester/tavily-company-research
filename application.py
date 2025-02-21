from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from backend.graph import Graph
from backend.utils.utils import generate_pdf_from_md
from backend.services.websocket_manager import WebSocketManager
from dotenv import load_dotenv
import logging
import os
import uvicorn
from datetime import datetime
import asyncio
import uuid
from collections import defaultdict
from backend.services.mongodb import MongoDBService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Ensure reports directory exists
REPORTS_DIR = "reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

# Initialize FastAPI application
app = FastAPI(title="Tavily Company Research API")

# Enable CORS - Explicitly allow frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5174",
        "http://localhost:5173",
        "https://tavily-company-research-65wtjfqzu-pogjesters-projects.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

@app.on_event("startup")
async def startup_event():
    """Runs when the application starts."""
    logger.info("Starting up Tavily Company Research API")

@app.on_event("shutdown")
async def shutdown_event():
    """Runs when the application is shutting down."""
    logger.info("Shutting down Tavily Company Research API")
    for job_connections in manager.active_connections.values():
        for connection in job_connections:
            try:
                await connection.close()
            except Exception:
                pass

# Initialize WebSocket manager
manager = WebSocketManager()

# Store research results and job status in memory
job_status = defaultdict(lambda: {
    "status": "pending",
    "result": None,
    "error": None,
    "debug_info": [],
    "last_update": datetime.now().isoformat()
})

# Initialize MongoDB service if URI is provided
mongodb = None
if os.getenv("MONGODB_URI"):
    mongodb = MongoDBService(os.getenv("MONGODB_URI"))

class ResearchRequest(BaseModel):
    company: str
    company_url: str | None = None
    industry: str | None = None
    hq_location: str | None = None

@app.options("/research")
async def preflight():
    """Handle CORS preflight requests explicitly."""
    response = JSONResponse(content=None, status_code=200)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response

@app.post("/research")
async def research(data: ResearchRequest):
    """Start a new research job."""
    try:
        logger.info(f"Received research request for {data.company}")
        job_id = str(uuid.uuid4())
        asyncio.create_task(process_research(job_id, data))

        response = JSONResponse(content={
            "status": "accepted",
            "job_id": job_id,
            "message": "Research started. Connect to WebSocket for updates.",
            "websocket_url": f"/research/ws/{job_id}"
        })
        
        # Add CORS headers manually
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"

        return response

    except Exception as e:
        logger.error(f"Error initiating research: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

async def process_research(job_id: str, data: ResearchRequest):
    """Background task to process research request."""
    try:
        if mongodb:
            mongodb.create_job(job_id, data.dict())
        await asyncio.sleep(1)  # Allow WebSocket connection

        await manager.send_status_update(job_id, status="processing", message="Starting research")

        graph = Graph(
            company=data.company,
            url=data.company_url,
            industry=data.industry,
            hq_location=data.hq_location,
            websocket_manager=manager,
            job_id=job_id
        )

        results = []
        state = {}

        async for s in graph.run(thread={}):
            state.update(s)
            if messages := state.get('messages', []):
                results.append(messages[-1].content)

        report_content = state.get('output', {}).get('report', '')

        if not report_content.strip():
            raise Exception("No report content generated")

        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        pdf_filename = f"{data.company.replace(' ', '_')}_{timestamp}.pdf"
        pdf_path = os.path.join(REPORTS_DIR, pdf_filename)

        generate_pdf_from_md(report_content, pdf_path)

        final_result = {
            "results": results,
            "report": report_content,
            "pdf_url": f"/research/pdf/{pdf_filename}",
        }

        await manager.send_status_update(job_id, status="completed", message="Research completed", result=final_result)

        if mongodb:
            mongodb.update_job(job_id=job_id, status="completed")
            mongodb.store_report(job_id=job_id, report_data=final_result)

    except Exception as e:
        logger.error(f"Research failed: {e}")
        if mongodb:
            mongodb.update_job(job_id=job_id, status="failed", error=str(e))

@app.get("/research/pdf/{filename}")
async def get_pdf(filename: str):
    """Download PDF report endpoint."""
    pdf_path = os.path.join(REPORTS_DIR, filename)
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(pdf_path, media_type='application/pdf', filename=filename)

@app.websocket("/research/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """WebSocket endpoint (CORS does not apply)."""
    try:
        await websocket.accept()
        await manager.connect(websocket, job_id)

        if job_id in job_status:
            status = job_status[job_id]
            await manager.send_status_update(
                job_id,
                status=status["status"],
                message="Connected to status stream",
                error=status["error"],
                result=status["result"]
            )

        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                manager.disconnect(websocket, job_id)
                break

    except Exception as e:
        logger.error(f"WebSocket error for job {job_id}: {str(e)}", exc_info=True)
        manager.disconnect(websocket, job_id)

@app.get("/research/{job_id}")
async def get_research(job_id: str):
    """Retrieve research results by job ID."""
    job = mongodb.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Research job not found")
    return job

@app.get("/research/{job_id}/report")
async def get_research_report(job_id: str):
    """Retrieve research report by job ID."""
    report = mongodb.get_report(job_id)
    if not report:
        raise HTTPException(status_code=404, detail="Research report not found")
    return report

if __name__ == '__main__':
    uvicorn.run(
        "application:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
