from langchain_core.messages import AIMessage
from typing import Dict, Any

from ...classes import ResearchState
from .base import BaseResearcher

class IndustryAnalyzer(BaseResearcher):
    def __init__(self) -> None:
        super().__init__()

    async def analyze(self, state: ResearchState) -> Dict[str, Any]:
        company = state.get('company', 'Unknown Company')
        industry = state.get('industry', 'Unknown Industry')
        msg = [f"🏭 Industry Analyzer analyzing {company} in {industry}"]
        
        # Generate search queries using LLM
        queries = await self.generate_queries(state, """
        Focus on industry analysis such as:
        - Market position and share
        - Competitive landscape
        - Industry trends and challenges
        - Key competitors
        - Regulatory environment
        - Market size and growth
        """)
        
        industry_data = {}
        
        # If we have site_scrape data and company_url, analyze it first
        if site_scrape := state.get('site_scrape'):
            if company_url := state.get('company_url'):
                industry_data[company_url] = {
                    'title': company,
                    'raw_content': site_scrape,
                    'source': 'company_website',
                    'query': 'Company website content'
                }
        
        # Perform additional research with increased search depth
        try:
            # Store documents with their respective queries
            for query in queries:
                documents = await self.search_documents([query], search_depth="advanced")
                if documents:  # Only process if we got results
                    for url, doc in documents.items():
                        doc['query'] = query  # Associate each document with its query
                        industry_data[url] = doc
            
            msg.append(f"\n✓ Found {len(industry_data)} documents")
        except Exception as e:
            msg.append(f"\n⚠️ Error during research: {str(e)}")
        
        # Update state with our findings
        messages = state.get('messages', [])
        messages.append(AIMessage(content="\n".join(msg)))
        state['messages'] = messages
        state['industry_data'] = industry_data
        
        return {
            'message': msg,
            'industry_data': industry_data
        }

    async def run(self, state: ResearchState) -> Dict[str, Any]:
        return await self.analyze(state) 