from langchain_core.messages import AIMessage
from langchain_anthropic import ChatAnthropic
from tavily import AsyncTavilyClient
import os
import json
from typing import List, Dict, Any
from datetime import datetime

from ...classes import ResearchState

class BaseResearcher:
    def __init__(self) -> None:
        tavily_key = os.getenv("TAVILY_API_KEY")
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if not tavily_key:
            raise ValueError("TAVILY_API_KEY environment variable is not set")
        if not anthropic_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
            
        self.tavily_client = AsyncTavilyClient(api_key=tavily_key)
        self.llm = ChatAnthropic(
            model_name="claude-3-5-haiku-20241022",
            temperature=0
        )
    
    async def generate_queries(self, state: ResearchState, prompt: str) -> List[str]:
        """Generate search queries using the LLM based on available information."""
        company = state.get('company', 'Unknown Company')
        industry = state.get('industry', '')
        hq = state.get('hq_location', '')
        current_date = datetime.now().strftime("%B %d, %Y")
        
        context = f"Company: {company}"
        if industry:
            context += f"\nIndustry: {industry}"
        if hq:
            context += f"\nHeadquarters: {hq}"
            
        response = await self.llm.ainvoke(
            f"""You are conducting research on {context} on {current_date}.
            
            Generate 4-6 specific search queries to gather information about the company.
            Focus your queries on recent and current information.
            
            {prompt}
            
            Return ONLY a JSON array of strings, where each string is a search query.
            Make queries specific and targeted to get high-quality results.
            Include the company name in most queries.
            Include the current year {datetime.now().year} in queries where relevant.
            
            Example format:
            [
                "Company X revenue growth",
                "Company X market share in Industry Y",
                "Company X recent announcements"
            ]
            """
        )
        
        try:
            # Extract the JSON array from the response
            # First, find anything that looks like a JSON array
            content = response.content
            start_idx = content.find('[')
            end_idx = content.rfind(']') + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                queries = json.loads(json_str)
                if queries and isinstance(queries, list):
                    return queries
            
            # Fallback: if we can't parse JSON, look for line items
            queries = [
                q.strip('- "\'') for q in response.content.split('\n')
                if q.strip('- "\'')
            ]
            return queries[:6]  # Limit to 6 queries
        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            # Fallback to basic queries if everything fails
            return [
                f"{company} overview {datetime.now().year}",
                f"{company} recent news {datetime.now().year}",
                f"{company} {prompt.split()[0]} {datetime.now().year}"
            ] 

    async def search_documents(self, query: str, search_depth: str = "advanced") -> Dict[str, Any]:
        """Perform a search and return results without raw content."""
        search_results = await self.tavily_client.search(
            query,
            search_depth=search_depth
        )
        
        results = {}
        for result in search_results.get('results', []):
            results[result['url']] = {
                'title': result.get('title'),
                'content': result.get('content'),  # This is the summary content
                'score': result.get('score'),
                'query': query
            }
        return results 