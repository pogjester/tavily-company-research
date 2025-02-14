from langchain_core.messages import AIMessage
from typing import Dict, List, Any
import os
import cohere

from ..classes import ResearchState

class Curator:
    def __init__(self) -> None:
        cohere_key = os.getenv("COHERE_API_KEY")
        if not cohere_key:
            raise ValueError("COHERE_API_KEY environment variable is not set")
        self.co = cohere.Client(cohere_key)
        self.batch_size = 10  # Process documents in batches

    def format_document(self, doc: Dict[str, Any]) -> str:
        """Format a document for relevance evaluation."""
        parts = []
        
        # Add title if available
        if title := doc.get('title'):
            parts.append(f"Title: {title}")
            
        # Add source query that found this document
        if query := doc.get('query'):
            parts.append(f"Search Query: {query}")
            
        # Try both content and raw_content
        content = doc.get('content') or doc.get('raw_content', '')
        if content:
            # Truncate content if too long (Cohere has token limits)
            if len(content) > 1000:
                content = content[:1000] + "..."
            parts.append(f"Content: {content}")
            
        return "\n\n".join(parts)

    def format_query(self, base_query: str, context: Dict[str, str]) -> str:
        """Format a query for better relevance evaluation."""
        query_parts = [
            f"Find highly relevant and recent information about {context.get('company', 'Unknown')}.",
            f"Specifically looking for: {base_query}",
            f"Company: {context.get('company', 'Unknown')}"
        ]
        
        if industry := context.get('industry'):
            if industry != 'Unknown':
                query_parts.append(f"Industry focus: {industry}")
                
        if location := context.get('hq_location'):
            if location != 'Unknown':
                query_parts.append(f"Company location: {location}")
                
        return " ".join(query_parts)

    async def evaluate_documents(self, docs: list, query: str, context: Dict[str, str]) -> list:
        """Evaluate a list of documents' relevance using Cohere rerank."""
        if not docs:
            return []

        print(f"\nDebug: Evaluating {len(docs)} documents")
        print("Document fields available:")
        for i, doc in enumerate(docs[:2]):  # Print first 2 docs as sample
            print(f"\nDocument {i + 1}:")
            print(f"Keys: {doc.keys()}")
            print(f"Title: {doc.get('title', 'No title')}")
            content = doc.get('content') or doc.get('raw_content', '')
            print(f"Has content: {bool(content)}")
            if content:
                print(f"Content length: {len(content)}")

        # Prepare document content
        documents = []
        valid_docs = []  # Keep track of docs with content
        for doc in docs:
            content = doc.get('content') or doc.get('raw_content', '')
            if not content:
                print(f"Warning: No content found in document with title: {doc.get('title', 'No title')}")
                continue
                
            # Format document for evaluation
            formatted_doc = self.format_document(doc)
            documents.append(formatted_doc)
            valid_docs.append(doc)

        if not documents:
            print("No documents with content to evaluate")
            return []

        print(f"\nFound {len(documents)} valid documents with content")
        
        # Format the query with context
        formatted_query = self.format_query(query, context)
        print(f"\nFormatted query: {formatted_query}")

        # Process in batches to avoid overwhelming the API
        evaluated_docs = []
        for i in range(0, len(documents), self.batch_size):
            batch_docs = documents[i:i + self.batch_size]
            batch_original_docs = valid_docs[i:i + self.batch_size]

            try:
                # Rerank the batch with more emphasis on relevance
                response = self.co.rerank(
                    model='rerank-v3.5',
                    query=formatted_query,
                    documents=batch_docs,
                    top_n=len(batch_docs)
                )

                # Attach relevance scores to documents
                for result in response.results:
                    doc = batch_original_docs[result.index]
                    score = result.relevance_score
                    print(f"\nDocument score: {score:.3f} for '{doc.get('title', 'No title')}'")
                    
                    # Only keep documents with good relevance
                    if score >= 0.5:
                        evaluated_doc = {
                            **doc,
                            "evaluation": {
                                "overall_score": score,
                                "query": formatted_query,
                                "formatted_content": batch_docs[result.index]
                            }
                        }
                        evaluated_docs.append(evaluated_doc)
            except Exception as e:
                print(f"Error during document evaluation: {e}")
                continue

        print(f"\nKept {len(evaluated_docs)} documents with scores >= 0.5")
        if evaluated_docs:
            print("\nTop scoring documents:")
            for doc in sorted(evaluated_docs, key=lambda x: x['evaluation']['overall_score'], reverse=True)[:3]:
                print(f"- {doc.get('title', 'No title')}: {doc['evaluation']['overall_score']:.3f}")
        
        return evaluated_docs

    async def curate_data(self, state: ResearchState) -> ResearchState:
        """Curate all collected data based on relevance scores."""
        company = state.get('company', 'Unknown Company')
        industry = state.get('industry', 'Unknown')
        context = {
            "company": company,
            "industry": industry,
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
                msg.append(f"\n• No {source_type} data available to curate")
                continue

            query = f"Relevant {source_type} information about {company}"
            if industry != 'Unknown':
                query += f" in {industry} industry"
                
            docs = list(data.values())
            print(f"\nProcessing {source_type} data:")
            print(f"Found {len(docs)} documents")
            print(f"Query: {query}")
            
            msg.append(f"\n• Found {len(docs)} {source_type} documents to evaluate")
            curation_tasks.append((data_field, source_type, data.keys(), docs, query))

        # Process all document types in parallel
        for data_field, source_type, urls, docs, query in curation_tasks:
            msg.append(f"\n• Evaluating {len(docs)} {source_type} documents...")

            # Evaluate documents based on content
            evaluated_docs = await self.evaluate_documents(docs, query, context)
            
            if not evaluated_docs:
                msg.append(f"  ⚠️ No {source_type} documents could be evaluated")
                continue

            # Filter documents with a score above 0.6
            relevant_docs = {url: doc for url, doc in zip(urls, evaluated_docs) 
                           if doc['evaluation']['overall_score'] >= 0.5}

            print(f"\nRelevant {source_type} documents:")
            print(f"Total evaluated: {len(evaluated_docs)}")
            print(f"Kept after filtering: {len(relevant_docs)}")
            if relevant_docs:
                print("Sample scores:")
                for url, doc in list(relevant_docs.items())[:2]:
                    print(f"- {doc.get('title', 'No title')}: {doc['evaluation']['overall_score']:.3f}")
                    print(f"  Query: {doc['evaluation']['query']}")

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
