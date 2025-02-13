from langchain_core.messages import AIMessage
from tavily import AsyncTavilyClient
import os

from ..classes import InputState, ResearchState

class GroundingNode:
    def __init__(self) -> None:
        self.tavily_client = AsyncTavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

    async def initial_search(self, input_state: InputState) -> ResearchState:
        company = input_state.get('company', 'Unknown Company')
        msg = f"🎯 Initiating research for {company}...\n"
        site_scrape = {}

        # Only attempt extraction if we have a URL
        if url := input_state.get('company_url'):
            msg += f"\n🌐 Analyzing company website: {url}"
            try:
                search_results = await self.tavily_client.extract(url)
                for item in search_results.get("results", []):
                    url = item.get('url')
                    raw_content = item.get("raw_content", "")
                    site_scrape[url] = {'url': url, 'raw_content': raw_content}
                msg += f"\n✅ Successfully extracted content from website"
            except Exception as e:
                error_msg = f"⚠️ Error extracting website content: {str(e)}"
                print(error_msg)
                msg += f"\n{error_msg}"
        else:
            msg += "\n⏩ No company URL provided, proceeding directly to research phase"

        # Add context about what information we have
        if hq := input_state.get('hq_location'):
            msg += f"\n📍 Company HQ: {hq}"
        if industry := input_state.get('industry'):
            msg += f"\n🏭 Industry: {industry}"
        
        # Initialize ResearchState with input information
        return {
            # Copy input fields
            "company": input_state.get('company'),
            "company_url": input_state.get('company_url'),
            "hq_location": input_state.get('hq_location'),
            "industry": input_state.get('industry'),
            # Initialize research fields
            "messages": [AIMessage(content=msg)],
            "site_scrape": site_scrape,
        }

    async def run(self, state: InputState) -> ResearchState:
        return await self.initial_search(state)
