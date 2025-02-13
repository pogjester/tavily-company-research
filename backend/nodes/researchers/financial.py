from langchain_core.messages import AIMessage
from tavily import AsyncTavilyClient
import os

from ...classes import ResearchState
from .base import BaseResearcher

class FinancialAnalyst(BaseResearcher):
    def __init__(self) -> None:
        super().__init__()

    async def analyze(self, state: ResearchState) -> ResearchState:
        company = state.get('company', 'Unknown Company')
        msg = f"💰 Financial Analyst researching {company}...\n"
        
        # Generate search queries using LLM
        queries = await self.generate_queries(state, """
        Focus on financial aspects such as:
        - Revenue and growth
        - Market valuation
        - Funding rounds
        - Key financial metrics
        - Recent financial news
        - Investor information
        """)
        
        financial_data = {}
        
        # If we have site_scrape data, analyze it first
        if state.get('site_scrape'):
            msg += "\n📊 Analyzing extracted financial information..."
            # TODO: Analyze the scraped content for financial information
        
        # Perform additional research
        try:
            msg += f"\n🔍 Searching for financial information using {len(queries)} queries..."
            for query in queries:
                search_results = await self.tavily_client.search(query)
                for result in search_results.get("results", []):
                    url = result.get("url")
                    if url not in financial_data:
                        financial_data[url] = result
            
            msg += f"\n✅ Found {len(financial_data)} relevant financial documents"
            msg += f"\n🔍 Used queries: \n" + "\n".join(f"  • {q}" for q in queries)
        except Exception as e:
            error_msg = f"⚠️ Error during financial research: {str(e)}"
            print(error_msg)
            msg += f"\n{error_msg}"
        
        # Update state with our findings
        messages = state.get('messages', [])
        messages.append(AIMessage(content="\n".join(msg)))
        state['messages'] = messages
        state['financial_data'] = financial_data
        
        return state

    async def run(self, state: ResearchState) -> ResearchState:
        return await self.analyze(state) 