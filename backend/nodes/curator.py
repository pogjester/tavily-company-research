from langchain_core.messages import AIMessage
from datetime import datetime
from typing import Dict, Any, List
import os
import cohere
from tavily import AsyncTavilyClient
import asyncio

from ..classes import ResearchState

class Curator:
    def __init__(self) -> None:
        cohere_key = os.getenv("COHERE_API_KEY")
        tavily_key = os.getenv("TAVILY_API_KEY")
        if not cohere_key:
            raise ValueError("COHERE_API_KEY environment variable is not set")
        if not tavily_key:
            raise ValueError("TAVILY_API_KEY environment variable is not set")
        self.co = cohere.Client(cohere_key)
        self.tavily_client = AsyncTavilyClient(api_key=tavily_key)
        self.batch_size = 10  # Process documents in batches

    async def evaluate_documents(self, docs: list, query: str) -> list:
        """Evaluate a list of documents' relevance using Cohere rerank."""
        if not docs:
            return []

        # Prepare document content, using available content
        documents = []
        for doc in docs:
            title = doc.get('title', '')
            content = doc.get('content', '')  # Using summary content for initial ranking
            full_content = f"{title}\n{content}"
            documents.append(full_content)

        # Process in batches to avoid overwhelming the API
        evaluated_docs = []
        for i in range(0, len(documents), self.batch_size):
            batch_docs = documents[i:i + self.batch_size]
            batch_original_docs = docs[i:i + self.batch_size]

            # Rerank the batch
            response = self.co.rerank(
                model='rerank-v3.5',
                query=query,
                documents=batch_docs,
                top_n=len(batch_docs)
            )

            # Attach relevance scores to documents
            for result in response.results:
                doc = batch_original_docs[result.index]
                score = result.relevance_score
                evaluated_doc = {
                    **doc,
                    "evaluation": {
                        "overall_score": score
                    }
                }
                evaluated_docs.append(evaluated_doc)

        return evaluated_docs

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
        # Process in batches to avoid overwhelming the API
        raw_contents = {}
        for i in range(0, len(urls), self.batch_size):
            batch_urls = urls[i:i + self.batch_size]
            tasks = [self.fetch_single_content(url) for url in batch_urls]
            results = await asyncio.gather(*tasks)
            for result in results:
                raw_contents.update(result)
        return raw_contents

    async def curate_data(self, state: ResearchState) -> ResearchState:
        """Curate all collected data."""
        company = state.get('company', 'Unknown Company')
        context = {
            "company": company,
            "industry": state.get('industry', 'Unknown'),
            "hq_location": state.get('hq_location', 'Unknown')
        }

        msg = [f"🔍 Curating research data for {company}:"]

        # Process each type of data
        data_types = {
            'financial_data': 'financial',
            'news_data': 'news',
            'industry_data': 'industry',
            'company_data': 'company'
        }

        # Create all evaluation tasks upfront
        curation_tasks = []
        for data_field, source_type in data_types.items():
            data = state.get(data_field, {})
            if not data:
                continue

            query = f"Relevant {source_type} information about {company} in {context['industry']} industry"
            docs = list(data.values())
            curation_tasks.append((data_field, source_type, data.keys(), docs, query))

        # Process all document types in parallel
        for data_field, source_type, urls, docs, query in curation_tasks:
            msg.append(f"\n• Evaluating {len(docs)} {source_type} documents...")

            # Evaluate documents
            evaluated_docs = await self.evaluate_documents(docs, query)

            # Filter documents with a score above 0.6
            relevant_docs = {url: doc for url, doc in zip(urls, evaluated_docs) 
                           if doc['evaluation']['overall_score'] >= 0.6}

            # Fetch raw content only for relevant documents
            if relevant_docs:
                msg.append(f"  • Fetching full content for {len(relevant_docs)} relevant documents...")
                raw_contents = await self.fetch_raw_content(list(relevant_docs.keys()))
                
                # Update relevant documents with raw content
                for url, raw_content in raw_contents.items():
                    if raw_content:
                        relevant_docs[url]['raw_content'] = raw_content

            # Update state with curated data
            state[f'curated_{data_field}'] = relevant_docs
            msg.append(f"  ✓ Kept {len(relevant_docs)}/{len(docs)} relevant documents")

        # Update state with curation message
        messages = state.get('messages', [])
        messages.append(AIMessage(content="\n".join(msg)))
        state['messages'] = messages

        return state

    async def run(self, state: ResearchState) -> ResearchState:
        return await self.curate_data(state)
