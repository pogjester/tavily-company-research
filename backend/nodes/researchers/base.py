import os
import asyncio
from datetime import datetime
from langchain_openai import ChatOpenAI
from tavily import AsyncTavilyClient

def convert_keys_to_str(data):
    if isinstance(data, dict):
        return {str(k): convert_keys_to_str(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_keys_to_str(item) for item in data]
    else:
        return data

class BaseResearcher:
    def __init__(self):
        tavily_key = os.getenv("TAVILY_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        if not tavily_key or not openai_key:
            raise ValueError("Missing API keys")
        self.tavily_client = AsyncTavilyClient(api_key=tavily_key)
        self.llm = ChatOpenAI(
            model_name="gpt-4o-mini",
            temperature=0,
            max_tokens=4096,
            api_key=openai_key
        )

    async def generate_queries(self, state, prompt):
        company = state.get("company", "Unknown Company")
        current_year = datetime.now().year
        
        messages = [
            {
                "role": "user",
                "content": f"""Researching {company} on {datetime.now().strftime("%B %d, %Y")}.
{prompt}
Provide exactly 4 search queries (one per line) that include the company name and {current_year}. 
Each query should be specific and focused on gathering relevant information.
Do not number the queries or add any extra text - just output exactly 4 lines."""
            }
        ]
        
        try:
            response = await self.llm.ainvoke(messages)
            # Extract content from OpenAI response and split into lines
            queries = [q.strip() for q in response.content.splitlines() if q.strip()]
            
            # Validate we got exactly 4 queries, otherwise use defaults
            if len(queries) == 4:
                return queries
                
        except Exception as e:
            print(f"Error generating queries: {e}")
            
        # Fallback queries if we didn't get exactly 4 valid queries
        return [
            f"{company} overview {current_year}",
            f"{company} recent news {current_year}",
            f"{company} {prompt.split()[0]} {current_year}",
            f"{company} industry analysis {current_year}"
        ]

    async def search_single_query(self, query, search_depth="advanced"):
        if not query or len(query.split()) < 3:
            return {}  # Return empty dict instead of empty list for invalid queries
        results = await self.tavily_client.search(
            query,
            search_depth=search_depth,
            include_raw_content=False,
            max_results=5
        )
        docs = {}  # Changed from list to dictionary
        for result in results.get("results", []):
            if not result.get("content") or not result.get("url"):
                continue
            url = result.get("url")
            docs[url] = {  # Use URL as key
                "title": result.get("title", ""),
                "content": result.get("content", ""),
                "query": query,
                "url": url,
                "source": "web_search",
                "score": result.get("score", 0.0)
            }
        return docs

    async def search_documents(self, queries, search_depth="advanced"):
        tasks = [
            self.search_single_query(q, search_depth)
            for q in queries if isinstance(q, str) and len(q.split()) >= 3
        ]
        results = await asyncio.gather(*tasks)
        # Merge all dictionaries into one
        merged_docs = {}
        for result_dict in results:
            merged_docs.update(result_dict)
        return merged_docs

    async def analyze(self, state):
        # Convert all keys in state to strings recursively
        return convert_keys_to_str(state)