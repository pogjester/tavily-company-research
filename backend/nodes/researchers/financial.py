from langchain_core.messages import AIMessage
from typing import Dict, Any
import logging
from ...classes import ResearchState
from .base import BaseResearcher

logger = logging.getLogger(__name__)

class FinancialAnalyst(BaseResearcher):
    def __init__(self) -> None:
        super().__init__()
        self.analyst_type = "financial_analyzer"

    async def analyze(self, state: ResearchState) -> Dict[str, Any]:
        company = state.get('company', 'Unknown Company')
        websocket_manager = state.get('websocket_manager')
        job_id = state.get('job_id')
        
        try:
            # Generate search queries
            queries = await self.generate_queries(
                state,
                """
                 Generate queries on the financial analysis of {company} in the {industry} industry such as:
        - Fundraising history and valuation
        - Financial statements and key metrics
        - Revenue and profit sources
        """)
            
            # Add message to show subqueries with emojis
            subqueries_msg = "🔍 Subqueries for financial analysis:\n" + "\n".join([f"• {query}" for query in queries])
            messages = state.get('messages', [])
            messages.append(AIMessage(content=subqueries_msg))
            state['messages'] = messages

            # Send queries through WebSocket
            if websocket_manager:
                if job_id:
                    await websocket_manager.send_status_update(
                        job_id=job_id,
                        status="processing",
                        message=f"Financial analysis queries generated",
                        result={
                            "step": "Financial Analyst",
                            "analyst_type": "Financial Analyst",
                            "queries": queries
                        }
                    )
            
            # Process site scrape data
            financial_data = {}
            if site_scrape := state.get('site_scrape'):
                company_url = state.get('company_url', 'company-website')
                financial_data[company_url] = {
                    'title': state.get('company', 'Unknown Company'),
                    'raw_content': site_scrape,
                    'query': f'Financial information on {company}'
                }

            for query in queries:
                documents = await self.search_documents(state, [query])
                for url, doc in documents.items():
                    doc['query'] = query
                    financial_data[url] = doc

            # Final status update
            completion_msg = f"Completed analysis with {len(financial_data)} documents"
            
            if websocket_manager:
                if job_id:
                    await websocket_manager.send_status_update(
                        job_id=job_id,
                        status="processing",
                        message=f"Used Tavily Search to find {len(financial_data)} documents",
                        result={
                            "step": "Search",
                            "analyst_type": "Financial Analyst",
                            "queries": queries
                        }
                    )
            
            # Update state
            messages.append(AIMessage(content=completion_msg))
            state['messages'] = messages
            state['financial_data'] = financial_data

            # Send completion status with final queries
            if websocket_manager and job_id:
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="processing",
                    message=completion_msg,
                    result={
                        "analyst_type": "Financial Analyst",
                        "queries": queries,
                        "documents_found": len(financial_data)
                    }
                )

            return {
                'message': completion_msg,
                'financial_data': financial_data,
                'analyst_type': self.analyst_type,
                'queries': queries
            }

        except Exception as e:
            error_msg = f"Financial analysis failed: {str(e)}"
            # Send error status
            if websocket_manager:
                if job_id:
                    await websocket_manager.send_status_update(
                        job_id=job_id,
                        status="error",
                        message=error_msg,
                        result={
                            "analyst_type": "Financial Analyst",
                            "error": str(e)
                        }
                    )
            raise  # Re-raise to maintain error flow

    async def run(self, state: ResearchState) -> Dict[str, Any]:
        return await self.analyze(state)