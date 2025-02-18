from langchain_core.messages import AIMessage
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
            if len(content) > 1500:
                content = content[:1500] + "..."
            parts.append(f"Content: {content}")
            
        return "\n\n".join(parts)


    async def evaluate_documents(self, docs: list, context: Dict[str, str]) -> list:
        """Evaluate a list of documents' relevance using Cohere rerank, using the specific query for each document."""
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

        evaluated_docs = []
        try:
            # Evaluate each document with its specific query
            for doc, formatted_doc in zip(valid_docs, documents):
                specific_query = doc.get('query', '')  # Use the specific query for this document
                print(f"\nEvaluating document with query: {specific_query}")
                response = self.co.rerank(
                    model='rerank-v3.5',
                    query=specific_query,
                    documents=[formatted_doc],
                    top_n=1
                )

                # Attach relevance scores to documents
                for result in response.results:
                    score = result.relevance_score
                    print(f"\nDocument score: {score:.3f} for '{doc.get('title', 'No title')}'")

                    # Only keep documents with good relevance
                    if score >= 0.7:
                        evaluated_doc = {
                            **doc,
                            "evaluation": {
                                "overall_score": score,
                                "query": specific_query,
                                "formatted_content": formatted_doc
                            }
                        }
                        evaluated_docs.append(evaluated_doc)
        except Exception as e:
            print(f"Error during document evaluation: {e}")
            return []

        print(f"\nKept {len(evaluated_docs)} documents with scores >= 0.7")
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

        msg = [f"🔍 Curating research data for {company}"]
        

        # Process each type of data
        data_types = {
            'financial_data': '💰 Financial',
            'news_data': '📰 News',
            'industry_data': '🏭 Industry',
            'company_data': '🏢 Company'
        }

        # Create all evaluation tasks upfront
        curation_tasks = []
        for data_field, source_type in data_types.items():
            data = state.get(data_field, {})
            if not data:
                continue

            docs = list(data.values())
            curation_tasks.append((data_field, source_type, data.keys(), docs))

        # Process all document types in parallel
        all_top_references = []  # Keep track of all top references with scores
        for data_field, source_type, urls, docs in curation_tasks:
            msg.append(f"\n{data_types[data_field]}: Found {len(docs)} documents")

            # Evaluate documents based on content
            evaluated_docs = await self.evaluate_documents(docs, context)

            if not evaluated_docs:
                msg.append(f"  ⚠️ No relevant documents found")
                continue

            # Filter documents with a score above threshold and limit to top 10
            relevant_docs = {url: doc for url, doc in zip(urls, evaluated_docs) 
                           if doc['evaluation']['overall_score'] >= 0.75}

            # Sort by score and limit to top 10
            if len(relevant_docs) > 10:
                sorted_docs = sorted(relevant_docs.items(), key=lambda item: item[1]['evaluation']['overall_score'], reverse=True)
                relevant_docs = dict(sorted_docs[:10])

            if relevant_docs:
                msg.append(f"  ✓ Kept {len(relevant_docs)} relevant documents")
            else:
                msg.append(f"  ⚠️ No documents met relevance threshold")

            # Collect all references with their scores
            current_references = [(url, doc['evaluation']['overall_score']) 
                                for url, doc in relevant_docs.items()]
            all_top_references.extend(current_references)

            # Update state with curated data
            state[f'curated_{data_field}'] = relevant_docs

        # Sort all references by score and select overall top 10
        all_top_references.sort(key=lambda x: x[1], reverse=True)
        top_reference_urls = [url for url, _ in all_top_references[:10]]

        # Update messages and state with final top references
        messages = state.get('messages', [])
        messages.append(AIMessage(content="\n".join(msg)))
        state['messages'] = messages
        state['references'] = top_reference_urls
        messages.append(AIMessage(content=f"Top References: {state['references']}"))
        print(f"Top References: {state['references']}")

        return state

    async def run(self, state: ResearchState) -> ResearchState:
        return await self.curate_data(state)
