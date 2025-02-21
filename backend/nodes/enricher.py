from langchain_core.messages import AIMessage
from typing import Dict, List
import os
from tavily import AsyncTavilyClient
import asyncio
from ..classes import ResearchState

class Enricher:
    """Enriches curated documents with raw content."""
    
    def __init__(self) -> None:
        tavily_key = os.getenv("TAVILY_API_KEY")
        if not tavily_key:
            raise ValueError("TAVILY_API_KEY environment variable is not set")
        self.tavily_client = AsyncTavilyClient(api_key=tavily_key)
        self.batch_size = 20

    async def fetch_single_content(self, url: str) -> Dict[str, str]:
        """Fetch raw content for a single URL."""
        try:
            result = await self.tavily_client.extract(url)
            if result and result.get('results'):
                return {url: result['results'][0].get('raw_content', '')}
        except Exception as e:
            print(f"Error fetching raw content for {url}: {e}")
        return {url: ''}

    async def fetch_raw_content(self, urls: List[str]) -> Dict[str, str]:
        """Fetch raw content for multiple URLs in parallel."""
        raw_contents = {}
        for i in range(0, len(urls), self.batch_size):
            batch_urls = urls[i:i + self.batch_size]
            tasks = [self.fetch_single_content(url) for url in batch_urls]
            results = await asyncio.gather(*tasks)
            for result in results:
                raw_contents.update(result)
        return raw_contents

    async def enrich_data(self, state: ResearchState) -> ResearchState:
        """Enrich curated documents with raw content."""
        company = state.get('company', 'Unknown Company')
        msg = [f"📚 Enriching curated data for {company}:"]

        # Process each type of curated data
        data_types = {
            'financial_data': '💰 Financial',
            'news_data': '📰 News',
            'industry_data': '🏭 Industry',
            'company_data': '🏢 Company'
        }

        for data_field, label in data_types.items():
            curated_field = f'curated_{data_field}'
            curated_docs = state.get(curated_field, {})
            
            if not curated_docs:
                msg.append(f"\n• No curated {label} documents to enrich")
                continue

            # Find documents needing enrichment
            docs_needing_content = {url: doc for url, doc in curated_docs.items() 
                                  if not doc.get('raw_content')}
            
            if not docs_needing_content:
                msg.append(f"\n• All {label} documents already have raw content")
                continue
            
            msg.append(f"\n• Enriching {len(docs_needing_content)} {label} documents...")
            
            # Fetch raw content for documents
            raw_contents = await self.fetch_raw_content(list(docs_needing_content.keys()))
            
            # Update documents with raw content
            enriched_count = 0
            for url, raw_content in raw_contents.items():
                if raw_content:
                    curated_docs[url]['raw_content'] = raw_content
                    enriched_count += 1
            
            # Update state with enriched documents
            state[curated_field] = curated_docs
            msg.append(f"  ✓ Successfully enriched {enriched_count}/{len(docs_needing_content)} documents")

        # Update state with enrichment message
        messages = state.get('messages', [])
        messages.append(AIMessage(content="\n".join(msg)))
        state['messages'] = messages

        if websocket_manager := state.get('websocket_manager'):
            if job_id := state.get('job_id'):
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="processing",
                    message="Extracting raw content from URLs using Tavily Extract",
                    result={"step": "Enriching"}
                )

        return state

    async def run(self, state: ResearchState) -> ResearchState:
        return await self.enrich_data(state) 