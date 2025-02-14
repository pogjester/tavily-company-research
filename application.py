from flask import Flask, request, jsonify
from backend.graph import Graph
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Flask application
application = Flask(__name__)
app = application

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
        async for state in graph.run({}, {}):
            logger.info(f"Received state update: {state.keys()}")
            if messages := state.get('messages', []):
                results.append(messages[-1].content)
                logger.info(f"Added message: {messages[-1].content}")

        logger.info("Research pipeline completed")
        return jsonify({
            "status": "success",
            "results": results,
            "report": state.get('report', '')
        })

    except Exception as e:
        logger.error(f"Error during research: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000) 