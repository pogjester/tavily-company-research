import os
import logging
import re
from datetime import datetime
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from backend.utils.utils import generate_pdf_from_md

logger = logging.getLogger(__name__)

class PDFService:
    def __init__(self, reports_dir: str):
        self.reports_dir = reports_dir
        os.makedirs(self.reports_dir, exist_ok=True)

    def _sanitize_company_name(self, company_name: str) -> str:
        """Sanitize company name for use in filenames."""
        return ''.join(c for c in (company_name or 'Unknown_Company') 
                      if c.isalnum() or c.isspace()).strip().replace(' ', '_')

    def _generate_pdf_filename(self, company_name: str) -> str:
        """Generate a standardized PDF filename."""
        sanitized_name = self._sanitize_company_name(company_name)
        timestamp = datetime.now().strftime('%Y-%m-%d')
        return f"{sanitized_name}_Research_Report_{timestamp}.pdf"

    def _preprocess_text(self, text: str) -> str:
        """Preprocess text to ensure proper XML tag nesting."""
        # Remove any existing para tags first
        text = text.replace('<para>', '').replace('</para>', '')
        
        def process_links(text):
            """Process markdown links into properly formatted ReportLab links."""
            def replace_link(match):
                text = match.group(1)
                url = match.group(2)
                # Use ReportLab's link tag with proper formatting
                return f'<link href="{url}" color="blue" textColor="blue"><u>{text or url}</u></link>'
            
            # Handle markdown links [text](url)
            text = re.sub(r'\[(.*?)\]\((.*?)\)', replace_link, text)
            return text
        
        # Process bold and italic tags with proper nesting
        def process_tags(text):
            # First handle bold text
            text = re.sub(r'\*\*(.*?)\*\*', lambda m: f'<b>{m.group(1)}</b>', text)
            
            # Then handle italic text, being careful not to match inside tags
            parts = []
            current_pos = 0
            in_tag = False
            start_italic = None
            
            for i, char in enumerate(text):
                if char == '<':
                    in_tag = True
                elif char == '>':
                    in_tag = False
                elif not in_tag and char == '*' and text[i-1:i] != '\\':
                    if start_italic is None:
                        start_italic = i
                    else:
                        # Found closing asterisk
                        italic_content = text[start_italic+1:i]
                        parts.append(text[current_pos:start_italic])
                        parts.append(f'<i>{italic_content}</i>')
                        current_pos = i + 1
                        start_italic = None
            
            parts.append(text[current_pos:])
            text = ''.join(parts)
            
            # Clean up any remaining asterisks
            text = text.replace('\\*', '*')  # Restore escaped asterisks
            text = text.replace('**', '').replace('*', '')
            
            return text

        # Process the text in the correct order: links first, then other formatting
        text = process_links(text)
        text = process_tags(text)
        
        # Ensure text is wrapped in para tags
        if not text.startswith('<para>'):
            text = f'<para>{text}</para>'
            
        return text

    def generate_pdf(self, report_content: str, company_name: str = None) -> dict:
        """Generate a PDF from markdown content."""
        try:
            # Preprocess the content line by line
            processed_lines = []
            for line in report_content.split('\n'):
                if line.strip():
                    processed_lines.append(self._preprocess_text(line))
                else:
                    processed_lines.append('')
            
            processed_content = '\n'.join(processed_lines)
            
            pdf_filename = self._generate_pdf_filename(company_name)
            pdf_path = os.path.join(self.reports_dir, pdf_filename)

            try:
                generate_pdf_from_md(processed_content, pdf_path)
            except Exception as e:
                logger.error(f"PDF generation failed: {e}")
                # Clean up failed PDF if it exists
                if os.path.exists(pdf_path):
                    try:
                        os.remove(pdf_path)
                    except Exception:
                        pass
                raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")

            return {
                "status": "success",
                "pdf_url": f"/research/pdf/{pdf_filename}"
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    def generate_pdf_from_job(self, job_id: str, job_status: dict, mongodb=None) -> dict:
        """Generate a PDF from a job's report content."""
        try:
            # First try to get report from memory
            report_content = None
            if job_id in job_status:
                result = job_status[job_id]
                if isinstance(result, dict):
                    report_content = result.get('report')

            # If not in memory and MongoDB is available, try to get from MongoDB
            if not report_content and mongodb:
                try:
                    report = mongodb.get_report(job_id)
                    if report and isinstance(report, dict):
                        report_content = report.get('report')
                except Exception as e:
                    logger.warning(f"Failed to get report from MongoDB: {e}")

            if not report_content:
                raise HTTPException(status_code=404, detail="No report content available")

            # Get company name from memory or MongoDB
            company_name = None
            if job_id in job_status:
                company_name = job_status[job_id].get('company')
            if not company_name and mongodb:
                try:
                    job = mongodb.get_job(job_id)
                    if job and isinstance(job, dict):
                        company_name = job.get('company')
                except Exception as e:
                    logger.warning(f"Failed to get company name from MongoDB: {e}")

            return self.generate_pdf(report_content, company_name)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            raise HTTPException(status_code=500, detail=str(e)) 