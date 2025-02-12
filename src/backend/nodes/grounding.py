from langchain_core.messages import AIMessage
from tavily import AsyncTavilyClient
import os

from ..classes import InputState, ResearchState

class GroundingNode:
    def __init__(self) -> None:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("TAVILY_API_KEY environment variable is not set")
        self.tavily_client = AsyncTavilyClient(api_key=api_key)

    async def initial_search(self, input_state: InputState) -> ResearchState:
        company = input_state.get('company', 'Unknown Company')
        msg = f"🎯 Initiating initial grounding for company '{company}'...\n"
        site_scrape = {}

        # Only attempt extraction if we have a URL
        if url := input_state.get('company_url'):
            try:
                search_results = await self.tavily_client.extract(url)
                for item in search_results.get("results", []):
                    url = item.get('url')
                    raw_content = item.get("raw_content", "")
                    site_scrape[url] = {'url': url, 'raw_content': raw_content}
                msg += f"\n✅ Successfully extracted content from {url}"
            except Exception as e:
                error_msg = f"⚠️ Error attempting to use Tavily Extract on {url}: {e}"
                print(error_msg)
                msg += f"\n{error_msg}"
        else:
            msg += "\n⚠️ No company URL provided for extraction"

        # Add any additional context we have
        if hq := input_state.get('hq_location'):
            msg += f"\n📍 Company HQ: {hq}"
        if industry := input_state.get('industry'):
            msg += f"\n🏭 Industry: {industry}"
        
        return {"messages": [AIMessage(content=msg)], "site_scrape": site_scrape}

    async def run(self, state: InputState) -> ResearchState:
        return await self.initial_search(state)
