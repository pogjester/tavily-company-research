from langchain_core.messages import AIMessage
from datetime import datetime
import os
from tavily import AsyncTavilyClient

from ..classes import ResearchState

class Collector:
    """Collects and organizes all research data before curation."""
    
    def __init__(self) -> None:
        tavily_key = os.getenv("TAVILY_API_KEY")
        if not tavily_key:
            raise ValueError("TAVILY_API_KEY environment variable is not set")
        self.tavily_client = AsyncTavilyClient(api_key=tavily_key)

    async def extract_content(self, urls: list) -> dict:
        """Extract full content from URLs using Tavily."""
        content_map = {}
        extraction_stats = {
            'total': len(urls),
            'success': 0,
            'failed': 0,
            'empty': 0,
            'errors': {}
        }
        
        for url in urls:
            try:
                print(f"Extracting content from: {url}")
                result = await self.tavily_client.extract(url)
                
                if not result:
                    print(f"No result returned for: {url}")
                    extraction_stats['empty'] += 1
                    content_map[url] = ''
                    continue
                    
                if 'results' not in result:
                    print(f"No 'results' in response for: {url}")
                    extraction_stats['empty'] += 1
                    content_map[url] = ''
                    continue
                    
                raw_content = result['results'][0].get('raw_content', '')
                if not raw_content:
                    print(f"No raw_content in result for: {url}")
                    extraction_stats['empty'] += 1
                else:
                    print(f"Successfully extracted {len(raw_content)} chars from: {url}")
                    extraction_stats['success'] += 1
                
                content_map[url] = raw_content
                
            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e)
                print(f"Error extracting from {url}: {error_type} - {error_msg}")
                extraction_stats['failed'] += 1
                extraction_stats['errors'][error_type] = extraction_stats['errors'].get(error_type, 0) + 1
                content_map[url] = ''
                
        return content_map, extraction_stats

    async def collect(self, state: ResearchState) -> ResearchState:
        """Collect and verify all research data is present."""
        company = state.get('company', 'Unknown Company')
        msg = [f"📦 Collecting research data for {company}:"]
        
        # Check each type of research data
        research_types = {
            'financial_data': '💰 Financial',
            'news_data': '📰 News',
            'industry_data': '🏭 Industry',
            'company_data': '🏢 Company'
        }
        
        all_present = True
        total_stats = {'success': 0, 'failed': 0, 'empty': 0, 'errors': {}}
        
        for data_field, label in research_types.items():
            data = state.get(data_field, {})
            if data:
                msg.append(f"• {label}: {len(data)} documents collected")
                
                # Extract raw content for URLs
                urls = list(data.keys())
                msg.append(f"  📥 Extracting content from {len(urls)} URLs...")
                content_map, stats = await self.extract_content(urls)
                
                # Update total stats
                total_stats['success'] += stats['success']
                total_stats['failed'] += stats['failed']
                total_stats['empty'] += stats['empty']
                for error_type, count in stats['errors'].items():
                    total_stats['errors'][error_type] = total_stats['errors'].get(error_type, 0) + count
                
                # Update documents with raw content
                enriched_data = {}
                for url, doc in data.items():
                    enriched_data[url] = {
                        **doc,
                        'raw_content': content_map.get(url, '')
                    }
                state[data_field] = enriched_data
                
                msg.append(f"  ✓ Content extraction results:")
                msg.append(f"    • Successful: {stats['success']}/{stats['total']}")
                msg.append(f"    • Failed: {stats['failed']}")
                msg.append(f"    • Empty results: {stats['empty']}")
                if stats['errors']:
                    msg.append("    • Errors encountered:")
                    for error_type, count in stats['errors'].items():
                        msg.append(f"      - {error_type}: {count}")
            else:
                msg.append(f"• {label}: No data found")
                all_present = False
        
        if not all_present:
            msg.append("\n⚠️ Warning: Some research data is missing")
            
        msg.append("\n📊 Total extraction statistics:")
        msg.append(f"  • Total successful extractions: {total_stats['success']}")
        msg.append(f"  • Total failed extractions: {total_stats['failed']}")
        msg.append(f"  • Total empty results: {total_stats['empty']}")
        if total_stats['errors']:
            msg.append("  • Error breakdown:")
            for error_type, count in total_stats['errors'].items():
                msg.append(f"    - {error_type}: {count}")
        
        # Update state with collection message
        messages = state.get('messages', [])
        messages.append(AIMessage(content="\n".join(msg)))
        state['messages'] = messages
        
        return state

    async def run(self, state: ResearchState) -> ResearchState:
        return await self.collect(state) 