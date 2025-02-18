from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from typing import Dict, Any, Union, List
import os
import logging

from ..classes import ResearchState

logger = logging.getLogger(__name__)

class Briefing:
    """Creates briefings for each research category and updates the ResearchState."""
    
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
        self.max_doc_length = 8000  # Maximum document content length

    async def generate_category_briefing(
        self, docs: Union[Dict[str, Any], List[Dict[str, Any]]], 
        category: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        company = context.get('company', 'Unknown')
        industry = context.get('industry', 'Unknown')
        logger.info(f"Generating {category} briefing for {company} using {len(docs)} documents")

        prompts = {
            'financial': f"""You are analyzing financial information about {company}.
Based on the provided documents, create a concise briefing covering key financial metrics, market valuation, funding status, and notable developments. Don't provide any information about the industry or the company. Never provide generic descriptions of GDP trends or broader economic trends.
Format your response as bullet points without introductions or conclusions.""",
            'news': f"""You are analyzing recent news about {company}.
Based on the provided documents, create a concise briefing covering major developments, key announcements, partnerships, and public perception. Don't provide any basic descriptions of the company.
Format your response as bullet points without introductions or conclusions.""",
            'industry': f"""You are analyzing {company}'s position in the {industry} industry.
Based on the provided documents, create a concise briefing covering market position, competitive landscape, trends, and regulatory environment. Don't provide any generic descriptions of the company. 
Format your response as bullet points without introductions or conclusions.""",
            'company': f"""You are analyzing core information about {company}.
Based on the provided documents, create a concise but detailed company briefing covering offerings, history,business model, leadership, and market presence. Start at the highest level and work your way down to the most specific.
Format your response as bullet points without introductions or conclusions."""
        }
        
        # Normalize docs to a list of (url, doc) tuples
        items = list(docs.items()) if isinstance(docs, dict) else [
            (doc.get('url', f'doc_{i}'), doc) for i, doc in enumerate(docs)
        ]
        # Sort documents by evaluation score (highest first)
        sorted_items = sorted(
            items, 
            key=lambda x: float(x[1].get('evaluation', {}).get('overall_score', '0')), 
            reverse=True
        )
        
        doc_texts = []
        total_length = 0
        for _ , doc in sorted_items:
            title = doc.get('title', '')
            content = doc.get('raw_content') or doc.get('content', '')
            if len(content) > self.max_doc_length:
                content = content[:self.max_doc_length] + "... [content truncated]"
            doc_entry = f"Title: {title}\n\nContent: {content}"
            if total_length + len(doc_entry) < 120000:  # Keep under limit
                doc_texts.append(doc_entry)
                total_length += len(doc_entry)
            else:
                break
        
        separator = "\n" + "-" * 40 + "\n"
        prompt = f"""{prompts.get(category, 'Create a research briefing based on the provided documents.')}

Analyze the following documents and extract key information about {company} in the {industry} industry:
{separator}{separator.join(doc_texts)}{separator}

Create a set of bullet points with factual, verifiable information without introductions or conclusions."""
        
        try:
            logger.info("Sending prompt to LLM")
            response = await self.llm.ainvoke(prompt)
            content = response.content.strip()
            if not content:
                logger.error(f"Empty response from LLM for {category} briefing")
                return {'content': ''}
            return {'content': content}
        except Exception as e:
            logger.error(f"Error generating {category} briefing: {e}")
            return {'content': ''}

    async def create_briefings(self, state: ResearchState) -> ResearchState:
        company = state.get('company', 'Unknown Company')
        context = {
            "company": company,
            "industry": state.get('industry', 'Unknown'),
            "hq_location": state.get('hq_location', 'Unknown')
        }
        logger.info(f"Creating section briefings for {company}")
        
        # Mapping of curated data fields to briefing categories
        categories = {
            'financial_data': 'financial',
            'news_data': 'news',
            'industry_data': 'industry',
            'company_data': 'company'
        }
        
        # Initialize a dict for all briefings
        briefings = {}
        summary = [f"Creating section briefings for {company}:"]
        
        for data_field, cat in categories.items():
            curated_key = f'curated_{data_field}'
            curated_data = state.get(curated_key, {})
            if curated_data:
                logger.info(f"Processing {data_field} with {len(curated_data)} documents")
                summary.append(f"Processing {data_field} ({len(curated_data)} documents)...")
                result = await self.generate_category_briefing(curated_data, cat, context)
                if result['content']:
                    # Store briefing under both a collective dict and a separate key
                    briefings[cat] = result['content']
                    state[f'{cat}_briefing'] = result['content']
                    print(f"Briefing for {data_field}: {result['content']}")
                    summary.append(f"Completed {data_field} ({len(result['content'])} characters)")
                else:
                    summary.append(f"Failed to generate briefing for {data_field}")
            else:
                summary.append(f"No data available for {data_field}")
        
        state['briefings'] = briefings
        state.setdefault('messages', []).append(AIMessage(content="\n".join(summary)))
        return state

    async def run(self, state: ResearchState) -> ResearchState:
        return await self.create_briefings(state)