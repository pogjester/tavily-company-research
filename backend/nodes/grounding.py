from langchain_core.messages import AIMessage
from tavily import AsyncTavilyClient
import os
import logging
from typing import Dict, Any, List
from ..classes import InputState, ResearchState

logger = logging.getLogger(__name__)

class GroundingNode:
    """Gathers initial grounding data about the company."""
    
    def __init__(self) -> None:
        self.tavily_client = AsyncTavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

    async def initial_search(self, state: InputState) -> ResearchState:
        # Add debug logging at the start to check websocket manager
        if websocket_manager := state.get('websocket_manager'):
            logger.info("Websocket manager found in state")
        else:
            logger.warning("No websocket manager found in state")
        
        company = state.get('company', 'Unknown Company')
        msg = f"🎯 Initiating research for {company}...\n"
        
        if websocket_manager := state.get('websocket_manager'):
            if job_id := state.get('job_id'):
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="processing",
                    message=f"🎯 Initiating research for {company}",
                    result={"step": "Initializing"}
                )

        site_scrape = {}

        # Only attempt extraction if we have a URL
        if url := state.get('company_url'):
            msg += f"\n🌐 Analyzing company website: {url}"
            logger.info(f"Starting website analysis for {url}")
            
            # Send initial briefing status
            if websocket_manager := state.get('websocket_manager'):
                if job_id := state.get('job_id'):
                    await websocket_manager.send_status_update(
                        job_id=job_id,
                        status="processing",
                        message="🌐 Analyzing company website",
                        result={"step": "Initial Site Scrape"}
                    )

            try:
                logger.info("Initiating Tavily extraction")
                site_extraction = await self.tavily_client.extract(url, extract_depth="basic")
                
                raw_contents = []
                for item in site_extraction.get("results", []):
                    if content := item.get("raw_content"):
                        raw_contents.append(content)
                
                if raw_contents:
                    site_scrape = {
                        'title': company,
                        'raw_content': "\n\n".join(raw_contents)
                    }
                    logger.info(f"Successfully extracted {len(raw_contents)} content sections")
                    msg += f"\n✅ Successfully extracted content from website"
                    if websocket_manager := state.get('websocket_manager'):
                        if job_id := state.get('job_id'):
                            await websocket_manager.send_status_update(
                                job_id=job_id,
                                status="processing",
                                message="Successfully extracted content from website",
                                result={"step": "Initial Site Scrape"}
                            )
                else:
                    logger.warning("No content found in extraction results")
                    msg += f"\n⚠️ No content found in website extraction"
                    if websocket_manager := state.get('websocket_manager'):
                        if job_id := state.get('job_id'):
                            await websocket_manager.send_status_update(
                                job_id=job_id,
                                status="processing",
                                message="⚠️ No content found in provided URL",
                                result={"step": "Initial Site Scrape"}
                            )
            except Exception as e:
                logger.error(f"Website extraction error: {str(e)}", exc_info=True)
                error_msg = f"⚠️ Error extracting website content: {str(e)}"
                print(error_msg)
                msg += f"\n{error_msg}"
                if websocket_manager := state.get('websocket_manager'):
                    if job_id := state.get('job_id'):
                        await websocket_manager.send_status_update(
                            job_id=job_id,
                            status="failed",
                            message="⚠️ Error extracting website content",
                            result={"step": "Initial Site Scrape"}
                        )
        else:
            msg += "\n⏩ No company URL provided, proceeding directly to research phase"
            if websocket_manager := state.get('websocket_manager'):
                if job_id := state.get('job_id'):
                    await websocket_manager.send_status_update(
                        job_id=job_id,
                        status="processing",
                        message="No company URL provided, proceeding directly to research phase",
                        result={"step": "Initializing"}
                    )
        # Add context about what information we have
        context_data = {}
        if hq := state.get('hq_location'):
            msg += f"\n📍 Company HQ: {hq}"
            context_data["hq_location"] = hq
        if industry := state.get('industry'):
            msg += f"\n🏭 Industry: {industry}"
            context_data["industry"] = industry
        
        # Initialize ResearchState with input information
        research_state = {
            # Copy input fields
            "company": state.get('company'),
            "company_url": state.get('company_url'),
            "hq_location": state.get('hq_location'),
            "industry": state.get('industry'),
            # Initialize research fields
            "messages": [AIMessage(content=msg)],
            "site_scrape": site_scrape,
            # Pass through websocket info
            "websocket_manager": state.get('websocket_manager'),
            "job_id": state.get('job_id')
        }

        return research_state

    async def run(self, state: InputState) -> ResearchState:
        return await self.initial_search(state)
