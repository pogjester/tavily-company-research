from langchain_core.messages import AIMessage
from typing import Dict, Any
import google.generativeai as genai
import os
import logging

logger = logging.getLogger(__name__)

from ..classes import ResearchState

class Editor:
    """Compiles individual section briefings into a cohesive final report."""
    
    def __init__(self) -> None:
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
        
        # Step 1: Initial Compilation
        if websocket_manager := state.get('websocket_manager'):
            if job_id := state.get('job_id'):
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="processing",
                    message="Compiling initial research report",
                    result={
                        "step": "Editor",
                        "substep": "compilation"
                    }
                )

        initial_report = await self.compile_content(state, briefings, company)

        # Step 2: Deduplication and Cleanup
        if websocket_manager := state.get('websocket_manager'):
            if job_id := state.get('job_id'):
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="processing",
                    message="Cleaning up and organizing report",
                    result={
                        "step": "Editor",
                        "substep": "cleanup"
                    }
                )

        final_report = await self.deduplicate_content(state, initial_report, company)
        
        # Add references and finalize
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

    async def compile_content(self, state: ResearchState, briefings: Dict[str, str], company: str) -> str:
        """Initial compilation of research sections."""
        
        combined_content = "\n\n".join(
            f"## {header.title()}\n---\n{content}"
            for header, content in briefings.items()
        )
        
        prompt = f"""You are compiling a comprehensive research report about {company}.

Original section content:
{combined_content}

Create a comprehensive report on {company} that:
1. Integrates information from all sections into a cohesive narrative
2. Maintains the most important details from each section
3. Organizes information logically within each section
4. Uses clear section headers and structure
5. Preserves all factual information
6. Focuses on the company: {company}

Return the compiled report maintaining the markdown format."""

        try:
            response = self.gemini_model.generate_content(prompt, stream=True)
            
            accumulated_text = ""
            async for chunk in response:
                chunk_text = chunk.text
                print(chunk.text)
                accumulated_text += chunk_text
                
                if websocket_manager := state.get('websocket_manager'):
                    if job_id := state.get('job_id'):
                        await websocket_manager.send_status_update(
                            job_id=job_id,
                            status="report_chunk",
                            message="Compiling initial report",
                            result={
                                "chunk": chunk_text,
                                "step": "Editor"
                            }
                        )
            
            return accumulated_text.strip()
        except Exception as e:
            logger.error(f"Error in initial compilation: {e}")
            return combined_content

    async def deduplicate_content(self, state: ResearchState, content: str, company: str) -> str:
        """Clean up and deduplicate the compiled report."""
        
        prompt = f"""You are an expert editor. You are given a report on {company}.

Current report:
{content}

Create a refined version that:
1. Removes repetitive information
2. Improves the flow and readability
3. Ensures consistent formatting and style
4. Removes sections that don't have any useful content
5. Maintains all unique insights

Return an flawless, detailed, and easily readable report maintaining the markdown format."""

        try:
            response = self.gemini_model.generate_content(prompt, stream=True)
            
            accumulated_text = ""
            async for chunk in response:
                chunk_text = chunk.text
                accumulated_text += chunk_text
                
                if websocket_manager := state.get('websocket_manager'):
                    if job_id := state.get('job_id'):
                        await websocket_manager.send_status_update(
                            job_id=job_id,
                            status="report_chunk",
                            message="Polishing final report",
                            result={
                                "chunk": chunk_text,
                                "step": "Editor"
                            }
                        )
            
            return accumulated_text.strip()
        except Exception as e:
            logger.error(f"Error in deduplication: {e}")
            return content

    async def run(self, state: ResearchState) -> ResearchState:
        return await self.compile_briefings(state)