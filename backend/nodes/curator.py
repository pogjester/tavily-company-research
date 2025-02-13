from langchain_core.messages import AIMessage
from datetime import datetime
from typing import Dict, Any
import os
import cohere

from ..classes import ResearchState

class Curator:
    def __init__(self) -> None:
        cohere_key = os.getenv("COHERE_API_KEY")
        if not cohere_key:
            raise ValueError("COHERE_API_KEY environment variable is not set")
        self.co = cohere.Client(cohere_key)

    async def evaluate_documents(self, docs: list, query: str) -> list:
        """Evaluate a list of documents' relevance using Cohere rerank."""
        # Prepare document content, combining title, content, and raw content
        documents = []
        for doc in docs:
            title = doc.get('title', '')
            content = doc.get('content', '')
            raw_content = doc.get('raw_content', '')
            # Combine all available content, prioritizing raw content if available
            full_content = f"{title}\n{raw_content if raw_content else content}"
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
                    "overall_score": score,
                    "used_raw_content": bool(doc.get('raw_content'))
                }
            }
            evaluated_docs.append(evaluated_doc)

        return evaluated_docs

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

            # Filter documents with a score above 0.6
            curated_data = {url: doc for url, doc in zip(data.keys(), evaluated_docs) if doc['evaluation']['overall_score'] >= 0.6}

            # Update state with curated data
            state[f'curated_{data_field}'] = curated_data
            msg.append(f"  ✓ Kept {len(curated_data)}/{len(data)} relevant documents")

        # Update state with curation message
        messages = state.get('messages', [])
        messages.append(AIMessage(content="\n".join(msg)))
        state['messages'] = messages

        return state

    async def run(self, state: ResearchState) -> ResearchState:
        return await self.curate_data(state)
