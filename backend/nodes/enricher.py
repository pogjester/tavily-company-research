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

    async def fetch_single_content(self, url: str, websocket_manager=None, job_id=None, category=None) -> Dict[str, str]:
        """Fetch raw content for a single URL."""
        try:
            if websocket_manager and job_id:
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="extracting",
                    message=f"Extracting content from {url}",
                    result={
                        "step": "Enriching",
                        "url": url,
                        "category": category
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
                            "category": category,
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
                        "category": category,
                        "success": False,
                        "error": str(e)
                    }
                )
        return {url: ''}

    async def fetch_raw_content(self, urls: List[str], websocket_manager=None, job_id=None, category=None) -> Dict[str, str]:
        """Fetch raw content for multiple URLs in parallel."""
        raw_contents = {}
        total_batches = (len(urls) + self.batch_size - 1) // self.batch_size

        # Create batches
        batches = [urls[i:i + self.batch_size] for i in range(0, len(urls), self.batch_size)]
        
        # Process batches in parallel with rate limiting
        semaphore = asyncio.Semaphore(3)  # Limit concurrent batches to 3
        
        async def process_batch(batch_num: int, batch_urls: List[str]) -> Dict[str, str]:
            async with semaphore:
                if websocket_manager and job_id:
                    await websocket_manager.send_status_update(
                        job_id=job_id,
                        status="batch_start",
                        message=f"Processing batch {batch_num + 1}/{total_batches}",
                        result={
                            "step": "Enriching",
                            "batch": batch_num + 1,
                            "total_batches": total_batches,
                            "category": category
                        }
                    )

                # Process URLs in batch concurrently
                tasks = [self.fetch_single_content(url, websocket_manager, job_id, category) for url in batch_urls]
                results = await asyncio.gather(*tasks)
                
                # Combine results from batch
                batch_contents = {}
                for result in results:
                    batch_contents.update(result)
                
                return batch_contents

        # Process all batches
        batch_results = await asyncio.gather(*[
            process_batch(i, batch) 
            for i, batch in enumerate(batches)
        ])

        # Combine results from all batches
        for batch_result in batch_results:
            raw_contents.update(batch_result)

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
            'financial_data': ('💰 Financial', 'financial'),
            'news_data': ('📰 News', 'news'),
            'industry_data': ('🏭 Industry', 'industry'),
            'company_data': ('🏢 Company', 'company')
        }

        # Create tasks for parallel processing
        enrichment_tasks = []
        for data_field, (label, category) in data_types.items():
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

            if websocket_manager and job_id:
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="category_start",
                    message=f"Processing {label} documents",
                    result={
                        "step": "Enriching",
                        "category": category,
                        "count": len(docs_needing_content)
                    }
                )

            # Create task for this category
            enrichment_tasks.append({
                'field': curated_field,
                'category': category,
                'label': label,
                'docs': docs_needing_content,
                'curated_docs': curated_docs
            })

        # Process all categories in parallel
        if enrichment_tasks:
            async def process_category(task):
                raw_contents = await self.fetch_raw_content(
                    list(task['docs'].keys()),
                    websocket_manager,
                    job_id,
                    task['category']
                )
                
                enriched_count = 0
                for url, raw_content in raw_contents.items():
                    if raw_content:
                        task['curated_docs'][url]['raw_content'] = raw_content
                        enriched_count += 1

                # Update state with enriched documents
                state[task['field']] = task['curated_docs']
                
                if websocket_manager and job_id:
                    await websocket_manager.send_status_update(
                        job_id=job_id,
                        status="category_complete",
                        message=f"Completed {task['label']} documents",
                        result={
                            "step": "Enriching",
                            "category": task['category'],
                            "enriched": enriched_count,
                            "total": len(task['docs'])
                        }
                    )
                
                return {
                    'category': task['category'],
                    'enriched': enriched_count,
                    'total': len(task['docs'])
                }

            # Process all categories in parallel
            results = await asyncio.gather(*[process_category(task) for task in enrichment_tasks])
            
            # Calculate totals
            total_enriched = sum(r['enriched'] for r in results)
            total_documents = sum(r['total'] for r in results)

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