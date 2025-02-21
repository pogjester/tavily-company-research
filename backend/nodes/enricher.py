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

    async def fetch_single_content(self, url: str, websocket_manager=None, job_id=None) -> Dict[str, str]:
        """Fetch raw content for a single URL."""
        try:
            if websocket_manager and job_id:
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="extracting",
                    message=f"Extracting content from {url}",
                    result={
                        "step": "Enriching",
                        "url": url
                    }
                )

            result = await self.tavily_client.extract(url)
            if result and result.get('results'):
                if websocket_manager and job_id:
                    await websocket_manager.send_status_update(
                        job_id=job_id,
                        status="extracted",
                        message=f"Successfully extracted content from {url}",
                        result={
                            "step": "Enriching",
                            "url": url,
                            "success": True
                        }
                    )
                return {url: result['results'][0].get('raw_content', '')}
        except Exception as e:
            print(f"Error fetching raw content for {url}: {e}")
            if websocket_manager and job_id:
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="extraction_error",
                    message=f"Failed to extract content from {url}: {str(e)}",
                    result={
                        "step": "Enriching",
                        "url": url,
                        "success": False,
                        "error": str(e)
                    }
                )
        return {url: ''}

    async def fetch_raw_content(self, urls: List[str], websocket_manager=None, job_id=None) -> Dict[str, str]:
        """Fetch raw content for multiple URLs in parallel."""
        raw_contents = {}
        total_batches = (len(urls) + self.batch_size - 1) // self.batch_size

        for batch_num, i in enumerate(range(0, len(urls), self.batch_size), 1):
            if websocket_manager and job_id:
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="batch_start",
                    message=f"Processing batch {batch_num}/{total_batches}",
                    result={
                        "step": "Enriching",
                        "batch": batch_num,
                        "total_batches": total_batches
                    }
                )

            batch_urls = urls[i:i + self.batch_size]
            tasks = [self.fetch_single_content(url, websocket_manager, job_id) for url in batch_urls]
            results = await asyncio.gather(*tasks)
            for result in results:
                raw_contents.update(result)

        return raw_contents

    async def enrich_data(self, state: ResearchState) -> ResearchState:
        """Enrich curated documents with raw content."""
        company = state.get('company', 'Unknown Company')
        websocket_manager = state.get('websocket_manager')
        job_id = state.get('job_id')

        if websocket_manager and job_id:
            await websocket_manager.send_status_update(
                job_id=job_id,
                status="processing",
                message=f"Starting content enrichment for {company}",
                result={
                    "step": "Enriching",
                    "substep": "initialization"
                }
            )

        msg = [f"📚 Enriching curated data for {company}:"]

        # Process each type of curated data
        data_types = {
            'financial_data': '💰 Financial',
            'news_data': '📰 News',
            'industry_data': '🏭 Industry',
            'company_data': '🏢 Company'
        }

        total_enriched = 0
        total_documents = 0

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
            
            total_documents += len(docs_needing_content)
            msg.append(f"\n• Enriching {len(docs_needing_content)} {label} documents...")

            if websocket_manager and job_id:
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="category_start",
                    message=f"Processing {label} documents",
                    result={
                        "step": "Enriching",
                        "category": data_field,
                        "count": len(docs_needing_content)
                    }
                )
            
            # Fetch raw content for documents
            raw_contents = await self.fetch_raw_content(
                list(docs_needing_content.keys()),
                websocket_manager,
                job_id
            )
            
            # Update documents with raw content
            enriched_count = 0
            for url, raw_content in raw_contents.items():
                if raw_content:
                    curated_docs[url]['raw_content'] = raw_content
                    enriched_count += 1
            
            total_enriched += enriched_count
            
            # Update state with enriched documents
            state[curated_field] = curated_docs
            msg.append(f"  ✓ Successfully enriched {enriched_count}/{len(docs_needing_content)} documents")

            if websocket_manager and job_id:
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="category_complete",
                    message=f"Completed {label} documents",
                    result={
                        "step": "Enriching",
                        "category": data_field,
                        "enriched": enriched_count,
                        "total": len(docs_needing_content)
                    }
                )

        # Send final status update
        if websocket_manager and job_id:
            await websocket_manager.send_status_update(
                job_id=job_id,
                status="enrichment_complete",
                message=f"Content enrichment complete. Successfully enriched {total_enriched}/{total_documents} documents",
                result={
                    "step": "Enriching",
                    "total_enriched": total_enriched,
                    "total_documents": total_documents
                }
            )

        # Update state with enrichment message
        messages = state.get('messages', [])
        messages.append(AIMessage(content="\n".join(msg)))
        state['messages'] = messages

        return state

    async def run(self, state: ResearchState) -> ResearchState:
        return await self.enrich_data(state) 