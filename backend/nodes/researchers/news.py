from langchain_core.messages import AIMessage

from ...classes import ResearchState
from .base import BaseResearcher

class NewsScanner(BaseResearcher):
    def __init__(self) -> None:
        super().__init__()

    async def analyze(self, state: ResearchState) -> ResearchState:
        company = state.get('company', 'Unknown Company')
        msg = f"📰 News Scanner analyzing recent coverage of {company}...\n"
        
        # Generate search queries using LLM
        queries = await self.generate_queries(state, """
        Focus on news and media coverage such as:
        - General news about the company
        - Major announcements and developments
        - Media coverage and public perception
        - Partnerships or deals
        - Executive interviews and statements
        """)
        
        news_data = {}
        
        # If we have site_scrape data, analyze it first
        if state.get('site_scrape'):
            msg += "\n📊 Analyzing extracted news information..."
            # TODO: Analyze the scraped content for news information
        
        # Perform additional research
        try:
            msg += f"\n🔍 Searching for news coverage using {len(queries)} queries..."
            for query in queries:
                search_results = await self.tavily_client.search(
                    query,
                    search_depth="advanced",
                    sort_by="date"  # Prioritize recent results
                )
                for result in search_results.get('results', []):
                    news_data[result['url']] = {
                        'title': result.get('title'),
                        'content': result.get('content'),
                        'score': result.get('score'),
                        'query': query,
                        'published_date': result.get('published_date')
                    }
            
            msg += f"\n✅ Found {len(news_data)} relevant news articles"
            msg += f"\n🔍 Used queries: \n" + "\n".join(f"  • {q}" for q in queries)
        except Exception as e:
            error_msg = f"⚠️ Error during news research: {str(e)}"
            print(error_msg)
            msg += f"\n{error_msg}"
        
        # Update state with our findings
        messages = state.get('messages', [])
        messages.append(AIMessage(content=msg))
        state['messages'] = messages
        state['news_data'] = news_data
        
        return state

    async def run(self, state: ResearchState) -> ResearchState:
        return await self.analyze(state) 