from langchain_core.messages import AIMessage
from typing import Dict, Any

from ...classes import ResearchState, InputState
from .base import BaseResearcher

class CompanyAnalyzer(BaseResearcher):
    def __init__(self) -> None:
        super().__init__()

    async def analyze(self, state: ResearchState) -> Dict[str, Any]:
        company = state.get('company', 'Unknown Company')
        msg = f"🏢 Company Analyzer researching {company}'s core business...\n"
        
        # Generate search queries using LLM
        queries = await self.generate_queries(state, """
        Focus on company fundamentals such as:
        - Core products and services
        - Company history and milestones
        - Leadership and management team
        - Business model and strategy
        - Technology and innovation
        - Mission and vision statements
        - Recent innovations and R&D
        - Customer base and target market
        - Geographic presence and expansion
        
        Cover both historical context and current operations.
        """)
        
        company_data = {}
        
        # If we have site_scrape data, analyze it first
        if site_scrape := state.get('site_scrape'):
            msg += "\n📊 Including site scrape data in company analysis..."
            company_data[InputState['company_url']] = {
                'title': InputState['company'],
                'raw_content': site_scrape
            }
        
        # Perform additional research
        try:
            msg += f"\n🔍 Searching for company information using {len(queries)} queries..."
            for query in queries:
                search_results = await self.search_documents(query)
                company_data.update(search_results)
            
            msg += f"\n✅ Found {len(company_data)} relevant company documents"
            msg += f"\n🔍 Used queries: \n" + "\n".join(f"  • {q}" for q in queries)
        except Exception as e:
            error_msg = f"⚠️ Error during company research: {str(e)}"
            print(error_msg)
            msg += f"\n{error_msg}"
        
        # Update state with our findings
        messages = state.get('messages', [])
        messages.append(AIMessage(content=msg))
        state['messages'] = messages
        state['company_data'] = company_data
        
        return {
            'message': msg,
            'company_data': company_data
        }

    async def run(self, state: ResearchState) -> Dict[str, Any]:
        return await self.analyze(state) 