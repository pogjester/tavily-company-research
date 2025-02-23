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

            edited_report = await self.content_sweep(state, initial_report, company)
            if not edited_report:
                logger.error("Content sweep failed")
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

            final_report = await self.clean_markdown(state, edited_report, company)
            
            # Ensure final_report is a string before proceeding
            final_report = final_report or ""
            
            # Add references and finalize
            if references := state.get('references', []):
                reference_lines = ["\n\n## References\n"]
                for ref in references:
                    reference_lines.append(f"* [{ref}]({ref})")
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
        
        # Don't automatically add ## headers, let the model handle the structure
        combined_content = "\n\n".join(
            f"{content}"
            for header, content in briefings.items()
        )
        
        prompt = f"""You are compiling a comprehensive research report about {company}.

Compiled briefings:
{combined_content}

Create a comprehensive and focused report on {company} that:
1. Integrates information from all sections into a cohesive non-repetitive narrative
2. Maintains important details from each section
3. Logically organizes information and removes transitional commentary / explanations
4. Uses clear section headers and structure

Formatting rules:
Strictly enforce this EXACT document structure:

# {company} Research Report

## Company Overview
[Company content with ### subsections]

## Industry Overview
[Industry content with ### subsections]

## Financial Overview
[Financial content with ### subsections]

## News
[News content with ### subsections]

## References
[Reference links if present]

Return the report in clean markdown format. No explanations or commentary."""

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
        
    async def content_sweep(self, state: ResearchState, content: str, company: str) -> str:
        """Sweep the content for any redundant information."""
        prompt = f"""You are an expert briefing editor. You are given a report on {company}.

Current report:
{content}


1. Remove redundant or repetitive information
2. Remove sections lacking substantial content
3. Remove any meta-commentary (e.g. "Here is the news...")
4. Use bullet points (*) for lists
5. Keep all factual content

Return the cleaned report in flawless markdown format. No explanations or commentary."""
        
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
                            message="Editing final report",
                            result={
                                "chunk": chunk_text,
                                "step": "Editor"
                            }
                        )
            
            return (accumulated_text or "").strip()
        except Exception as e:
            logger.error(f"Error in editing: {e}")
            return (content or "").strip()

    async def clean_markdown(self, state: ResearchState, content: str, company: str) -> str:
        """Clean up and format in markdown."""
        
        prompt = f"""You are an expert markdown editor. You are given a report on {company}.

Current report:
{content}

Instructions:
Strictly enforce this EXACT document structure:

# {company} Research Report

## Company Overview
[Company content with ### subsections]

## Industry Overview
[Industry content with ### subsections]

## Financial Overview
[Financial content with ### subsections]

## News
[News content with ### subsections]

## References
[Reference links if present]

Critical rules:
1. The document MUST start with "# {company} Research Report"
2. The document MUST ONLY use these exact ## headers in this order:
   - ## Company Overview
   - ## Industry Overview
   - ## Financial Overview
   - ## News
   - ## References (if present)
3. NO OTHER ## HEADERS ARE ALLOWED
4. Use ### for subsections in Company/Industry/Financial sections
5. News section should only use bullet points (*), never headers
6. Never use code blocks (```)
7. Never use more than one blank line between sections
8. Format all bullet points with *
9. Add one blank line before and after each section/list

Return the polished report in flawless markdown format. No explanation."""

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
                            message="Formatting final report",
                            result={
                                "chunk": chunk_text,
                                "step": "Editor"
                            }
                        )
            
            return (accumulated_text or "").strip()
        except Exception as e:
            logger.error(f"Error in formatting: {e}")
            return (content or "").strip()

    async def run(self, state: ResearchState) -> ResearchState:
        return await self.compile_briefings(state)
