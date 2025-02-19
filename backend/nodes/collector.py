from langchain_core.messages import AIMessage
from ..classes import ResearchState

class Collector:
    """Collects and organizes all research data before curation."""

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
        
        for data_field, label in research_types.items():
            data = state.get(data_field, {})
            if data:
                msg.append(f"• {label}: {len(data)} documents collected")
            else:
                msg.append(f"• {label}: No data found")
        
        # Update state with collection message
        messages = state.get('messages', [])
        messages.append(AIMessage(content="\n".join(msg)))
        state['messages'] = messages
        
        await state.get('websocket_manager').send_status_update(
            job_id=state.get('job_id'),
            status="processing",
            message="Collecting research data",
            result={"step": "Collection"}
        )
        
        return state

    async def run(self, state: ResearchState) -> ResearchState:
        return await self.collect(state)

    async def collect_data(self, state: ResearchState) -> ResearchState:
        """Collect and merge all research data."""
        company = state.get('company', 'Unknown Company')
        
        # Send initial status
        if websocket_manager := state.get('websocket_manager'):
            if job_id := state.get('job_id'):
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="processing",
                    message="Collecting research data",
                    result={"step": "Collection"}
                )

        # Check if we have any data from researchers
        has_data = any([
            state.get('financial_data'),
            state.get('news_data'),
            state.get('industry_data'),
            state.get('company_data')
        ])

        if not has_data:
            # Send error status if no data was collected
            if websocket_manager and job_id:
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="error",
                    message="No research data was collected. Please try again.",
                    error="Research failed to collect any data"
                )
            return state

        # Continue with normal collection... 