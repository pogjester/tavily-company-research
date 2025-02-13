from langchain_core.messages import AIMessage
from typing import Dict, Any

from ...classes import ResearchState, InputState
from .base import BaseResearcher

class IndustryAnalyzer(BaseResearcher):
    def __init__(self) -> None:
        super().__init__()

    async def analyze(self, state: ResearchState) -> Dict[str, Any]:
        company = state.get('company', 'Unknown Company')
        industry = state.get('industry', 'Unknown Industry')
        msg = f"🏭 Industry Analyzer researching {company}'s position in {industry}...\n"
        
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
        
        # If we have site_scrape data, analyze it first
        if site_scrape := state.get('site_scrape'):
            msg += "\n📊 Including site scrape data in company analysis..."
            industry_data[InputState['company_url']] = {
                'title': InputState['company'],
                'raw_content': site_scrape
            }
        
        # Perform additional research
        try:
            msg += f"\n🔍 Searching for industry information using {len(queries)} queries..."
            for query in queries:
                search_results = await self.search_documents(query)
                industry_data.update(search_results)
            
            msg += f"\n✅ Found {len(industry_data)} relevant industry documents"
            msg += f"\n🔍 Used queries: \n" + "\n".join(f"  • {q}" for q in queries)
        except Exception as e:
            error_msg = f"⚠️ Error during industry research: {str(e)}"
            print(error_msg)
            msg += f"\n{error_msg}"
        
        # Update state with our findings
        messages = state.get('messages', [])
        messages.append(AIMessage(content=msg))
        state['messages'] = messages
        state['industry_data'] = industry_data
        
        return {
            'message': msg,
            'industry_data': industry_data
        }

    async def run(self, state: ResearchState) -> Dict[str, Any]:
        return await self.analyze(state) 