from langchain_core.messages import AIMessage
from typing import Dict, Any
import os
import cohere
from ..classes import ResearchState
from urllib.parse import urlparse, urljoin

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
            
        # Try both content and raw_content
        content = doc.get('content') or doc.get('raw_content', '')
        if content:
            # Truncate content if too long (Cohere has token limits)
            if len(content) > 1500:
                content = content[:1500] + "..."
            parts.append(f"Content: {content}")
            
        return "\n\n".join(parts)


    async def evaluate_documents(self, state: ResearchState, docs: list, context: Dict[str, str]) -> list:
        if websocket_manager := state.get('websocket_manager'):
                if job_id := state.get('job_id'):
                    await websocket_manager.send_status_update(
                        job_id=job_id,
                        status="processing",
                        message=f"Evaluating documents",
                        result={
                            "step": "Curation",
                        }
                    )
        
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
                tavily_score = float(doc.get('score', 0))  # Default to 0 if no score
                if tavily_score >= 0.25:
                    specific_query = doc.get('query', '')  # Use the specific query for this document
                    print(f"\nEvaluating document with query: {specific_query} (Tavily score: {tavily_score:.3f})")
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
                        if score >= 0.3:
                            evaluated_doc = {
                                **doc,
                                "evaluation": {
                                    "overall_score": score,
                                    "tavily_score": tavily_score,
                                    "query": specific_query,
                                    "formatted_content": formatted_doc
                                }
                            }
                            evaluated_docs.append(evaluated_doc)
                            
                            # Send incremental update for kept document
                            if websocket_manager := state.get('websocket_manager'):
                                if job_id := state.get('job_id'):
                                    await websocket_manager.send_status_update(
                                        job_id=job_id,
                                        status="document_kept",
                                        message=f"Kept document: {doc.get('title', 'No title')}",
                                        result={
                                            "step": "Curation",
                                            "doc_type": doc.get('doc_type', 'unknown'),  # Add doc_type to track category
                                            "title": doc.get('title', 'No title')
                                        }
                                    )
                else:
                    print(f"Skipping document with low Tavily score ({tavily_score:.3f}): {doc.get('title', 'No title')}")
        except Exception as e:
            print(f"Error during document evaluation: {e}")
            return []

        return evaluated_docs

    async def curate_data(self, state: ResearchState) -> ResearchState:
        """Curate all collected data based on relevance scores."""
        company = state.get('company', 'Unknown Company')
        
        # Send initial status update through WebSocket
        if websocket_manager := state.get('websocket_manager'):
            if job_id := state.get('job_id'):
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="processing",
                    message=f"Starting document curation for {company}",
                    result={
                        "step": "Curation",
                        "doc_counts": {  # Initialize counts to 0
                            "company": {"initial": 0, "kept": 0},
                            "industry": {"initial": 0, "kept": 0},
                            "financial": {"initial": 0, "kept": 0},
                            "news": {"initial": 0, "kept": 0}
                        }
                    }
                )

        industry = state.get('industry', 'Unknown')
        context = {
            "company": company,
            "industry": industry,
            "hq_location": state.get('hq_location', 'Unknown')
        }

        msg = [f"🔍 Curating research data for {company}"]
        
        # Process each type of data with status updates
        data_types = {
            'financial_data': ('💰 Financial', 'financial'),
            'news_data': ('📰 News', 'news'),
            'industry_data': ('🏭 Industry', 'industry'),
            'company_data': ('🏢 Company', 'company')
        }

        # Create all evaluation tasks upfront
        curation_tasks = []
        for data_field, (emoji, doc_type) in data_types.items():
            data = state.get(data_field, {})
            if not data:
                continue

            # Filter and normalize URLs
            unique_docs = {}
            for url, doc in data.items():
                try:
                    # Parse and normalize URL
                    parsed = urlparse(url)
                    if not parsed.scheme:
                        url = urljoin('https://', url)
                    
                    # Remove tracking parameters
                    clean_url = parsed._replace(query='', fragment='').geturl()
                    
                    # Use clean URL as key and add doc_type
                    if clean_url not in unique_docs:
                        doc['url'] = clean_url  # Update doc with clean URL
                        doc['doc_type'] = doc_type  # Add doc_type for tracking
                        unique_docs[clean_url] = doc
                except Exception as e:
                    continue

            docs = list(unique_docs.values())
            curation_tasks.append((data_field, emoji, doc_type, unique_docs.keys(), docs))

        # Track document counts for each type
        doc_counts = {}
        
        # Process all document types in parallel
        all_top_references = []  # Keep track of all top references with scores
        for data_field, emoji, doc_type, urls, docs in curation_tasks:
            msg.append(f"\n{emoji}: Found {len(docs)} documents")

            # Send initial count for this category
            if websocket_manager := state.get('websocket_manager'):
                if job_id := state.get('job_id'):
                    await websocket_manager.send_status_update(
                        job_id=job_id,
                        status="category_start",
                        message=f"Processing {doc_type} documents",
                        result={
                            "step": "Curation",
                            "doc_type": doc_type,
                            "initial_count": len(docs)
                        }
                    )

            # Evaluate documents based on content
            evaluated_docs = await self.evaluate_documents(state, docs, context)

            if not evaluated_docs:
                msg.append(f"  ⚠️ No relevant documents found")
                doc_counts[data_field] = {"initial": len(docs), "kept": 0}
                continue

            # Filter documents with a score above threshold
            relevant_docs = {url: doc for url, doc in zip(urls, evaluated_docs) 
                            if doc['evaluation']['overall_score'] >= 0.3}
            
            # Sort by score but maintain as dictionary
            sorted_items = sorted(relevant_docs.items(), key=lambda item: item[1]['evaluation']['overall_score'], reverse=True)
            
            # Limit to top 30 while keeping as dictionary
            if len(sorted_items) > 30:
                sorted_items = sorted_items[:30]
            relevant_docs = dict(sorted_items)

            # Track document counts
            doc_counts[data_field] = {
                "initial": len(docs),
                "kept": len(relevant_docs)
            }

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
        state['references'] = list(top_reference_urls)
        messages.append(AIMessage(content=f"Top References: {state['references']}"))
        print(f"Top References: {state['references']}")

        # Send final curation stats
        if websocket_manager := state.get('websocket_manager'):
            if job_id := state.get('job_id'):
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="curation_complete",
                    message="Document curation complete",
                    result={
                        "step": "Curation",
                        "doc_counts": {
                            "company": doc_counts.get('company_data', {"initial": 0, "kept": 0}),
                            "industry": doc_counts.get('industry_data', {"initial": 0, "kept": 0}),
                            "financial": doc_counts.get('financial_data', {"initial": 0, "kept": 0}),
                            "news": doc_counts.get('news_data', {"initial": 0, "kept": 0})
                        }
                    }
                )

        return state

    async def run(self, state: ResearchState) -> ResearchState:
        return await self.curate_data(state)
