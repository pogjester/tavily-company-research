import os
from datetime import datetime
from langchain_core.messages import AIMessage
from ..utils.utils import generate_pdf_from_md
from ..classes import ResearchState
import logging

logger = logging.getLogger(__name__)

class OutputNode:
    def __init__(self, output_dir="reports"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    async def markdown_to_pdf(self, markdown_content: str, output_path: str):
        try:  
            # Generate the PDF from Markdown content
            generate_pdf_from_md(markdown_content, output_path)
        except Exception as e:
            raise Exception(f"Failed to generate PDF: {str(e)}")

    async def format_output(self, state: ResearchState):
        report = state.get("report")
        if not report:
            logger.error("No report content found in state")
            return state
            
        logger.info(f"Formatting output for report with {len(report)} characters")
        logger.info(f"Current state keys: {list(state.keys())}")
        output_format = state.get("output_format", "pdf")  # Default to PDF

        # Set up the directory and file paths
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        file_base = f"{self.output_dir}/{state['company']}_Weekly_Report_{timestamp}"
        
        try:
            if output_format == "pdf":
                pdf_file_path = f"{file_base}.pdf"
                await self.markdown_to_pdf(markdown_content=report, output_path=pdf_file_path)
                formatted_report = f"📥 PDF report saved at {pdf_file_path}"
            else:
                markdown_file_path = f"{file_base}.md"
                with open(markdown_file_path, "w") as md_file:
                    md_file.write(report)
                formatted_report = f"📥 Markdown report saved at {markdown_file_path}"

            # Update messages in existing state
            messages = state.get('messages', [])
            messages.append(AIMessage(content=formatted_report))
            state['messages'] = messages
            state['output'] = {
                'format': output_format,
                'path': pdf_file_path if output_format == "pdf" else markdown_file_path,
                'timestamp': timestamp,
                'report': report,
                'briefings': state.get('briefings', {}),
                'references': state.get('references', [])
            }
            
            logger.info(f"Final state keys after output: {list(state.keys())}")
            return state  # Return the complete state with all information preserved
            
        except Exception as e:
            logger.error(f"Error formatting output: {str(e)}")
            return state

    async def run(self, state: ResearchState):
        return await self.format_output(state)
    