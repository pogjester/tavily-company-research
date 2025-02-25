from langchain_core.messages import AIMessage
from typing import Dict, Any
import os
from ..classes import ResearchState
from urllib.parse import urlparse, urljoin
import logging
from ..utils.references import process_references_from_search_results

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

        logger.info(f"Evaluating {len(docs)} documents")
        
        evaluated_docs = []
        try:
            # Evaluate each document using Tavily's score
            for doc in docs:
                try:
                    # Ensure score is a valid float
                    tavily_score = float(doc.get('score', 0))  # Default to 0 if no score
                    
                    # Keep documents with good Tavily score
                    if tavily_score >= self.relevance_threshold:
                        logger.info(f"Document passed threshold with score {tavily_score:.4f} for '{doc.get('title', 'No title')}'")
                        
                        evaluated_doc = {
                            **doc,
                            "evaluation": {
                                "overall_score": tavily_score,  # Store as float
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
                                        "title": doc.get('title', 'No title'),
                                        "score": tavily_score
                                    }
                                )
                    else:
                        logger.info(f"Document below threshold with score {tavily_score:.4f} for '{doc.get('title', 'No title')}'")
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error processing score for document: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error during document evaluation: {e}")
            return []

        # Sort evaluated docs by score before returning
        evaluated_docs.sort(key=lambda x: float(x['evaluation']['overall_score']), reverse=True)
        logger.info(f"Returning {len(evaluated_docs)} evaluated documents")
        
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
            
            # Limit to top 30 documents per category
            if len(sorted_items) > 30:
                sorted_items = sorted_items[:30]
            relevant_docs = dict(sorted_items)

            doc_counts[data_field] = {
                "initial": len(docs),
                "kept": len(relevant_docs)
            }

            if relevant_docs:
                msg.append(f"  ✓ Kept {len(relevant_docs)} relevant documents")
                logger.info(f"Kept {len(relevant_docs)} documents for {doc_type} with scores above threshold")
            else:
                msg.append(f"  ⚠️ No documents met relevance threshold")
                logger.info(f"No documents met relevance threshold for {doc_type}")

            # Store curated documents in state
            state[f'curated_{data_field}'] = relevant_docs
            
        # Process references using the references module
        top_reference_urls, reference_titles, reference_info = process_references_from_search_results(state)
        logger.info(f"Selected top {len(top_reference_urls)} references for the report")
        
        # Update state with references and their titles
        messages = state.get('messages', [])
        messages.append(AIMessage(content="\n".join(msg)))
        state['messages'] = messages
        state['references'] = top_reference_urls
        state['reference_titles'] = reference_titles
        state['reference_info'] = reference_info

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
