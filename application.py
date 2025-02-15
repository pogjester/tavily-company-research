from flask import Flask, request, jsonify, send_file
from backend.graph import Graph
from backend.utils.utils import generate_pdf_from_md
from dotenv import load_dotenv
import logging
import os
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Flask application
application = Flask(__name__)
app = application

# Create reports directory if it doesn't exist
REPORTS_DIR = "reports"
if not os.path.exists(REPORTS_DIR):
    os.makedirs(REPORTS_DIR)

# Store research results in memory (for demo purposes)
# In production, you would use a proper database
research_cache = {}

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
    """Main research endpoint."""
    try:
        logger.info("Received research request")
        data = request.json
        logger.info(f"Request data: {data}")
        
        if not data or 'company' not in data:
            logger.error("Missing company name in request")
            return jsonify({"error": "Missing company name"}), 400

        # Initialize research graph
        logger.info(f"Initializing research graph for {data.get('company')}")
        graph = Graph(
            company=data.get('company'),
            url=data.get('company_url'),
            industry=data.get('industry'),
            hq_location=data.get('hq_location')
        )

        # Run research pipeline
        logger.info("Starting research pipeline")
        results = []
        final_state = None
        async for state in graph.run({}, {}):
            logger.info(f"Received state update: {state.keys()}")
            if messages := state.get('messages', []):
                results.append(messages[-1].content)
                logger.info(f"Added message: {messages[-1].content}")
            final_state = state

        if not final_state:
            return jsonify({"error": "Research pipeline failed"}), 500

        # Get the report content
        report_content = final_state.get('report', '')
        
        # Debug check for report content
        print("\n\n")
        print("="*100)
        print(f"📊 COMPLETE RESEARCH REPORT FOR {data['company'].upper()}")
        print("="*100)
        print("\n")
        
        if not report_content or not report_content.strip():
            logger.error("❌ Report content is empty or whitespace only!")
            logger.error("Final state keys available:", list(final_state.keys()))
            return jsonify({"error": "No report content generated"}), 500
            
        print(report_content)
        print("\n")
        print("="*100)
        print("END OF REPORT")
        print("="*100)
        print("\n\n")
        
        # Also log individual sections for debugging
        logger.info("\nDETAILED SECTION BREAKDOWN:")
        sections_found = []
        for section in ['Company Overview', 'Industry Analysis', 'Financial Analysis', 'Recent Developments', 'References']:
            start_idx = report_content.find(section)
            if start_idx != -1:
                sections_found.append(section)
                next_section_idx = float('inf')
                for next_section in ['Company Overview', 'Industry Analysis', 'Financial Analysis', 'Recent Developments', 'References']:
                    if next_section != section:
                        idx = report_content.find(next_section, start_idx + len(section))
                        if idx != -1 and idx < next_section_idx:
                            next_section_idx = idx
                
                section_content = report_content[start_idx:next_section_idx if next_section_idx != float('inf') else None]
                logger.info("\n" + "-"*50)
                logger.info(f"SECTION: {section}")
                logger.info("-"*50)
                logger.info(section_content.strip())
        
        logger.info("\nSections found in report: " + ", ".join(sections_found))
        logger.info(f"Total report length: {len(report_content)} characters")

        # Generate PDF from the report
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        pdf_filename = f"{data['company'].replace(' ', '_')}_{timestamp}.pdf"
        pdf_path = os.path.join(REPORTS_DIR, pdf_filename)
        
        try:
            # Debug log the content being sent to PDF generator
            logger.info(f"Generating PDF with content length: {len(report_content)} characters")
            logger.info("First 500 characters of report:")
            logger.info("-" * 50)
            logger.info(report_content[:500])
            logger.info("-" * 50)
            
            generate_pdf_from_md(report_content, pdf_path)
            logger.info(f"Generated PDF report at {pdf_path}")
            
            # Verify PDF was created and has content
            if os.path.exists(pdf_path):
                pdf_size = os.path.getsize(pdf_path)
                logger.info(f"PDF file size: {pdf_size} bytes")
                if pdf_size == 0:
                    logger.error("PDF file was created but is empty")
            else:
                logger.error("PDF file was not created")
        except Exception as e:
            logger.error(f"Error generating PDF: {str(e)}", exc_info=True)
            # Continue without PDF if generation fails
            pdf_path = None

        # Store research results in cache
        research_cache[data['company']] = {
            'results': results,
            'report': report_content,
            'briefings': final_state.get('briefings', {}),
            'references': final_state.get('references', {}),
            'pdf_path': pdf_path
        }

        response_data = {
            "status": "success",
            "results": results,
            "report": report_content
        }

        # Add PDF download URL if available
        if pdf_path:
            response_data["pdf_url"] = f"/research/pdf/{pdf_filename}"

        logger.info("Research pipeline completed")
        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error during research: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

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