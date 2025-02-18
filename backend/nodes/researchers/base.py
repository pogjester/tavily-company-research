import os
import asyncio
from datetime import datetime
from openai import AsyncOpenAI
from tavily import AsyncTavilyClient
from typing import Dict, Any, List

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
        self.openai_client = AsyncOpenAI(api_key=openai_key)

    async def generate_queries(self, state: Dict, prompt: str) -> List[str]:
        company = state.get("company", "Unknown Company")
        current_year = datetime.now().year
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": f"""Researching {company} on {datetime.now().strftime("%B %d, %Y")}.
{self._format_query_prompt(prompt, company, current_year)}"""
                }],
                temperature=0,
                max_tokens=4096,
                stream=True
            )
            
            queries = [
                q.strip() 
                for q in response.choices[0].message.content.splitlines() 
                if q.strip()
            ]
            
            await self._send_update(
                f"Generated {len(queries)} queries",
                "query_generation_complete",
                {"queries": queries}
            )
            
            return queries[:4]  # Ensure max 4 queries
            
        except Exception as e:
            return self._fallback_queries(company, current_year)

    def _format_query_prompt(self, prompt, company, year):
        return f"""{prompt}

        Important Guidelines:
        - Focus ONLY on {company}-specific information
        - Include the year {year} in each query
        - Make queries precise and targeted
        - Provide exactly 4 search queries (one per line)"""

    def _fallback_queries(self, company, year):
        return [
            f"{company} overview {year}",
            f"{company} recent news {year}",
            f"{company} financial reports {year}",
            f"{company} industry analysis {year}"
        ]

    async def search_single_query(self, query: str) -> Dict[str, Any]:
        if not query or len(query.split()) < 3:
            return {}

        await self._send_update(
            "Starting web search",
            "search_start",
            {"query": query}
        )

        try:
            results = await self.tavily_client.search(
                query,
                search_depth="advanced",
                include_raw_content=False,
                max_results=5
            )
            
            docs = {}
            for result in results.get("results", []):
                if not result.get("content") or not result.get("url"):
                    continue
                    
                url = result.get("url")
                docs[url] = {
                    "title": result.get("title", ""),
                    "content": result.get("content", ""),
                    "query": query,
                    "url": url,
                    "source": "web_search",
                    "score": result.get("score", 0.0)
                }

            await self._send_update(
                f"Found {len(docs)} documents",
                "search_complete",
                {"query": query, "count": len(docs)}
            )
            
            return docs
            
        except Exception as e:
            await self._send_update(
                "Search failed",
                "search_error",
                {"query": query, "error": str(e)}
            )
            return {}

    async def search_documents(self, queries: List[str]) -> Dict[str, Any]:
        valid_queries = [q for q in queries if isinstance(q, str) and len(q.split()) >= 3]

        tasks = [self.search_single_query(q) for q in valid_queries]
        results = await asyncio.gather(*tasks)
        
        merged_docs = {}
        for result_dict in results:
            merged_docs.update(result_dict)

        return merged_docs

    async def analyze(self, state):
        analyzed = convert_keys_to_str(state)
        return analyzed