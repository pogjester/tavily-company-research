from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from typing import Dict, Any, List
from datetime import datetime
import os

from ..classes import ResearchState

class Editor:
    """Compiles individual section briefings into a cohesive final report."""
    
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

    async def edit_report(self, briefings: Dict[str, str], context: Dict[str, Any], references: Dict[str, List[Dict[str, str]]]) -> str:
        """Compile section briefings into a final report."""
        company = context['company']
        industry = context.get('industry', 'Unknown')
        
        sections = {
            'company': '🏢 Company Overview',
            'industry': '🏭 Industry Analysis',
            'financial': '💰 Financial Analysis',
            'news': '📰 Recent Developments'
        }
        
        # Prepare the briefings in a structured format
        formatted_briefings = []
        for category, section_title in sections.items():
            if content := briefings.get(category):
                formatted_briefings.append(f"{section_title}\n{'='*40}\n{content}\n")
        
        prompt = rf"""You are creating the final research report about {company} in the {industry} industry.
The following sections contain bullet-point information gathered from various sources.

{"\n\n".join(formatted_briefings)}

Create a well-structured final report that:
1. Maintains the distinct sections with their original headers
2. Preserves the bullet-point format within each section
3. Ensures information flows logically within sections
4. Removes any redundant points between sections
5. Groups related points together within each section
6. Maintains factual, concise language throughout

Format Requirements:
- Keep the original section headers
- Maintain bullet points (do not convert to paragraphs)
- Do not add any introductions or conclusions
- Do not add transitional text between sections
- Keep each point clear and factual
- Ensure information is current as of {datetime.now().strftime("%Y-%m-%d")}

Return the final report maintaining the section structure and bullet-point format."""

        # Get edited content from LLM
        response = await self.llm.ainvoke(prompt)
        edited_content = response.content

        # Format references section
        reference_lines = ["\n\n📚 References\n" + "="*40]
        for category, refs in references.items():
            if refs:
                reference_lines.append(f"\n{sections[category]} Sources:")
                for ref in sorted(refs, key=lambda x: float(x['score']), reverse=True)[:5]:  # Top 5 sources per section
                    reference_lines.append(f"• {ref['title']}")
                    reference_lines.append(f"  {ref['url']}")
                    reference_lines.append(f"  Score: {ref['score']}")
        
        # Combine content and references
        return edited_content + "\n".join(reference_lines)

    async def compile_briefings(self, state: ResearchState) -> ResearchState:
        """Compile section briefings into a final report."""
        company = state.get('company', 'Unknown Company')
        context = {
            "company": company,
            "industry": state.get('industry', 'Unknown'),
            "hq_location": state.get('hq_location', 'Unknown')
        }
        
        msg = [f"📑 Compiling final report for {company}..."]
        
        briefings = state.get('briefings', {})
        if not briefings:
            msg.append("\n⚠️ No section briefings available to compile")
            state['report'] = None
        else:
            msg.append(f"\n• Found {len(briefings)} section briefings to compile")
            
            # Get references from state
            references = state.get('references', {})
            
            # Compile the final report
            compiled_report = await self.edit_report(briefings, context, references)
            state['report'] = compiled_report
            
            msg.append("\n✅ Report compilation complete")
            
            # Print completion message
            print(f"\n{'='*80}")
            print(f"Report compilation completed for {company}")
            print(f"Sections included: {', '.join(briefings.keys())}")
            print(f"{'='*80}")
        
        # Update state with compilation message
        messages = state.get('messages', [])
        messages.append(AIMessage(content="\n".join(msg)))
        state['messages'] = messages
        
        return state

    async def run(self, state: ResearchState) -> ResearchState:
        return await self.compile_briefings(state) 