from langchain_core.messages import AIMessage
from typing import Dict, List
import os
from tavily import AsyncTavilyClient
import logging
from ..classes import ResearchState

logger = logging.getLogger(__name__)

class Enricher:
    """Enriches curated documents with raw content."""
    
    def __init__(self) -> None:
        tavily_key = os.getenv("TAVILY_API_KEY")
        if not tavily_key:
            raise ValueError("TAVILY_API_KEY environment variable is not set")
        self.tavily_client = AsyncTavilyClient(api_key=tavily_key)
        self.batch_size = 20  # Process documents in batches

    async def fetch_raw_content(self, urls: List[str]) -> Dict[str, str]:
        """Fetch raw content for multiple URLs in parallel."""
        raw_contents = {}
        try:
            # Process in batches to avoid overwhelming the API
            for i in range(0, len(urls), self.batch_size):
                batch_urls = urls[i:i + self.batch_size]
                logger.info(f"Fetching raw content for batch: {batch_urls}")
                results = await self.tavily_client.extract(batch_urls)
                for result in results.get("results", []):
                    url = result.get("url")
                    raw_content = result.get("raw_content", "")
                    raw_contents[url] = raw_content
                    logger.info(f"Fetched raw content for URL: {url}")
        except Exception as e:
            logger.error(f"Error fetching raw content for URLs: {e}")
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
            
            # Limit to 20 documents at a time
            docs_to_enrich = list(docs_needing_content.keys())[:20]
            msg.append(f"\n• Enriching {len(docs_to_enrich)} {label} documents...")
            logger.info(f"Enriching {len(docs_to_enrich)} {label} documents for {company}")

            # Fetch raw content for documents
            raw_contents = await self.fetch_raw_content(docs_to_enrich)
            
            # Update documents with raw content
            enriched_count = 0
            for url, raw_content in raw_contents.items():
                if raw_content:
                    curated_docs[url]['raw_content'] = raw_content
                    enriched_count += 1
                    logger.info(f"Enriched document for URL: {url}")
            
            # Update state with enriched documents
            state[curated_field] = curated_docs
            msg.append(f"  ✓ Successfully enriched {enriched_count}/{len(docs_to_enrich)} documents")
            logger.info(f"Successfully enriched {enriched_count}/{len(docs_to_enrich)} {label} documents for {company}")

        # Update state with enrichment message
        messages = state.get('messages', [])
        messages.append(AIMessage(content="\n".join(msg)))
        state['messages'] = messages

        return state

    async def run(self, state: ResearchState) -> ResearchState:
        return await self.enrich_data(state)