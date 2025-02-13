from langchain_core.messages import AIMessage
from langchain_anthropic import ChatAnthropic
from typing import Dict, Any
import os

from ..classes import ResearchState

class Briefing:
    """Creates briefings for each research category using curated documents."""
    
    def __init__(self) -> None:
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if not anthropic_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
            
        self.llm = ChatAnthropic(
            model_name="claude-3-haiku-20240307",
            temperature=0,
            max_tokens=1024
        )

    async def generate_category_briefing(self, docs: Dict[str, Any], category: str, context: Dict[str, Any]) -> str:
        """Generate a briefing for a specific category of research."""
        company = context['company']
        industry = context.get('industry', 'Unknown')
        
        # Create category-specific prompts
        prompts = {
            'financial': rf"""You are analyzing financial information about {company} in the {industry} industry.
Based on the provided documents, create a concise financial briefing that covers:
- Key financial metrics and performance
- Market valuation and growth
- Funding and investment status
- Notable financial developments""",
            
            'news': rf"""You are analyzing recent news about {company} in the {industry} industry.
Based on the provided documents, create a concise news briefing that covers:
- Major recent developments
- Key announcements
- Notable partnerships or deals
- Public perception and media coverage""",
            
            'industry': rf"""You are analyzing {company}'s position in the {industry} industry.
Based on the provided documents, create a concise industry briefing that covers:
- Market position and share
- Competitive landscape
- Industry trends and challenges
- Regulatory environment""",
            
            'company': rf"""You are analyzing core information about {company} in the {industry} industry.
Based on the provided documents, create a concise company briefing that covers:
- Core products and services
- Business model and strategy
- Leadership and management
- Technology and innovation
- Market presence and expansion"""
        }
        
        # Prepare documents for analysis
        doc_texts = []
        for doc in docs.values():
            title = doc.get('title', '')
            content = doc.get('raw_content') or doc.get('content', '')
            doc_texts.append(rf"Title: {title}\n\nContent: {content}")

        # Build the final prompt
        separator = r"\n" + "-" * 40 + r"\n"
        prompt = (
            rf"""{prompts.get(category, 'Create a concise briefing based on the provided documents.')}

Documents to analyze:
{separator}
{separator.join(doc_texts)}
{separator}

Create a clear, well-organized briefing that extracts and synthesizes the key information.
Focus on factual, verifiable information.
Use bullet points where appropriate for clarity."""
        )
        
        response = await self.llm.ainvoke(prompt)
        return response.content

    async def create_briefings(self, state: ResearchState) -> ResearchState:
        """Create briefings for all research categories."""
        company = state.get('company', 'Unknown Company')
        context = {
            "company": company,
            "industry": state.get('industry', 'Unknown'),
            "hq_location": state.get('hq_location', 'Unknown')
        }
        
        msg = [f"📋 Creating research briefings for {company}:"]

        # Process each category of curated data
        categories = {
            'financial_data': '💰 Financial',
            'news_data': '📰 News',
            'industry_data': '🏭 Industry',
            'company_data': '🏢 Company'
        }
        
        briefings = {}
        for data_field, label in categories.items():
            curated_field = f'curated_{data_field}'
            curated_data = state.get(curated_field, {})
            
            if curated_data:
                msg.append(f"\n• Generating {label} briefing from {len(curated_data)} documents...")
                category = data_field.replace('_data', '')
                briefing = await self.generate_category_briefing(curated_data, category, context)
                briefings[category] = briefing
                msg.append("  ✓ Briefing generated")
                
                # Add the actual briefing content to the message
                msg.append(f"\n{label} Briefing:")
                msg.append("=" * 40)
                msg.append(briefing)
                msg.append("=" * 40 + "\n")

                print(f"Curated data for {label}: {bool(curated_data)}")
                print(f"Generated briefing for {category}: {briefing if curated_data else 'No briefing generated'}")
                print(f"State after briefing generation: {state}")
            else:
                msg.append(f"\n• No curated {label} documents available")
        
        # Update state with briefings and message
        state['briefings'] = briefings
        
        # Add summary of generated briefings
        if briefings:
            msg.append("\n📊 Briefing Summary:")
            msg.append(f"Generated {len(briefings)} briefings for {company}")
            for category in briefings.keys():
                msg.append(f"- {categories.get(category + '_data', category)} briefing completed")
        else:
            msg.append("\n⚠️ No briefings were generated due to lack of curated data")
        
        messages = state.get('messages', [])
        messages.append(AIMessage(content="\n".join(msg)))
        state['messages'] = messages
        
        # Print briefings for immediate visibility
        print(f"\n{'='*80}\n🔍 Generated Briefings for {company}:\n{'='*80}")
        for category, content in briefings.items():
            print(f"\n{categories.get(category + '_data', category)}:")
            print("-" * 40)
            print(content)
            print("=" * 80)
        return state

    async def run(self, state: ResearchState) -> ResearchState:
        return await self.create_briefings(state)
