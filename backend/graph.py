from langchain_core.messages import SystemMessage, AIMessage
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver
from typing import Dict, Any, AsyncIterator

# Import research state class
from .classes.state import ResearchState, InputState, OutputState

# Import node classes
from .nodes import GroundingNode
from .nodes.researchers import (
    FinancialAnalyst,
    NewsScanner,
    IndustryAnalyzer,
    CompanyAnalyzer
)

class Graph:
    def __init__(self, company=None, url=None, hq_location=None, industry=None):
        # Initial setup of ResearchState and messages
        self.messages = [
            SystemMessage(content="You are an expert researcher ready to begin the information gathering process.")
        ]

        #Initialize InputState
        self.input_state = InputState(
            company=company,
            company_url=url,
            hq_location=hq_location,
            industry=industry
        )

        # Initialize all nodes
        self.ground = GroundingNode()
        self.financial_analyst = FinancialAnalyst()
        self.news_scanner = NewsScanner()
        self.industry_analyst = IndustryAnalyzer()
        self.company_analyst = CompanyAnalyzer()

        # Initialize workflow for the graph
        self.workflow = StateGraph(InputState)

        # Add nodes to the workflow
        self.workflow.add_node("grounding", self.ground.run)
        self.workflow.add_node("financial_analyst", self.financial_analyst.run)
        self.workflow.add_node("news_scanner", self.news_scanner.run)
        self.workflow.add_node("industry_analyst", self.industry_analyst.run)
        self.workflow.add_node("company_analyst", self.company_analyst.run)

        # Set up the workflow
        # After grounding, run all research tasks in parallel
        self.workflow.set_entry_point("grounding")
        self.workflow.add_edge("grounding", "financial_analyst")
        self.workflow.add_edge("grounding", "news_scanner")
        self.workflow.add_edge("grounding", "industry_analyst")
        self.workflow.add_edge("grounding", "company_analyst")

        # Add memory saver to the workflow
        self.memory = MemorySaver()

    async def run(self, config: Dict[str, Any], thread: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]:
        """Run the graph with the given configuration.
        
        Args:
            config: Configuration for the graph run
            thread: Thread configuration for state persistence
        
        Yields:
            Dict containing the current state of the graph
        """
        # Update input state with config if provided
        if config:
            self.input_state.update(config)
            
        # Compile the graph
        graph = self.workflow.compile()
        
        # Execute the graph asynchronously
        async for state in graph.astream(self.input_state, thread):
            yield state

    def compile(self):
        """Compile the graph for execution."""
        return self.workflow.compile()
        
        