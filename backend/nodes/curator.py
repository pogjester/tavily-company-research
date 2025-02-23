from langchain_core.messages import AIMessage
from typing import Dict, Any
import os
from ..classes import ResearchState
from urllib.parse import urlparse, urljoin
import logging

logger = logging.getLogger(__name__)

class Curator:
    def __init__(self) -> None:
        self.relevance_threshold = 0.4  # Fixed initialization of class attribute
        logger.info("Curator initialized with relevance threshold: {relevance_threshhold}")

    async def evaluate_documents(self, state: ResearchState, docs: list, context: Dict[str, str]) -> list:
        """Evaluate documents based on Tavily's scoring."""
        if websocket_manager := state.get('websocket_manager'):
            if job_id := state.get('job_id'):
                logger.info(f"Sending initial curation status update for job {job_id}")
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="processing",
                    message=f"Evaluating documents",
                    result={
                        "step": "Curation",
                    }
                )
        
        if not docs:
            return []

        print(f"\nDebug: Evaluating {len(docs)} documents")
        
        evaluated_docs = []
        try:
            # Evaluate each document using Tavily's score
            for doc in docs:
                tavily_score = float(doc.get('score', 0))  # Default to 0 if no score
                
                # Keep documents with good Tavily score
                if tavily_score >= self.relevance_threshold:  # Adjusted threshold since we're only using Tavily
                    print(f"\nDocument score: {tavily_score:.3f} for '{doc.get('title', 'No title')}'")
                    
                    evaluated_doc = {
                        **doc,
                        "evaluation": {
                            "overall_score": tavily_score,
                            "query": doc.get('query', '')
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
                                    "doc_type": doc.get('doc_type', 'unknown'),
                                    "title": doc.get('title', 'No title')
                                }
                            )
                else:
                    print(f"Skipping document with low score ({tavily_score:.3f}): {doc.get('title', 'No title')}")
                    
        except Exception as e:
            print(f"Error during document evaluation: {e}")
            return []

        return evaluated_docs

    async def curate_data(self, state: ResearchState) -> ResearchState:
        """Curate all collected data based on Tavily scores."""
        company = state.get('company', 'Unknown Company')
        logger.info(f"Starting curation for company: {company}")
        
        # Send initial status update through WebSocket
        if websocket_manager := state.get('websocket_manager'):
            if job_id := state.get('job_id'):
                logger.info(f"Sending initial curation status update for job {job_id}")
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="processing",
                    message=f"Starting document curation for {company}",
                    result={
                        "step": "Curation",
                        "doc_counts": {
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
                    parsed = urlparse(url)
                    if not parsed.scheme:
                        url = urljoin('https://', url)
                    clean_url = parsed._replace(query='', fragment='').geturl()
                    if clean_url not in unique_docs:
                        doc['url'] = clean_url
                        doc['doc_type'] = doc_type
                        unique_docs[clean_url] = doc
                except Exception as e:
                    continue

            docs = list(unique_docs.values())
            curation_tasks.append((data_field, emoji, doc_type, unique_docs.keys(), docs))

        # Track document counts for each type
        doc_counts = {}
        all_top_references = []

        for data_field, emoji, doc_type, urls, docs in curation_tasks:
            msg.append(f"\n{emoji}: Found {len(docs)} documents")

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

            evaluated_docs = await self.evaluate_documents(state, docs, context)

            if not evaluated_docs:
                msg.append(f"  ⚠️ No relevant documents found")
                doc_counts[data_field] = {"initial": len(docs), "kept": 0}
                continue

            # Filter and sort by Tavily score
            relevant_docs = {url: doc for url, doc in zip(urls, evaluated_docs)}
            sorted_items = sorted(relevant_docs.items(), key=lambda item: item[1]['evaluation']['overall_score'], reverse=True)
            
            # Limit to top 15 documents
            if len(sorted_items) > 30:
                sorted_items = sorted_items[:30]
            relevant_docs = dict(sorted_items)

            doc_counts[data_field] = {
                "initial": len(docs),
                "kept": len(relevant_docs)
            }

            if relevant_docs:
                msg.append(f"  ✓ Kept {len(relevant_docs)} relevant documents")
            else:
                msg.append(f"  ⚠️ No documents met relevance threshold")

            # Collect references with scores
            current_references = [(url, doc['evaluation']['overall_score']) 
                                for url, doc in relevant_docs.items()]
            all_top_references.extend(current_references)

            state[f'curated_{data_field}'] = relevant_docs

        # Sort references by score and select top 10
        all_top_references.sort(key=lambda x: x[1], reverse=True)
        top_reference_urls = [url for url, _ in all_top_references[:10]]

        # Update state
        messages = state.get('messages', [])
        messages.append(AIMessage(content="\n".join(msg)))
        state['messages'] = messages
        state['references'] = list(top_reference_urls)

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
