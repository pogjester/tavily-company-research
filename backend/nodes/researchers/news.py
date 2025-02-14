from langchain_core.messages import AIMessage
from typing import Dict, Any
from ...classes import ResearchState
from .base import BaseResearcher

class NewsScanner(BaseResearcher):
    def __init__(self) -> None:
        super().__init__()

    async def analyze(self, state: ResearchState) -> Dict[str, Any]:
        company = state.get('company', 'Unknown Company')
        msg = [f"📰 News Scanner analyzing {company}"]
        
        # Generate search queries using LLM
        queries = await self.generate_queries(state, """
        Focus on recent news coverage such as:
        - Recent company announcements
        - Press releases
        - Media coverage
        - Company developments
        - Executive changes
        - Strategic initiatives
        """)
        
        news_data = {}
        
        # If we have site_scrape data and company_url, analyze it first
        if site_scrape := state.get('site_scrape'):
            if company_url := state.get('company_url'):
                news_data[company_url] = {
                    'title': company,
                    'raw_content': site_scrape,
                    'source': 'company_website',
                    'query': 'Company website content'
                }
        
        # Perform additional research with recent time filter
        try:
            # Store documents with their respective queries
            for query in queries:
                documents = await self.search_documents([query], search_depth="advanced")
                if documents:  # Only process if we got results
                    for url, doc in documents.items():
                        doc['query'] = query  # Associate each document with its query
                        news_data[url] = doc
            
            msg.append(f"\n✓ Found {len(news_data)} documents")
        except Exception as e:
            msg.append(f"\n⚠️ Error during research: {str(e)}")
        
        # Update state with our findings
        messages = state.get('messages', [])
        messages.append(AIMessage(content="\n".join(msg)))
        state['messages'] = messages
        state['news_data'] = news_data
        
        return {
            'message': msg,
            'news_data': news_data
        }

    async def run(self, state: ResearchState) -> Dict[str, Any]:
        return await self.analyze(state) 