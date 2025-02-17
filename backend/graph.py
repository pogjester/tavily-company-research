from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph
from typing import Dict, Any, AsyncIterator

# Import research state class
from .classes.state import ResearchState, InputState

# Import node classes
from .nodes import GroundingNode
from .nodes.researchers import (
    FinancialAnalyst,
    NewsScanner,
    IndustryAnalyzer,
    CompanyAnalyzer
)
from .nodes.collector import Collector
from .nodes.curator import Curator
from .nodes.enricher import Enricher
from .nodes.briefing import Briefing
from .nodes.editor import Editor
from .nodes.output import OutputNode

class Graph:
    def __init__(self, company=None, url=None, hq_location=None, industry=None):
        # Initialize InputState
        self.input_state = ResearchState(
            company=company,
            company_url=url,
            hq_location=hq_location,
            industry=industry,
            messages=[
                SystemMessage(content="You are an expert researcher ready to begin the information gathering process.")
            ]
        )

        # Initialize all nodes
        self.ground = GroundingNode()
        self.financial_analyst = FinancialAnalyst()
        self.news_scanner = NewsScanner()
        self.industry_analyst = IndustryAnalyzer()
        self.company_analyst = CompanyAnalyzer()
        self.collector = Collector()
        self.curator = Curator()
        self.enricher = Enricher()
        self.briefing = Briefing()
        self.editor = Editor()
        self.output = OutputNode()

        # Initialize workflow for the graph
        self.workflow = StateGraph(InputState)

        # Add nodes to the workflow
        self.workflow.add_node("grounding", self.ground.run)
        self.workflow.add_node("financial_analyst", self.financial_analyst.run)
        self.workflow.add_node("news_scanner", self.news_scanner.run)
        self.workflow.add_node("industry_analyst", self.industry_analyst.run)
        self.workflow.add_node("company_analyst", self.company_analyst.run)
        self.workflow.add_node("collector", self.collector.run)
        self.workflow.add_node("curator", self.curator.run)
        self.workflow.add_node("enricher", self.enricher.run)
        self.workflow.add_node("briefing", self.briefing.run)
        self.workflow.add_node("editor", self.editor.run)
        self.workflow.add_node("output", self.output.run)

        # Set up the workflow
        self.workflow.set_entry_point("grounding")
     
        # Define the list of research nodes
        research_nodes = ["financial_analyst", "news_scanner", "industry_analyst", "company_analyst"]

        # After grounding, run all research tasks in parallel
        for node in research_nodes:
            self.workflow.add_edge("grounding", node)
            self.workflow.add_edge(node, "collector")

        # Collector feeds into curator
        self.workflow.add_edge("collector", "curator")
        
        # Curator feeds into enricher
        self.workflow.add_edge("curator", "enricher")
        
        # Enricher feeds into briefing
        self.workflow.add_edge("enricher", "briefing")
        
        # Briefing feeds into editor
        self.workflow.add_edge("briefing", "editor")

        # Editor feeds into output
        self.workflow.add_edge("editor", "output")

    async def run(self, config: Dict[str, Any], thread: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]:
        """Run the graph with the given configuration.
        
        Args:
            config: Configuration for the graph run
            thread: Thread configuration for state persistence
        
        Yields:
            Dict containing the current state of the graph
        """
        # Update state with config if provided
        if config:
            self.input_state.update(config)
            
        # Compile the graph
        graph = self.workflow.compile()
        
        # Track the full state
        full_state = dict(self.input_state)
        
        # Execute the graph asynchronously
        async for state_update in graph.astream(self.input_state, thread):
            # Extract actual data from node outputs
            for node_name, node_data in state_update.items():
                if isinstance(node_data, dict):
                    # Skip the node name and just update with the data
                    full_state.update(node_data)
                else:
                    # If it's not a dict, keep the node name as the key
                    full_state[node_name] = node_data
            yield full_state

    def compile(self):
        """Compile the graph for execution."""
        return self.workflow.compile()
        
        