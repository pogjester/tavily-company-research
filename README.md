# Tavily Company Research Platform 🔍

An advanced, AI-powered research platform that automatically generates comprehensive company reports by analyzing multiple data sources. The platform uses a sophisticated pipeline of AI agents to gather, curate, and synthesize information about any company.

## Features ✨

- **Multi-Source Research**: Gathers data from various sources including company websites, news articles, financial reports, and industry analyses
- **Parallel Processing**: Utilizes async operations for efficient data gathering and processing
- **Intelligent Curation**: Uses Cohere's reranking to identify the most relevant information
- **Smart Summarization**: Leverages GPT-4 and Claude to create concise, well-organized briefings
- **Automated Report Generation**: Produces professional PDF reports with consistent formatting
- **Modular Architecture**: Built using LangGraph for flexible, maintainable agent workflows

## Architecture 🏗️

The platform follows a modular architecture with specialized nodes:

1. **Research Nodes**:

   - `FinancialAnalyst`: Gathers financial metrics and performance data
   - `NewsScanner`: Collects recent news and developments
   - `IndustryAnalyzer`: Analyzes market position and industry trends
   - `CompanyAnalyzer`: Researches core business information

2. **Processing Nodes**:
   - `Collector`: Aggregates research data
   - `Curator`: Evaluates and filters relevant information
   - `Briefing`: Generates category-specific summaries
   - `Editor`: Compiles the final report

## Setup 🚀

### Prerequisites

- Python 3.11+
- [Pandoc](https://pandoc.org/installing.html) for PDF generation

### Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/tavily-company-research.git
cd tavily-company-research
```

2. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your API keys:

```env
TAVILY_API_KEY=your_tavily_key
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
COHERE_API_KEY=your_cohere_key
```

## Usage 💡

### Basic Usage

```python
from backend.graph import Graph

# Initialize the research graph
graph = Graph(
    company="Example Corp",
    url="https://example.com",
    industry="Technology",
    hq_location="San Francisco, CA"
)

# Run the research pipeline
async for state in graph.run({}, {}):
    print(state.get('messages', [])[-1].content)
```

### Running in LangGraph Studio 🎮

The project includes LangGraph Studio configuration for easy visualization and debugging of the research pipeline.

1. Install LangGraph Studio:

```bash
pip install langgraph[studio]
```

2. Start the Studio server:

```bash
langgraph studio start
```

3. The project's `langgraph.json` configuration will automatically be detected, allowing you to:

   - Visualize the entire research pipeline
   - Monitor node execution in real-time
   - Debug individual node outputs
   - Track API calls and performance
   - View the complete state flow

4. Access the Studio interface at `http://localhost:8000` in your browser

5. Run your graph with tracing enabled:

```python
from backend.graph import Graph
import os

os.environ["LANGGRAPH_STUDIO_API_KEY"] = "your-studio-key"  # Optional for private instances

graph = Graph(
    company="Example Corp",
    url="https://example.com",
    industry="Technology",
    hq_location="San Francisco, CA"
)

# Enable tracing when running
async for state in graph.run({}, {"trace": True}):
    print(state.get('messages', [])[-1].content)
```

The Studio interface will show:

- A visual DAG of the research pipeline
- Real-time execution progress
- Node-specific metrics and outputs
- Complete state transitions
- API usage statistics

### Configuration Options

- `company`: Company name (required)
- `company_url`: Company website URL (optional)
- `industry`: Industry sector (optional)
- `hq_location`: Company headquarters location (optional)

## Output Format 📄

The platform generates a structured report with sections:

- 🏢 Company Overview
- 🏭 Industry Analysis
- 💰 Financial Analysis
- 📰 Recent Developments

Reports are available in both Markdown and PDF formats, with automatic formatting and styling.

## API Integration 🔌

The platform integrates with several AI and research APIs:

- **Tavily**: Web search and content extraction
- **Anthropic Claude**: Query generation and analysis
- **OpenAI GPT-4**: Report compilation and editing
- **Cohere**: Content relevance ranking

## Contributing 🤝

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Add docstrings for all functions and classes
- Write unit tests for new features
- Update documentation as needed

## Performance Optimization 🚄

The platform includes several optimizations:

- Parallel execution of research tasks
- Batched API requests
- Efficient content curation before full extraction
- Memory-optimized data processing

## License 📝

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments 🙏

- [LangGraph](https://github.com/langchain-ai/langgraph) for the agent framework
- [Tavily](https://tavily.com/) for the research API
- All other open-source libraries and their contributors
