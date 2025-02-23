# Tavily Company Research Platform 🔍

An advanced, AI-powered research platform that automatically generates comprehensive company reports by analyzing multiple data sources. The platform uses a sophisticated pipeline of AI agents to gather, curate, and synthesize information about any company.

## Features ✨

- **Multi-Source Research**: Gathers data from various sources including company websites, news articles, financial reports, and industry analyses
- **AI-Powered Content Filtering**: Uses Tavily's relevance scoring for precise content curation
- **Real-Time Progress Streaming**: Uses WebSocket connections to stream research progress and results
- **Dual Model Architecture**: 
  - Gemini 2.0 Flash for high-context research synthesis
  - GPT-4 Optimized for precise report formatting and editing
- **Modern React Frontend**: Beautiful, responsive UI with real-time updates and progress tracking
- **Modular Architecture**: Built using a pipeline of specialized research and processing nodes

## Technical Architecture 🏗️

### Research Pipeline

The platform follows a modular architecture with specialized nodes that process data sequentially:

1. **Research Nodes**:
   - `CompanyAnalyzer`: Researches core business information
   - `IndustryAnalyzer`: Analyzes market position and trends
   - `FinancialAnalyst`: Gathers financial metrics and performance data
   - `NewsScanner`: Collects recent news and developments

2. **Processing Nodes**:
   - `Collector`: Aggregates research data from all analyzers
   - `Curator`: Implements content filtering and relevance scoring
   - `Briefing`: Generates category-specific summaries using Gemini 2.0 Flash
   - `Editor`: Compiles and formats the final report using GPT-4

### Content Generation Architecture 🤖

The platform leverages a dual-model approach for optimal performance:

1. **Gemini 2.0 Flash** (`briefing.py`):
   - Handles high-context research synthesis tasks
   - Excels at processing and summarizing large volumes of data
   - Used for generating initial category briefings
   - Efficient at maintaining context across multiple documents

2. **GPT-4 Optimized** (`editor.py`):
   - Specializes in precise formatting and editing tasks
   - Handles markdown structure and consistency
   - Superior at following exact formatting instructions
   - Used for:
     - Final report compilation
     - Content deduplication
     - Markdown formatting
     - Real-time report streaming

This dual-model approach combines Gemini's strength in handling large context windows with GPT-4's precision in following specific formatting instructions.

### Content Curation System 🎯

The platform implements a sophisticated content filtering system in `curator.py`:

1. **Relevance Scoring**:
   - Documents are scored by Tavily's AI-powered search
   - A minimum threshold of 0.4 is required to proceed
   - Scores reflect relevance to the specific research query
   - Higher scores indicate better matches to the research intent

2. **Document Processing**:
   - Content is normalized and cleaned
   - URLs are deduplicated and standardized
   - Documents are sorted by relevance scores
   - Real-time progress updates are sent via WebSocket

### Real-Time Communication System 📡

The platform implements a WebSocket-based real-time communication system:

1. **Backend Implementation**:
   - Uses FastAPI's WebSocket support
   - Maintains persistent connections per research job
   - Sends structured status updates for various events:
     ```python
     await websocket_manager.send_status_update(
         job_id=job_id,
         status="processing",
         message=f"Generating {category} briefing",
         result={
             "step": "Briefing",
             "category": category,
             "total_docs": len(docs)
         }
     )
     ```

2. **Frontend Integration**:
   - React components subscribe to WebSocket updates
   - Updates are processed and displayed in real-time
   - Different UI components handle specific update types:
     - Query generation progress
     - Document curation statistics
     - Briefing completion status
     - Report generation progress

3. **Status Types**:
   - `query_generating`: Real-time query creation updates
   - `document_kept`: Document curation progress
   - `briefing_start/complete`: Briefing generation status
   - `report_chunk`: Streaming report generation
   - `curation_complete`: Final document statistics

## Setup 🚀

### Prerequisites

- Python 3.11+
- Node.js 18+
- API Keys:
  - Tavily API Key
  - Google Gemini API Key
  - OpenAI API Key (for GPT-4)
- Optional:
  - MongoDB URI (for result persistence)

### Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/tavily-company-research.git
cd tavily-company-research
```

2. Install backend dependencies:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

3. Install frontend dependencies:

```bash
cd simple-frontend
npm install
```

4. Create a `.env` file with your API keys:

```env
TAVILY_API_KEY=your_tavily_key
GEMINI_API_KEY=your_gemini_key
OPENAI_API_KEY=your_openai_key

# Optional: Enable MongoDB persistence
# MONGODB_URI=your_mongodb_connection_string
```

### Database Configuration (Optional)

The platform can optionally use MongoDB to persist research results and reports:

1. **Without MongoDB**: 
   - The application runs in-memory only
   - Research results are available only during the session
   - Historical reports cannot be retrieved after server restart

2. **With MongoDB**:
   - Set `MONGODB_URI` in your `.env` file
   - Research results and reports are persisted
   - Historical reports can be retrieved via API endpoints:
     - GET `/research/{job_id}`: Retrieve job details
     - GET `/research/{job_id}/report`: Retrieve report content

To set up MongoDB:
1. Create a MongoDB database (local or cloud)
2. Get your connection string
3. Add to `.env`: `MONGODB_URI=your_connection_string`

## Usage 💡

### Local Development

1. Start the backend server (choose one option):

   **Option 1: Direct Python Module**
   ```bash
   python -m backend.main
   ```

   **Option 2: FastAPI with Uvicorn**
   ```bash
   # Install uvicorn if not already installed
   pip install uvicorn

   # Run the FastAPI application with hot reload
   uvicorn backend.application:app --reload --port 8000
   ```

   The backend will be available at:
   - API Endpoint: `http://localhost:8000`
   - API Documentation: `http://localhost:8000/docs`
   - WebSocket Endpoint: `ws://localhost:8000/research/ws/{job_id}`

2. Start the frontend development server:
   ```bash
   cd simple-frontend
   npm run dev
   ```

3. Access the application at `http://localhost:5173`

### Deployment Options 🚀

The application can be deployed to various cloud platforms. Here are some common options:

#### AWS Elastic Beanstalk

1. Install the EB CLI:
   ```bash
   pip install awsebcli
   ```

2. Initialize EB application:
   ```bash
   eb init -p python-3.11 tavily-research
   ```

3. Create and deploy:
   ```bash
   eb create tavily-research-prod
   ```

#### Other Deployment Options

- **Docker**: The application includes a Dockerfile for containerized deployment
- **Heroku**: Deploy directly from GitHub with the Python buildpack
- **Google Cloud Run**: Suitable for containerized deployment with automatic scaling
- **DigitalOcean App Platform**: Simple deployment with GitHub integration

Choose the platform that best suits your needs. The application is platform-agnostic and can be hosted anywhere that supports Python web applications.

## Contributing 🤝

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License 📝

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments 🙏

- [Tavily](https://tavily.com/) for the research API
- [Google Gemini](https://cloud.google.com/vertex-ai/docs/generative-ai/model-reference/gemini) for the text generation model
- All other open-source libraries and their contributors
