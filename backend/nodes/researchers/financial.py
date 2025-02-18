from langchain_core.messages import AIMessage
from typing import Dict, Any, List
import logging
import json
import time
from ...classes import ResearchState
from .base import BaseResearcher

logger = logging.getLogger(__name__)

class FinancialAnalyst(BaseResearcher):
    def __init__(self) -> None:
        super().__init__()
        self.analyst_type = "financial_analyst"  # Add this if not present

    async def _send_update(self, message: str, type: str = "status", extra: dict = None):
        payload = {
            "type": type,
            "analyst": self.analyst_type,
            "content": message,
            "timestamp": time.time(),
            **(extra or {})
        }

    async def analyze(self, state: ResearchState) -> Dict[str, Any]:
        company = state.get('company', 'Unknown Company')
        
        await self._send_update(f"Starting financial analysis of {company}", "analysis_start")
        
        try:
            # Generate search queries
            await self._send_update("Generating search queries...", "query_generation")
            queries = await self.generate_queries(
                state,
                """
                Generate queries on the financial aspects of {company}...
                """
            )
            
            await self._send_update(
                f"Generated {len(queries)} search queries", 
                "queries_generated",
                {"queries": queries}
            )

            # Process site scrape data
            financial_data = {}
            if site_scrape := state.get('site_scrape'):
                await self._send_update("Incorporating website scrape data", "data_inclusion")
                company_url = state.get('company_url', 'company-website')
                financial_data[company_url] = {
                    'title': state.get('company', 'Unknown Company'),
                    'raw_content': site_scrape,
                    'query': f'Financial information on {company}'
                }

            # Document processing
            await self._send_update(
                f"Searching with {len(queries)} queries...", 
                "search_start",
                {"query_count": len(queries)}
            )
            
            for query in queries:
                await self._send_update(
                    f"Processing query: {query}", 
                    "query_start",
                    {"query": query}
                )
                
                documents = await self.search_documents([query])
                for url, doc in documents.items():
                    doc['query'] = query
                    financial_data[url] = doc
                    await self._send_update(
                        f"Found document at {url}", 
                        "document_found",
                        {"url": url, "query": query}
                    )

            # Final status update
            completion_msg = f"Completed analysis with {len(financial_data)} documents"
            await self._send_update(completion_msg, "analysis_complete")
            
            # Update state
            messages = state.get('messages', [])
            messages.append(AIMessage(content=completion_msg))
            state['messages'] = messages
            state['financial_data'] = financial_data

            return {
                'message': completion_msg,
                'financial_data': financial_data,
                'analyst_type': self.analyst_type,
                'queries': queries
            }

        except Exception as e:
            error_msg = f"Financial analysis failed: {str(e)}"
            await self._send_update(error_msg, "error", {"error": str(e)})
            raise  # Re-raise to maintain error flow

    async def run(self, state: ResearchState) -> Dict[str, Any]:
        return await self.analyze(state)