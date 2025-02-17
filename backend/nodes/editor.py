from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from typing import Dict, Any, List
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)

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

    async def edit_report(self, state: ResearchState, briefings: Dict[str, str], context: Dict[str, Any]) -> str:
        """Compile section briefings into a final report and update the state."""
        company = context['company']
        industry = context.get('industry', 'Unknown')
        
        logger.info(f"Starting report compilation for {company}")
        logger.info(f"Available briefing sections: {list(briefings.keys())}")
        
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
                logger.info(f"Adding {section_title} section with {len(content)} characters")
                formatted_briefings.append(f"{section_title}\n{'='*40}\n{content}\n")
            else:
                logger.info(f"Missing {section_title} section")
        
        if not formatted_briefings:
            logger.error("No briefing sections available to compile!")
            return ""
            
        logger.info(f"Compiled {len(formatted_briefings)} sections for editing")
        
        prompt = f"""You are creating the final research report about {company} in the {industry} industry.
The following sections contain bullet-point information gathered from various sources.

{chr(10).join(formatted_briefings)}

Create a well-structured final report that:
1. Maintains the distinct sections with their original headers
3. Ensures information flows logically within sections
4. Removes any redundant / repetitive points between sections
5. Groups related points together within each section
6. Maintains factual, concise language throughout
7. Eliminates any points that are not relevant to the company

Format Requirements:
- Do not add any introductions or conclusions
- Do not add transitional text between sections
- Keep each point clear and factual
- Ensure information is current as of {datetime.now().strftime("%Y-%m-%d")}

Return the final report. No explanation."""

        # Get edited content from LLM
        logger.info("Sending content to LLM for editing")
        response = await self.llm.ainvoke(prompt)
        edited_content = response.content
        
        logger.info(f"Received edited content from LLM ({len(edited_content)} characters)")
        
        # Format references section
        reference_lines = ["\n\n📚 References\n" + "="*40 + "\n"]
        for url in state.get('references', []):
            reference_lines.append(f"• {url}")

        # Combine content and references
        final_report = edited_content + "\n".join(reference_lines)
        logger.info(f"Final report compiled with {len(final_report)} characters")
        
        # Log the first 500 characters of the report for verification
        logger.info("Final report:")
        logger.info("-" * 50)
        logger.info(final_report)
        logger.info("-" * 50)
        
        # Update the state with the final report
        state['report'] = final_report
        
        return final_report

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
            logger.error("No briefings found in state")
        else:
            msg.append(f"\n• Found {len(briefings)} section briefings to compile")
            logger.info(f"Found briefings for sections: {list(briefings.keys())}")
            
            # Get references from state
            references = state.get('references', [])
            logger.info(f"References found in state: {len(references)} items")
            
            # Debug log for references
            if references:
                logger.info(f"Sample reference: {references[0]}")
            else:
                logger.error("No references found in state!")
                logger.error(f"Available state keys: {list(state.keys())}")
            
            # Compile the final report
            compiled_report = await self.edit_report(state, briefings, context)
            
            if not compiled_report or not compiled_report.strip():
                logger.error("Compiled report is empty!")
                state['report'] = None
                msg.append("\n⚠️ Error: Failed to generate report content")
            else:
                state['report'] = compiled_report
                logger.info(f"Successfully compiled report with {len(compiled_report)} characters")
                msg.append("\n✅ Report compilation complete")
            
            # Print completion message
            print(f"\n{'='*80}")
            print(f"Report compilation completed for {company}")
            print(f"Sections included: {', '.join(briefings.keys())}")
            print(f"Report length: {len(compiled_report)} characters")
            print(f"{'='*80}")
        
        # Update state with compilation message
        messages = state.get('messages', [])
        messages.append(AIMessage(content="\n".join(msg)))
        state['messages'] = messages
        
        # Ensure references are preserved in state
        if references:
            state['references'] = references
        
        return state

    async def run(self, state: ResearchState) -> ResearchState:
        return await self.compile_briefings(state) 