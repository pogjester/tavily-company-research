from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from typing import Dict, Any, Union, List
import os
import logging

from ..classes import ResearchState

logger = logging.getLogger(__name__)

class Briefing:
    """Creates individual briefings for each research category."""
    
    def __init__(self) -> None:
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
            
        self.llm = ChatOpenAI(
            model_name="gpt-4o-mini",
            temperature=0,
            max_tokens=4096,
            api_key=openai_key
        )
        
        # Maximum content length per document (roughly 2000 tokens)
        self.max_doc_length = 8000

    async def generate_category_briefing(self, docs: Union[Dict[str, Any], List[Dict[str, Any]]], category: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a briefing for a specific research category."""
        company = context['company']
        industry = context.get('industry', 'Unknown')
        
        logger.info(f"Generating {category} briefing for {company}")
        logger.info(f"Processing {len(docs)} documents")
        
        # Create category-specific prompts with explicit formatting instructions
        prompts = {
            'financial': rf"""You are analyzing financial information about {company}.
Based on the provided documents, create a concise financial briefing that covers:
- Key financial metrics and performance
- Market valuation and growth
- Funding and investment status
- Notable financial developments

Format your response as a series of bullet points only. Do not include any introductions, transitions, or conclusions.""",
            
            'news': rf"""You are analyzing recent news about {company}.
Based on the provided documents, create a concise news briefing that covers:
- Major recent developments
- Key announcements
- Notable partnerships or deals
- Public perception and media coverage

Format your response as a series of bullet points only. Do not include any introductions, transitions, or conclusions.""",
            
            'industry': rf"""You are analyzing {company}'s position in the {industry} industry.
Based on the provided documents, create a concise industry briefing that covers:
- Market position and share
- Competitive landscape
- Industry trends and challenges
- Regulatory environment

Format your response as a series of bullet points only. Do not include any introductions, transitions, or conclusions.""",
            
            'company': rf"""You are analyzing core information about {company}.
Based on the provided documents, create a concise company briefing that covers:
- Core products and services
- Business model and strategy
- Leadership and management
- Technology and innovation
- Market presence and expansion

Format your response as a series of bullet points only. Do not include any introductions, transitions, or conclusions."""
        }
        
        # Convert docs to a list of (url, doc) tuples
        if isinstance(docs, dict):
            items = list(docs.items())
        else:  # List input
            items = [(doc.get('url', f'doc_{i}'), doc) for i, doc in enumerate(docs)]
        
        # Prepare all documents for analysis
        doc_texts = []
        references = []
        total_length = 0
        
        # Sort items by evaluation score if available
        sorted_items = sorted(
            items,
            key=lambda x: float(x[1].get('evaluation', {}).get('overall_score', '0')),
            reverse=True
        )
        
        for url, doc in sorted_items:
            # Create reference first
            ref_data = {
                "url": str(url),
                "title": str(doc.get('title', 'Untitled')),
                "query": str(doc.get('query', 'General research')),
                "source": str(doc.get('source', 'web_search')),
                "score": str(doc.get('evaluation', {}).get('overall_score', '0'))
            }
            references.append(ref_data)
            
            # Process document content
            title = doc.get('title', '')
            content = doc.get('raw_content') or doc.get('content', '')
            
            # Truncate content if too long
            if len(content) > self.max_doc_length:
                content = content[:self.max_doc_length] + "... [content truncated]"
            
            doc_text = rf"Title: {title}\n\nContent: {content}"
            doc_length = len(doc_text)
            
            # Only add document if we haven't exceeded ~32k tokens (128k chars)
            if total_length + doc_length < 120000:  # Conservative limit
                doc_texts.append(doc_text)
                total_length += doc_length
            else:
                break  # Stop adding documents if we're approaching the context limit
        
        # Build the prompt with all documents
        separator = r"\n" + "-" * 40 + r"\n"
        prompt = (
            rf"""{prompts.get(category, 'Create a research briefing based on the provided documents.')}

Analyze the following documents and extract key information:
{separator}
{separator.join(doc_texts)}
{separator}

Create a clear, well-organized set of bullet points that captures the key information.
Focus on factual, verifiable information.
Do not include any introductions, transitions, or conclusions."""
        )
        
        try:
            logger.info("Sending content to LLM for analysis")
            response = await self.llm.ainvoke(prompt)
            content = response.content.strip()
            
            if not content:
                logger.error(f"Received empty content from LLM for {category} briefing")
                return {'content': '', 'references': []}
                
            logger.info(f"Generated {category} briefing with {len(content)} characters")
            
            # Log a preview of the content
            logger.info("First 500 characters of the briefing:")
            logger.info("-" * 50)
            logger.info(content[:500])
            logger.info("-" * 50)
            
            return {
                'content': content,
                'references': references
            }
            
        except Exception as e:
            logger.error(f"Error generating {category} briefing: {str(e)}")
            return {'content': '', 'references': []}

    async def create_briefings(self, state: ResearchState) -> ResearchState:
        """Create individual briefings for all research categories."""
        company = state.get('company', 'Unknown Company')
        context = {
            "company": company,
            "industry": state.get('industry', 'Unknown'),
            "hq_location": state.get('hq_location', 'Unknown')
        }
        
        logger.info(f"Starting briefing generation for {company}")
        print(f"\n{'='*80}")
        print(f"Creating section briefings for {company}")
        
        # Process each category of curated data
        categories = {
            'financial_data': '💰 Financial',
            'news_data': '📰 News',
            'industry_data': '🏭 Industry',
            'company_data': '🏢 Company'
        }
        
        briefings = {}
        references = {}
        msg = [f"📋 Creating section briefings for {company}:"]
        
        for data_field, label in categories.items():
            curated_field = f'curated_{data_field}'
            curated_data = state.get(curated_field, {})
            
            if curated_data:
                logger.info(f"Processing {label} section ({len(curated_data)} documents)")
                msg.append(f"\n• Processing {label} section ({len(curated_data)} documents)...")
                category = data_field.replace('_data', '')
                result = await self.generate_category_briefing(curated_data, category, context)
                
                if result['content']:
                    briefings[str(category)] = result['content']
                    references[str(category)] = result['references']
                    msg.append(f"  ✓ Section completed ({len(result['content'])} characters)")
                    logger.info(f"Generated {category} briefing with {len(result['content'])} characters")
                else:
                    msg.append("  ⚠️ Failed to generate section content")
                    logger.error(f"Failed to generate content for {category} section")
            else:
                msg.append(f"\n• No data available for {label} section")
                logger.warning(f"No curated data found for {label} section")
        
        # Update state with section briefings and references
        state['briefings'] = briefings
        state['references'] = references
        
        # Add processing summary
        if briefings:
            msg.append(f"\n✓ Generated {len(briefings)} section briefings")
            logger.info(f"Successfully generated {len(briefings)} section briefings")
            
            # Log briefing lengths
            for category, content in briefings.items():
                logger.info(f"{category} briefing length: {len(content)} characters")
        else:
            msg.append("\n⚠️ No section briefings could be generated")
            logger.error("Failed to generate any section briefings")
        
        messages = state.get('messages', [])
        messages.append(AIMessage(content="\n".join(msg)))
        state['messages'] = messages
        
        return state

    async def run(self, state: ResearchState) -> ResearchState:
        return await self.create_briefings(state)
