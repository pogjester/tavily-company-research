from langchain_anthropic import ChatAnthropic
from tavily import AsyncTavilyClient
import os
import json
from typing import List, Dict, Any
from datetime import datetime
import asyncio

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
            
        print(f"\n🔍 Generating queries for {company}...")
            
        response = await self.llm.ainvoke(
            f"""You are conducting research on {context} on {current_date}.
            Generate 4 specific search queries to gather information about the company.
            Focus your queries on recent and current information.
            
            {prompt}
            
            Return ONLY a JSON array of strings, where each string is a search query.
            Include the company name and year in each query.
            Each query must be at least 3 words long.
            
            Example format:
            [
                "Apple revenue growth 2025",
                "Apple market share in smartphone industry 2025",
                "Apple recent product announcements 2025",
                "Apple financial performance Q1 2025"
            ]
            """
        )
        
        # Default queries in case parsing fails
        default_queries = [
            f"{company} overview {datetime.now().year}",
            f"{company} recent news {datetime.now().year}",
            f"{company} {prompt.split()[0]} {datetime.now().year}",
            f"{company} industry analysis {datetime.now().year}"
        ]
        
        try:
            # Extract the JSON array from the response
            content = response.content.strip()
            print(f"\n📝 LLM Response:\n{content}")
            
            if '[' in content and ']' in content:
                start_idx = content.find('[')
                end_idx = content.rfind(']') + 1
                json_str = content[start_idx:end_idx]
                queries = json.loads(json_str)
                
                if isinstance(queries, list) and len(queries) > 0:
                    # Validate each query
                    valid_queries = []
                    for query in queries:
                        if isinstance(query, str) and len(query.split()) >= 3:
                            valid_queries.append(query)
                    
                    if valid_queries:
                        print(f"\n✅ Generated {len(valid_queries)} valid queries:")
                        for q in valid_queries[:4]:
                            print(f"  • {q}")
                        return valid_queries[:4]  # Limit to 4 queries
            
            print("\n⚠️ Failed to parse valid queries from LLM response, using defaults:")
            for q in default_queries:
                print(f"  • {q}")
            return default_queries
            
        except Exception as e:
            print(f"\n❌ Error parsing LLM response: {e}")
            print("Using default queries:")
            for q in default_queries:
                print(f"  • {q}")
            return default_queries

    async def search_single_query(self, query: str, search_depth: str = "advanced") -> Dict[str, Any]:
        """Perform a search for a single query."""
        if not isinstance(query, str) or len(query.split()) < 3:
            print(f"Invalid query format: {query}")
            return {}
            
        try:
            print(f"\nExecuting search for query: {query}")
            search_results = await self.tavily_client.search(
                query,
                search_depth=search_depth,
                include_raw_content=False,
                max_results=5  # Limit results per query for speed
            )
            
            if not search_results.get('results'):
                print("No results returned from search")
                return {}
                
            print(f"Search returned {len(search_results['results'])} results")
            
            results = {}
            for result in search_results.get('results', []):
                # Ensure we have content to evaluate
                content = result.get('content')
                if not content:
                    print(f"Warning: No content in result for {result.get('url')}")
                    continue
                    
                url = result.get('url')
                if not url:
                    print("Warning: Result missing URL")
                    continue
                    
                results[url] = {
                    'title': result.get('title', ''),
                    'content': content,  # This is the summary content for evaluation
                    'score': result.get('score', 0.0),
                    'query': query,
                    'url': url  # Store URL in document for reference
                }
                
                print(f"\nFound document: {result.get('title', 'No title')}")
                print(f"Content length: {len(content)}")
                print(f"Initial relevance: {result.get('score', 0.0)}")
            
            print(f"\nQuery '{query}' returned {len(results)} valid documents with content")
            return results
        except Exception as e:
            print(f"Error searching query '{query}': {e}")
            return {}

    async def search_documents(self, queries: List[str], search_depth: str = "advanced") -> Dict[str, Any]:
        """Perform searches in parallel for multiple queries."""
        if not isinstance(queries, list):
            print(f"Invalid queries format: {queries}")
            return {}
            
        # Filter out invalid queries
        valid_queries = [q for q in queries if isinstance(q, str) and len(q.split()) >= 3]
        if not valid_queries:
            print("No valid queries to search")
            return {}
            
        print(f"\nExecuting {len(valid_queries)} search queries in parallel")
        
        # Run all searches in parallel
        search_tasks = [self.search_single_query(query, search_depth) for query in valid_queries]
        results_list = await asyncio.gather(*search_tasks)
        
        # Merge all results
        merged_results = {}
        total_docs = 0
        for results in results_list:
            merged_results.update(results)
            total_docs += len(results)
        
        print(f"\nTotal documents found across all queries: {total_docs}")
        print(f"Unique documents after merging: {len(merged_results)}")
        
        return merged_results 