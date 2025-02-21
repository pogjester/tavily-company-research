from langchain_core.messages import AIMessage
from typing import Dict, Any
import google.generativeai as genai
import os
import logging
from ..utils.markdown import standardize_markdown

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
            try:
                compiled_report = await self.edit_report(state, individual_briefings, context)
                if not compiled_report or not compiled_report.strip():
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
            except Exception as e:
                logger.error(f"Error during report compilation: {e}")
                state['report'] = None
                msg.append(f"\n⚠️ Error during report compilation: {str(e)}")
        
        state.setdefault('messages', []).append(AIMessage(content="\n".join(msg)))
        return state
    
    async def edit_report(self, state: ResearchState, briefings: Dict[str, str], context: Dict[str, Any]) -> str:
        """Compile section briefings into a final report and update the state."""
        try:
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
            if not initial_report:
                logger.error("Initial compilation failed")
                return ""

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
            
            # Ensure final_report is a string before proceeding
            final_report = final_report or ""
            
            # Add references and finalize
            if references := state.get('references', []):
                reference_lines = ["\n\n## References\n---\n"]
                for ref in references:
                    reference_lines.append(f"• [{ref}]({ref})")
                final_report += "\n".join(reference_lines)
            
            # Final step: Standardize markdown format
            final_report = standardize_markdown(final_report)
            
            logger.info(f"Final report compiled with {len(final_report)} characters")
            
            # Log a preview of the report
            logger.info("Final report preview:")
            logger.info(final_report[:500])
            
            # Update state with the final report
            state['report'] = final_report
            
            return final_report
        except Exception as e:
            logger.error(f"Error in edit_report: {e}")
            return ""
    
    async def compile_content(self, state: ResearchState, briefings: Dict[str, str], company: str) -> str:
        """Initial compilation of research sections."""
        
        combined_content = "\n\n".join(
            f"## {header.title()}\n{content}"
            for header, content in briefings.items()
        )
        
        prompt = f"""You are compiling a comprehensive research report about {company}.

Original section content:
{combined_content}

Create a comprehensive report on {company} that:
1. Integrates information from all sections into a cohesive narrative
2. Maintains the most important details from each section
3. Organizes information logically within each section and removes any transitional commentary / explanations
4. Uses clear section headers and structure
5. Preserves all factual information 
6. Focuses on {company}

Return the compiled report in perfectly formatted markdown. Do not include any explanatory text."""

        try:
            response = self.gemini_model.generate_content(prompt, stream=True)
            
            accumulated_text = ""
            async for chunk in response:
                chunk_text = chunk.text
                print(chunk_text)
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
            
            return (accumulated_text or "").strip()
        except Exception as e:
            logger.error(f"Error in initial compilation: {e}")
            return (combined_content or "").strip()

    async def deduplicate_content(self, state: ResearchState, content: str, company: str) -> str:
        """Clean up and deduplicate the compiled report."""
        
        prompt = f"""You are an expert markdown editor. You are given a report on {company}.

Current report:
{content}

Create a refined version that follows these EXACT markdown formatting rules:
1. Main title should use a single # (e.g. "# Company Research Report")
2. All section headers should use ## without any horizontal rules (e.g. "## Company Overview")
3. All subsections should use ### (e.g. "### Core Products")
4. Use * consistently for all bullet points (never use • or -)
5. Add a blank line before and after each section and subsection header
6. Ensure consistent indentation for bullet points
7. Use bold (**text**) for emphasis, not italics
8. Keep one blank line between bullet points for readability
9. References should be properly formatted as markdown links

Additionally:
1. Remove any redundant information
2. Improve flow and readability
3. Remove sections lacking substantial content
4. Remove transitional commentary / explanations that an LLM might have added.
5. Ensure perfect markdown syntax

Return the polished report in flawless markdown format. Provide no explanations or commentary."""

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
            
            return (accumulated_text or "").strip()
        except Exception as e:
            logger.error(f"Error in deduplication: {e}")
            return (content or "").strip()

    async def run(self, state: ResearchState) -> ResearchState:
        return await self.compile_briefings(state)
