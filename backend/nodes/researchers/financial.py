from langchain_core.messages import AIMessage
from typing import Dict, Any


from ...classes import ResearchState, InputState
from .base import BaseResearcher

class FinancialAnalyst(BaseResearcher):
    def __init__(self) -> None:
        super().__init__()

    async def analyze(self, state: ResearchState) -> Dict[str, Any]:
        company = state.get('company', 'Unknown Company')
        msg = f"💰 Financial Analyst researching {company}...\n"
        
        # Generate search queries using LLM
        queries = await self.generate_queries(state, """
        Generate queries on the financial aspects of {company} in the {industry} industry such as:
        - Revenue and growth
        - Market valuation
        - Funding rounds
        - Key financial metrics
        - Recent financial news
        - Investor information
        """)
        
        financial_data = {}
        
        # If we have site_scrape data, include it first
        if site_scrape := state.get('site_scrape'):
            msg += "\n📊 Including site scrape data in company analysis..."
            company_url = state.get('company_url', 'company-website')
            financial_data[company_url] = {
                'title': state.get('company', 'Unknown Company'),
                'raw_content': site_scrape,
                'query': f'Financial information on {company}'  # Add a default query for site scrape
            }
        
        # Perform additional research
        try:
            msg += f"\n🔍 Searching for financial information using {len(queries)} queries..."
            # Store documents with their respective queries
            for query in queries:
                documents = await self.search_documents([query])
                for url, doc in documents.items():
                    doc['query'] = query  # Associate each document with its query
                    financial_data[url] = doc
            
            msg += f"\n✅ Found {len(financial_data)} relevant financial documents"
            msg += f"\n🔍 Used queries: \n" + "\n".join(f"  • {q}" for q in queries)
        except Exception as e:
            error_msg = f"⚠️ Error during financial research: {str(e)}"
            print(error_msg)
            msg += f"\n{error_msg}"
        
        # Update state with our findings
        messages = state.get('messages', [])
        messages.append(AIMessage(content=msg))
        state['messages'] = messages
        state['financial_data'] = financial_data
        
        return {
            'message': msg,
            'financial_data': financial_data
        }

    async def run(self, state: ResearchState) -> Dict[str, Any]:
        return await self.analyze(state) 