from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph
from typing import Dict, Any, AsyncIterator
import logging

from .classes.state import InputState
from .nodes import GroundingNode
from .nodes.researchers import (FinancialAnalyst, NewsScanner, 
                               IndustryAnalyzer, CompanyAnalyzer)
from .nodes.collector import Collector
from .nodes.curator import Curator
from .nodes.enricher import Enricher
from .nodes.briefing import Briefing
from .nodes.editor import Editor
from .nodes.output import OutputNode

logger = logging.getLogger(__name__)

class Graph:
    def __init__(self, company=None, url=None, hq_location=None, industry=None,
                 websocket_manager=None, job_id=None):
        self.websocket_manager = websocket_manager
        self.job_id = job_id
        
        # Initialize InputState
        self.input_state = InputState(
            company=company,
            company_url=url,
            hq_location=hq_location,
            industry=industry,
            websocket_manager=websocket_manager,
            job_id=job_id,
            messages=[
                SystemMessage(content="Expert researcher starting investigation")
            ]
        )

        # Initialize nodes with WebSocket manager and job ID
        self._init_nodes()
        self._build_workflow()

    def _init_nodes(self):
        """Initialize all workflow nodes"""
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

    def _build_workflow(self):
        """Configure the state graph workflow"""
        self.workflow = StateGraph(InputState)
        
        # Add nodes with their respective processing functions
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

        # Configure workflow edges
        self.workflow.set_entry_point("grounding")
        self.workflow.set_finish_point("output")
        
        research_nodes = [
            "financial_analyst", 
            "news_scanner",
            "industry_analyst", 
            "company_analyst"
        ]

        # Connect grounding to all research nodes
        for node in research_nodes:
            self.workflow.add_edge("grounding", node)
            self.workflow.add_edge(node, "collector")

        # Connect remaining nodes
        self.workflow.add_edge("collector", "curator")
        self.workflow.add_edge("curator", "enricher")
        self.workflow.add_edge("enricher", "briefing")
        self.workflow.add_edge("briefing", "editor")
        self.workflow.add_edge("editor", "output")

    async def run(self, thread: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]:
        """Execute the research workflow"""
        compiled_graph = self.workflow.compile()
        
        async for state in compiled_graph.astream(
            self.input_state,
            thread
        ):
            if self.websocket_manager and self.job_id:
                await self._handle_ws_update(state)
            yield state

    async def _handle_ws_update(self, state: Dict[str, Any]):
        """Handle WebSocket updates based on state changes"""
        update = {
            "type": "state_update",
            "data": {
                "current_node": state.get("current_node", "unknown"),
                "progress": state.get("progress", 0),
                "keys": list(state.keys())
            }
        }
        await self.websocket_manager.broadcast_to_job(
            self.job_id,
            update
        )