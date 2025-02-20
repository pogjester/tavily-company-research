from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from typing import Dict, Any
import google.generativeai as genai
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)

from ..classes import ResearchState

class Editor:
    """Compiles individual section briefings into a cohesive final report."""
    
    def __init__(self) -> None:
        # openai_key = os.getenv("OPENAI_API_KEY")
        # if not openai_key:
        #     raise ValueError("OPENAI_API_KEY environment variable is not set")
            
        # self.llm = ChatOpenAI(
        #     model_name="gpt-4o",
        #     temperature=0,
        #     max_tokens=4096,
        #     api_key=openai_key,
        # )
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        if not self.gemini_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        
        # Configure Gemini
        genai.configure(api_key=self.gemini_key)
        self.gemini_model = genai.GenerativeModel('gemini-2.0-flash')

    async def compile_briefings(self, state: ResearchState) -> ResearchState:
        """Compile individual briefing categories from state into a final report."""
        company = state.get('company', 'Unknown Company')
        
        # Send initial compilation status
        if websocket_manager := state.get('websocket_manager'):
            if job_id := state.get('job_id'):
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="processing",
                    message=f"Starting report compilation for {company}",
                    result={
                        "step": "Editor",
                        "substep": "initialization"
                    }
                )

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

        # Send briefing collection status
        if websocket_manager := state.get('websocket_manager'):
            if job_id := state.get('job_id'):
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="processing",
                    message="Collecting section briefings",
                    result={
                        "step": "Editor",
                        "substep": "collecting_briefings"
                    }
                )

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
    
    async def edit_report(self, state: ResearchState, briefings: Dict[str, str], context: Dict[str, Any]) -> str:
        """Compile section briefings into a final report and update the state."""
        company = context.get('company', 'Unknown')
        industry = context.get('industry', 'Unknown')
        hq = context.get('hq_location', 'Unknown')
        
        logger.info(f"Starting report compilation for {company}")
        logger.info(f"Available briefing sections: {list(briefings.keys())}")
        
        # Send editing start status
        if websocket_manager := state.get('websocket_manager'):
            if job_id := state.get('job_id'):
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="processing",
                    message=f"Editing report for {company}",
                    result={
                        "step": "Editor",
                        "substep": "editing",
                        "sections": list(briefings.keys())
                    }
                )

        # First compile sections
        combined_content = "\n\n".join(
            f"## {header.title()}\n---\n{content}"
            for header, content in briefings.items()
        )
        
        # Then deduplicate
        if websocket_manager := state.get('websocket_manager'):
            if job_id := state.get('job_id'):
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="processing",
                    message="Removing duplicate information",
                    result={
                        "step": "Editor",
                        "substep": "deduplication"
                    }
                )
        
        final_report = await self.deduplicate_content(combined_content, company)
        
        # Add references
        if references := state.get('references', []):
            reference_lines = ["\n\n## References\n---\n"]
            for ref in references:
                reference_lines.append(f"• [{ref}]({ref})")
            final_report += "\n".join(reference_lines)
        
        logger.info(f"Final report compiled with {len(final_report)} characters")
        
        # Log a preview of the report
        logger.info("Final report preview:")
        logger.info(final_report[:500])
        
        # Update state with the final report
        state['report'] = final_report
        
        return final_report

    async def deduplicate_content(self, content: str, company: str) -> str:
        """Remove repetitive information from the report."""
        
        prompt = f"""You are cleaning up a research report about {company}. The report has some repeated information across sections.

Original report:
{content}

Create a new version that:
1. Removes all duplicate information, keeping only the most detailed/relevant instance
2. Maintains all unique information
3. Keeps the original section structure and headers
4. Preserves the bullet-point format
5. Does not add any new text or transitions

Return only the deduplicated report. No explanations."""

        try:
            response = self.gemini_model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error deduplicating report: {e}")
            return content  # Return original content if deduplication fails

    async def run(self, state: ResearchState) -> ResearchState:
        return await self.compile_briefings(state)