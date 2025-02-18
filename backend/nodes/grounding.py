from langchain_core.messages import AIMessage
from tavily import AsyncTavilyClient
import os
import time
import logging

from ..classes import InputState, ResearchState

logger = logging.getLogger(__name__)

class GroundingNode:
    def __init__(self) -> None:
        self.tavily_client = AsyncTavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

    async def _send_update(self, state: InputState, message: str, status: str, data: dict = None):
        """Send a status update through websocket if available"""
        if websocket_manager := state.get('websocket_manager'):
            if job_id := state.get('job_id'):
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status=status,
                    message=message,
                    result=data
                )
        logger.info(f"Grounding update - {status}: {message}")

    async def initial_search(self, state: InputState) -> ResearchState:
        company = state.get('company', 'Unknown Company')
        msg = f"🎯 Initiating research for {company}...\n"
        
        await self._send_update(
            state,
            f"Starting research for {company}",
            "research_start",
            {"company": company}
        )

        site_scrape = {}

        # Only attempt extraction if we have a URL
        if url := state.get('company_url'):
            msg += f"\n🌐 Analyzing company website: {url}"
            await self._send_update(
                state,
                f"Analyzing company website: {url}",
                "site_scrape_start",
                {"url": url}
            )

            try:
                site_extraction = await self.tavily_client.extract(url)
                for item in site_extraction.get("results", []):
                    raw_content = item.get("raw_content", "")
                    site_scrape = {'title': company, 'raw_content': raw_content}
                
                msg += f"\n✅ Successfully extracted content from website"
                await self._send_update(
                    state,
                    "Successfully extracted website content",
                    "site_scrape_complete",
                    {
                        "url": url,
                        "content_length": len(raw_content) if raw_content else 0
                    }
                )
            except Exception as e:
                error_msg = f"⚠️ Error extracting website content: {str(e)}"
                print(error_msg)
                msg += f"\n{error_msg}"
                await self._send_update(
                    state,
                    error_msg,
                    "site_scrape_error",
                    {"error": str(e)}
                )
        else:
            msg += "\n⏩ No company URL provided, proceeding directly to research phase"
            await self._send_update(
                state,
                "No company URL provided",
                "site_scrape_skip"
            )

        # Add context about what information we have
        context_data = {}
        if hq := state.get('hq_location'):
            msg += f"\n📍 Company HQ: {hq}"
            context_data["hq_location"] = hq
        if industry := state.get('industry'):
            msg += f"\n🏭 Industry: {industry}"
            context_data["industry"] = industry

        if context_data:
            await self._send_update(
                state,
                "Additional context gathered",
                "context_complete",
                context_data
            )
        
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

        await self._send_update(
            state,
            "Grounding phase complete",
            "grounding_complete",
            {"state_keys": list(research_state.keys())}
        )

        return research_state

    async def run(self, state: InputState) -> ResearchState:
        return await self.initial_search(state)
