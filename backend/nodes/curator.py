from langchain_core.messages import AIMessage
from datetime import datetime
from typing import Dict, Any, List
import os
import cohere
from tavily import AsyncTavilyClient

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

    async def evaluate_documents(self, docs: list, query: str) -> list:
        """Evaluate a list of documents' relevance using Cohere rerank."""
        # Prepare document content, using available content
        documents = []
        for doc in docs:
            title = doc.get('title', '')
            content = doc.get('content', '')  # Using summary content for initial ranking
            full_content = f"{title}\n{content}"
            documents.append(full_content)

        # Rerank the documents
        response = self.co.rerank(
            model='rerank-v3.5',
            query=query,
            documents=documents,
            top_n=len(docs)
        )

        # Attach relevance scores to documents
        evaluated_docs = []
        for result in response.results:
            doc = docs[result.index]
            score = result.relevance_score
            evaluated_doc = {
                **doc,
                "evaluation": {
                    "overall_score": score
                }
            }
            evaluated_docs.append(evaluated_doc)

        return evaluated_docs

    async def fetch_raw_content(self, urls: List[str]) -> Dict[str, str]:
        """Fetch raw content for a list of URLs using Tavily."""
        raw_contents = {}
        for url in urls:
            try:
                result = await self.tavily_client.extract(url)
                if result and result.get('results'):
                    raw_contents[url] = result['results'][0].get('raw_content', '')
            except Exception as e:
                print(f"Error fetching raw content for {url}: {e}")
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

        for data_field, source_type in data_types.items():
            data = state.get(data_field, {})
            if not data:
                msg.append(f"\n• No {source_type} data to curate")
                continue

            msg.append(f"\n• Evaluating {len(data)} {source_type} documents...")

            # Create query based on document type
            queries = {
                'financial': f"Relevant financial information about {company} in {context['industry']} industry",
                'news': f"Recent and important news about {company} in {context['industry']} industry",
                'industry': f"Industry analysis and market position of {company} in {context['industry']} industry",
                'company': f"Core business information and company details about {company} in {context['industry']} industry"
            }
            query = queries.get(source_type, f"Information about {company} in {context['industry']} industry")

            # Evaluate documents
            docs = list(data.values())
            evaluated_docs = await self.evaluate_documents(docs, query)

            # Filter documents with a score above 0.5
            relevant_docs = {url: doc for url, doc in zip(data.keys(), evaluated_docs) 
                           if doc['evaluation']['overall_score'] >= 0.5}

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
            msg.append(f"  ✓ Kept {len(relevant_docs)}/{len(data)} relevant documents")

        # Update state with curation message
        messages = state.get('messages', [])
        messages.append(AIMessage(content="\n".join(msg)))
        state['messages'] = messages

        return state

    async def run(self, state: ResearchState) -> ResearchState:
        return await self.curate_data(state)
