from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from typing import Dict, Any
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
            model_name="gpt-4o",
            temperature=0,
            max_tokens=4096,
            api_key=openai_key,
        )

    async def edit_report(self, state: ResearchState, briefings: Dict[str, str], context: Dict[str, Any]) -> str:
        """Compile section briefings into a final report and update the state."""
        company = context.get('company', 'Unknown')
        industry = context.get('industry', 'Unknown')
        hq = context.get('hq_location', 'Unknown')
        
        logger.info(f"Starting report compilation for {company}")
        logger.info(f"Available briefing sections: {list(briefings.keys())}")
        
        # Combine all briefings into a single content block
        combined_content = "\n\n".join(
            f"## {header.title()}\n---\n{content}"  # Replace === with ---
            for header, content in briefings.items()
        )
        
        prompt = f"""You are creating a comprehensive research report about {company} in the {industry} industry (HQ:{hq}).
The following contains bullet-point information for various sections:

{combined_content}

Create a well-structured, detailed final report that:
1. Maintains the distinct sections with their original headers
2. Eliminates repetition (critical!)
3. Maintains factual, concise language throughout
4. Eliminates any points that are not relevant to {company} in the {industry} industry

Format Requirements:
- Do not add any introductions or conclusions
- Do not add transitional text between sections
- Ensure information is current as of {datetime.now().strftime("%Y-%m-%d")}

Return only the formatted report. No explanation."""

        try:
            await state.get('websocket_manager').send_status_update(
                job_id=state.get('job_id'),
                status="processing",
                message="Compiling the final research report",
                result={"step": "Editor"}
            )
            response = await self.llm.ainvoke(prompt)
            final_report = response.content.strip()
            
            if not final_report:
                logger.error("No content generated from briefings")
                return ""

            # Format references
            reference_lines = [
                "\n\n## References\n---\n"  # Match the format of other sections
            ]
            references = state.get('references', [])
            for ref in references:
                # Format as markdown link - URL is both the text and the link
                reference_lines.append(f"• [{ref}]({ref})")
                
            final_report += "\n".join(reference_lines)
            logger.info(f"Final report compiled with {len(final_report)} characters")
            
            # Log a preview of the report
            logger.info("Final report preview:")
            logger.info(final_report[:500])
            
            # Update state with the final report
            state['report'] = final_report
            
            return final_report
            
        except Exception as e:
            logger.error(f"Error generating final report: {e}")
            return ""

    async def compile_briefings(self, state: ResearchState) -> ResearchState:
        """Compile individual briefing categories from state into a final report."""
        company = state.get('company', 'Unknown Company')
        context = {
            "company": company,
            "industry": state.get('industry', 'Unknown'),
            "hq_location": state.get('hq_location', 'Unknown')
        }
        
        msg = [f"📑 Compiling final report for {company}..."]
        
        # Pull individual briefings from dedicated state keys
        briefing_keys = {
            'company': 'company_briefing',
            'industry': 'industry_briefing',
            'financial': 'financial_briefing',
            'news': 'news_briefing'
        }
        individual_briefings = {}
        for category, key in briefing_keys.items():
            if content := state.get(key):
                individual_briefings[category] = content
                msg.append(f"Found {category} briefing ({len(content)} characters)")
            else:
                msg.append(f"No {category} briefing available")
                logger.error(f"Missing state key: {key}")
        
        if not individual_briefings:
            msg.append("\n⚠️ No briefing sections available to compile")
            state['report'] = None
            logger.error("No briefings found in state")
        else:
            compiled_report = await self.edit_report(state, individual_briefings, context)
            if not compiled_report.strip():
                logger.error("Compiled report is empty!")
                state['report'] = None
                msg.append("\n⚠️ Error: Failed to generate report content")
            else:
                state['report'] = compiled_report
                logger.info(f"Successfully compiled report with {len(compiled_report)} characters")
                msg.append("\n✅ Report compilation complete")
                
            print(f"\n{'='*80}")
            print(f"Report compilation completed for {company}")
            print(f"Sections included: {', '.join(individual_briefings.keys())}")
            print(f"Report length: {len(compiled_report)} characters")
            print(f"{'='*80}")
        
        state.setdefault('messages', []).append(AIMessage(content="\n".join(msg)))
  
        return state

    async def run(self, state: ResearchState) -> ResearchState:
        return await self.compile_briefings(state)