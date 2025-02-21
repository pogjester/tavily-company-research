import os
import asyncio
from datetime import datetime
from openai import AsyncOpenAI
from tavily import AsyncTavilyClient
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class BaseResearcher:
    def __init__(self):
        tavily_key = os.getenv("TAVILY_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        
        if not tavily_key or not openai_key:
            raise ValueError("Missing API keys")
            
        self.tavily_client = AsyncTavilyClient(api_key=tavily_key)
        self.openai_client = AsyncOpenAI(api_key=openai_key)
        self.analyst_type = "base_researcher"  # Default type

    @property
    def analyst_type(self) -> str:
        if not hasattr(self, '_analyst_type'):
            raise ValueError("Analyst type not set by subclass")
        return self._analyst_type

    @analyst_type.setter
    def analyst_type(self, value: str):
        self._analyst_type = value

    async def generate_queries(self, state: Dict, prompt: str) -> List[str]:
        company = state.get("company", "Unknown Company")
        industry = state.get("industry", "Unknown Industry")
        hq = state.get("hq", "Unknown HQ")
        current_year = datetime.now().year
        
        try:
            logger.info(f"Generating queries for {company} as {self.analyst_type}")
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "system",
                    "content": f"You are researching {company}, a company in the {industry} industry."
                },
                {
                    "role": "user",
                    "content": f"""Researching {company} on {datetime.now().strftime("%B %d, %Y")}.
{self._format_query_prompt(prompt, company, hq, current_year)}"""
                }],
                temperature=0,
                max_tokens=4096,
                stream=True
            )
            
            queries = []
            current_query = ""
            current_query_number = 1

            async for chunk in response:
                if chunk.choices[0].finish_reason == "stop":
                    break
                    
                content = chunk.choices[0].delta.content
                if content:
                    current_query += content
                    
                    # Send the current state of the query being typed
                    if websocket_manager := state.get('websocket_manager'):
                        if job_id := state.get('job_id'):
                            await websocket_manager.send_status_update(
                                job_id=job_id,
                                status="query_generating",
                                message="Generating research query",
                                result={
                                    "query": current_query,
                                    "query_number": current_query_number,
                                    "category": self.analyst_type,
                                    "is_complete": False
                                }
                            )
                    
                    # If we detect a newline, we've completed a query
                    if '\n' in current_query:
                        parts = current_query.split('\n')
                        # Last part becomes the start of next query
                        current_query = parts[-1]
                        
                        # Add completed queries
                        for query in parts[:-1]:
                            query = query.strip()
                            if query:
                                queries.append(query)
                                # Send completed query
                                if websocket_manager := state.get('websocket_manager'):
                                    if job_id := state.get('job_id'):
                                        await websocket_manager.send_status_update(
                                            job_id=job_id,
                                            status="query_generated",
                                            message="Generated new research query",
                                            result={
                                                "query": query,
                                                "query_number": len(queries),
                                                "category": self.analyst_type,
                                                "is_complete": True
                                            }
                                        )
                                current_query_number += 1

            # Handle final query
            if current_query.strip():
                query = current_query.strip()
                queries.append(query)
                if websocket_manager := state.get('websocket_manager'):
                    if job_id := state.get('job_id'):
                        await websocket_manager.send_status_update(
                            job_id=job_id,
                            status="query_generated",
                            message="Generated new research query",
                            result={
                                "query": query,
                                "query_number": len(queries),
                                "category": self.analyst_type,
                                "is_complete": True
                            }
                        )

            # Add logging
            logger.info(f"Generated {len(queries)} queries for {self.analyst_type}: {queries}")

            if not queries:
                raise ValueError(f"No queries generated for {company}")

            queries = queries[:4]  # Ensure max 4 queries
            
            # Add final logging
            logger.info(f"Final queries for {self.analyst_type}: {queries}")
            
            return queries
            
        except Exception as e:
            logger.error(f"Error generating queries for {company}: {e}")
            if websocket_manager := state.get('websocket_manager'):
                if job_id := state.get('job_id'):
                    await websocket_manager.send_status_update(
                        job_id=job_id,
                        status="error",
                        message=f"Failed to generate research queries: {str(e)}",
                        error=f"Query generation failed: {str(e)}"
                    )
            return []

    def _format_query_prompt(self, prompt, company, hq, year):
        return f"""{prompt}

        Important Guidelines:
        - Focus ONLY on {company}-specific information
        - Make queries very brief and to the point
        - Provide exactly 4 search queries (one per line), with no hyphens or dashes
        - DO NOT make assumptions about the industry - use only the provided industry information"""

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

        try:
            results = await self.tavily_client.search(
                query,
                search_depth="basic",
                include_raw_content=False,
                max_results=15
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

            return docs
            
        except Exception as e:
            logger.error(f"Error searching query '{query}': {e}")
            return {}

    async def search_documents(self, queries: List[str]) -> Dict[str, Any]:
        if not queries:
            logger.error("No valid queries to search")
            return {}

        valid_queries = [q for q in queries if isinstance(q, str) and len(q.split()) >= 3]
        if not valid_queries:
            logger.error("No valid queries after filtering")
            return {}

        try:
            tasks = [self.search_single_query(q) for q in valid_queries]
            results = await asyncio.gather(*tasks)
            
            merged_docs = {}
            for result_dict in results:
                merged_docs.update(result_dict)

            if not merged_docs:
                logger.error("No documents found from any query")
            
            return merged_docs

        except Exception as e:
            logger.error(f"Error during document search: {e}")
            return {}