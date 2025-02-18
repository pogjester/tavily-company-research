from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from backend.graph import Graph
from backend.utils.utils import generate_pdf_from_md
from backend.websocket_manager import ConnectionManager
from dotenv import load_dotenv
import logging
import os
import uvicorn
from datetime import datetime
import asyncio
import uuid
from collections import defaultdict

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize FastAPI application
app = FastAPI(title="Tavily Company Research API")

@app.on_event("startup")
async def startup_event():
    """Runs when the application starts."""
    logger.info("Starting up Tavily Company Research API")
    # Create reports directory if it doesn't exist
    if not os.path.exists(REPORTS_DIR):
        os.makedirs(REPORTS_DIR)
        logger.info(f"Created reports directory at {REPORTS_DIR}")

@app.on_event("shutdown")
async def shutdown_event():
    """Runs when the application is shutting down."""
    logger.info("Shutting down Tavily Company Research API")
    # Clean up any active WebSocket connections
    for job_connections in manager.active_connections.values():
        for connection in job_connections:
            try:
                await connection.close()
            except:
                pass

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Create reports directory if it doesn't exist
REPORTS_DIR = "reports"
if not os.path.exists(REPORTS_DIR):
    os.makedirs(REPORTS_DIR)

# Initialize WebSocket manager
manager = ConnectionManager()

# Store research results and job status in memory
research_cache = {}
job_status = defaultdict(lambda: {
    "status": "pending",
    "result": None,
    "error": None,
    "debug_info": [],
    "last_update": datetime.now().isoformat(),
    "progress": 0
})

def update_job_status(job_id: str, status: str = None, progress: int = None, message: str = None, error: str = None, result: dict = None):
    """Update job status with debug information."""
    job = job_status[job_id]
    
    if message:
        job["debug_info"].append({
            "timestamp": datetime.now().isoformat(),
            "message": message
        })
    
    if status:
        job["status"] = status
    if progress is not None:
        job["progress"] = progress
    if error:
        job["error"] = error
    if result:
        job["result"] = result
        
    job["last_update"] = datetime.now().isoformat()

class ResearchRequest(BaseModel):
    company: str
    company_url: str | None = None
    industry: str | None = None
    hq_location: str | None = None

