from flask import Flask, request, jsonify, send_file
from backend.graph import Graph
from backend.utils.utils import generate_pdf_from_md
from dotenv import load_dotenv
import logging
import os
from datetime import datetime
import asyncio
import uuid
from collections import defaultdict
from flask_cors import CORS

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Flask application
application = Flask(__name__)
app = application

# Enable CORS
CORS(app, resources={
    r"/research*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173"]},
    r"/health": {"origins": "*"}
})

# Create reports directory if it doesn't exist
REPORTS_DIR = "reports"
if not os.path.exists(REPORTS_DIR):
    os.makedirs(REPORTS_DIR)

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

def update_job_status(job_id, message, status=None, error=None, result=None, progress=None):
    """Update job status with debug information."""
    job = job_status[job_id]
    job["debug_info"].append({
        "timestamp": datetime.now().isoformat(),
        "message": message
    })
    job["last_update"] = datetime.now().isoformat()
    
    if status:
        job["status"] = status
    if error:
        job["error"] = error
    if result:
        job["result"] = result
    if progress is not None:
        job["progress"] = progress

async def process_research(job_id, data):
    """Background task to process research request."""
    try:
        update_job_status(job_id, f"Starting research for {data.get('company')}", status="processing", progress=0)
        
        # Initialize research graph
        update_job_status(job_id, "Initializing research graph", progress=5)
        graph = Graph(
            company=data.get('company'),
            url=data.get('company_url'),
            industry=data.get('industry'),
            hq_location=data.get('hq_location')
        )

        # Run research pipeline
        results = []
        state = {}
        update_job_status(job_id, "Starting research pipeline", progress=10)
        
        progress = 10
        async for s in graph.run({}, {}):
            state.update(s)
            
            # Update progress based on state changes
            if messages := state.get('messages', []):
                latest_message = messages[-1].content
                results.append(latest_message)
                update_job_status(
                    job_id, 
                    f"Research update: {latest_message[:100]}...",
                    progress=min(progress + 10, 90)
                )
                progress = min(progress + 10, 90)
            
            # Log specific state updates
            if briefings := state.get('briefings'):
                sections = list(briefings.keys())
                update_job_status(
                    job_id,
                    f"Completed briefings for sections: {', '.join(sections)}",
                    progress=min(progress + 5, 90)
                )

        update_job_status(job_id, "Research pipeline completed, generating report", progress=95)

        # Get the report content
        report_content = state.get('output', {}).get('report', '')
        
        if not report_content or not report_content.strip():
            raise Exception("No report content generated")

        # Generate PDF
        update_job_status(job_id, "Generating PDF report", progress=98)
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        pdf_filename = f"{data['company'].replace(' ', '_')}_{timestamp}.pdf"
        pdf_path = os.path.join(REPORTS_DIR, pdf_filename)
        
        generate_pdf_from_md(report_content, pdf_path)
        
        # Store results
        research_cache[data['company']] = {
            'results': results,
            'report': report_content,
            'briefings': state.get('briefings', {}),
            'references': state.get('references', {}),
            'pdf_path': pdf_path
        }
        
        # Update final job status
        update_job_status(
            job_id,
            "Research completed successfully",
            status="completed",
            progress=100,
            result={
                "results": results,
                "report": report_content,
                "pdf_url": f"/research/pdf/{pdf_filename}",
                "sections_completed": list(state.get('briefings', {}).keys()),
                "total_references": len(state.get('references', [])),
                "completion_time": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Error processing job {job_id}: {str(e)}", exc_info=True)
        update_job_status(
            job_id,
            f"Error during research: {str(e)}",
            status="failed",
            error=str(e)
        )

@app.route('/health', methods=['GET'])
async def health_check():
    """Health check endpoint for AWS."""
    return jsonify({"status": "healthy"}), 200

@app.route('/', methods=['GET'])
async def root():
    """Root endpoint."""
    return jsonify({"status": "healthy", "message": "Tavily Company Research API is running"}), 200

@app.route('/research', methods=['POST'])
async def research():
    """Main research endpoint that returns a job ID."""
    try:
        logger.info("Received research request")
        data = request.json
        logger.info(f"Request data: {data}")
        
        if not data or 'company' not in data:
            return jsonify({"error": "Missing company name"}), 400

        # Generate a job ID
        job_id = str(uuid.uuid4())
        
        # Start background task
        asyncio.create_task(process_research(job_id, data))
        
        return jsonify({
            "status": "accepted",
            "job_id": job_id,
            "message": "Research started. Use /research/status/<job_id> to check status.",
            "polling_url": f"/research/status/{job_id}"
        })

    except Exception as e:
        logger.error(f"Error initiating research: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/research/status/<job_id>', methods=['GET'])
async def check_status(job_id):
    """Check the status of a research job."""
    if job_id not in job_status:
        return jsonify({"error": "Job not found"}), 404
        
    status = job_status[job_id]
    return jsonify({
        "status": status["status"],
        "progress": status["progress"],
        "debug_info": status["debug_info"],
        "last_update": status["last_update"],
        "result": status["result"] if status["status"] == "completed" else None,
        "error": status["error"] if status["status"] == "failed" else None
    })

@app.route('/research/pdf/<filename>', methods=['GET'])
async def get_pdf(filename):
    """Download PDF report endpoint."""
    try:
        pdf_path = os.path.join(REPORTS_DIR, filename)
        if not os.path.exists(pdf_path):
            return jsonify({"error": "PDF not found"}), 404
        return send_file(pdf_path, mimetype='application/pdf', as_attachment=True)
    except Exception as e:
        logger.error(f"Error sending PDF: {str(e)}", exc_info=True)
        return jsonify({"error": "Error retrieving PDF"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True) 