async def process_research(job_id: str, data: ResearchRequest):
    """Background task to process research request."""
    try:
        update_job_status(job_id, status="processing", progress=0, message=f"Starting research for {data.company}")
        await manager.send_status_update(
            job_id,
            status="processing",
            progress=0,
            message=f"Starting research for {data.company}"
        )
        
        # Initialize research graph
        update_job_status(job_id, progress=5, message="Initializing research graph")
        await manager.send_status_update(
            job_id,
            status="processing",
            progress=5,
            message="Initializing research graph"
        )
        
        graph = Graph(
            company=data.company,
            url=data.company_url,
            industry=data.industry,
            hq_location=data.hq_location
        )

        # Run research pipeline
        results = []
        state = {}
        update_job_status(job_id, progress=10, message="Starting research pipeline")
        await manager.send_status_update(
            job_id,
            status="processing",
            progress=10,
            message="Starting research pipeline"
        )
        
        progress = 10
        analyst_queries = {
            "Financial Analyst": [],
            "Industry Analyst": [],
            "Company Analyst": [],
            "News Scanner": []
        }

        async for s in graph.run({}, {}):
            state.update(s)
            
            # Update progress based on state changes
            if messages := state.get('messages', []):
                latest_message = messages[-1].content
                results.append(latest_message)

                # Extract queries if present in the message
                if "Used queries:" in latest_message:
                    for analyst in analyst_queries.keys():
                        if analyst in latest_message:
                            queries_start = latest_message.index("Used queries:") + len("Used queries:")
                            queries = [
                                q.strip() 
                                for q in latest_message[queries_start:].strip().split("•") 
                                if q.strip()
                            ]
                            analyst_queries[analyst] = queries
                            # Send analyst-specific update
                            await manager.send_analyst_update(job_id, analyst, queries)

                progress = min(progress + 10, 90)
                update_job_status(job_id, progress=progress, message=latest_message)
                await manager.send_status_update(
                    job_id,
                    status="processing",
                    progress=progress,
                    message=latest_message
                )
            
            # Log specific state updates
            if briefings := state.get('briefings'):
                sections = list(briefings.keys())
                progress = min(progress + 5, 90)
                update_job_status(
                    job_id, 
                    progress=progress,
                    message=f"Completed briefings for sections: {', '.join(sections)}"
                )
                await manager.send_status_update(
                    job_id,
                    status="processing",
                    progress=progress,
                    message=f"Completed briefings for sections: {', '.join(sections)}"
                )

        update_job_status(job_id, progress=95, message="Research pipeline completed, generating report")
        await manager.send_status_update(
            job_id,
            status="processing",
            progress=95,
            message="Research pipeline completed, generating report"
        )

        # Get the report content
        report_content = state.get('output', {}).get('report', '')
        
        if not report_content or not report_content.strip():
            raise Exception("No report content generated")

        # Generate PDF
        update_job_status(job_id, progress=98, message="Generating PDF report")
        await manager.send_status_update(
            job_id,
            status="processing",
            progress=98,
            message="Generating PDF report"
        )
        
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        pdf_filename = f"{data.company.replace(' ', '_')}_{timestamp}.pdf"
        pdf_path = os.path.join(REPORTS_DIR, pdf_filename)
        
        generate_pdf_from_md(report_content, pdf_path)
        
        # Store results
        research_cache[data.company] = {
            'results': results,
            'report': report_content,
            'briefings': state.get('briefings', {}),
            'references': state.get('references', {}),
            'pdf_path': pdf_path
        }
        
        # Prepare final result
        final_result = {
            "results": results,
            "report": report_content,
            "pdf_url": f"/research/pdf/{pdf_filename}",
            "sections_completed": list(state.get('briefings', {}).keys()),
            "total_references": len(state.get('references', [])),
            "completion_time": datetime.now().isoformat(),
            "analyst_queries": analyst_queries
        }
        
        # Send final success update
        update_job_status(
            job_id,
            status="completed",
            progress=100,
            message="Research completed successfully",
            result=final_result
        )
        await manager.send_status_update(
            job_id,
            status="completed",
            progress=100,
            message="Research completed successfully",
            result=final_result
        )
        
    except Exception as e:
        logger.error(f"Error processing job {job_id}: {str(e)}", exc_info=True)
        update_job_status(
            job_id,
            status="failed",
            progress=0,
            message=f"Error during research: {str(e)}",
            error=str(e)
        )
        await manager.send_status_update(
            job_id,
            status="failed",
            progress=0,
            message=f"Error during research: {str(e)}",
            error=str(e)
        )

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

@app.get("/")
async def root():
    """Root endpoint."""
    return {"status": "healthy", "message": "Tavily Company Research API is running"}

@app.post("/research")
async def research(data: ResearchRequest):
    """Start a new research job."""
    try:
        logger.info(f"Received research request for {data.company}")
        
        # Generate a job ID
        job_id = str(uuid.uuid4())
        
        # Start background task
        asyncio.create_task(process_research(job_id, data))
        
        return {
            "status": "accepted",
            "job_id": job_id,
            "message": "Research started. Connect to WebSocket for updates.",
            "websocket_url": f"/research/ws/{job_id}"
        }

    except Exception as e:
        logger.error(f"Error initiating research: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/research/pdf/{filename}")
async def get_pdf(filename: str):
    """Download PDF report endpoint."""
    try:
        pdf_path = os.path.join(REPORTS_DIR, filename)
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=404, detail="PDF not found")
        return FileResponse(pdf_path, media_type='application/pdf', filename=filename)
    except Exception as e:
        logger.error(f"Error sending PDF: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving PDF")

@app.websocket("/research/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for research status updates."""
    try:
        # Log connection attempt
        logger.info(f"WebSocket connection attempt for job {job_id}")
        
        await websocket.accept()
        await manager.connect(websocket, job_id)
        
        # Send initial state if job exists
        if job_id in job_status:
            status = job_status[job_id]
            await manager.send_status_update(
                job_id,
                status=status["status"],
                progress=status["progress"],
                message="Connected to status stream",
                error=status["error"],
                result=status["result"]
            )
            
        # Keep connection alive until client disconnects
        while True:
            try:
                # Wait for client messages (if any)
                data = await websocket.receive_text()
                logger.info(f"Received message from client: {data}")
                # You can handle client messages here if needed
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for job {job_id}")
                manager.disconnect(websocket, job_id)
                break
                
    except Exception as e:
        logger.error(f"WebSocket error for job {job_id}: {str(e)}", exc_info=True)
        manager.disconnect(websocket, job_id)

if __name__ == '__main__':
    uvicorn.run(
        "application:app",
        host='0.0.0.0',
        port=8000,
        reload=True,
        ws='websockets'
    ) 