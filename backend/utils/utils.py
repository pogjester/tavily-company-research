import markdown
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, KeepTogether
import logging
import os
import re
import datetime
from .references import extract_domain_name, extract_title_from_url_path, extract_link_info

logger = logging.getLogger(__name__)

def clean_text(text: str) -> str:
    """Clean up text by replacing escaped quotes and other special characters."""
    # Remove any trailing JSON artifacts
    text = re.sub(r'",?\s*"pdf_url":.+$', '', text)
    # Replace escaped quotes with regular quotes
    text = text.replace('\\"', '"')
    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def generate_pdf_from_md(markdown_content: str, output_pdf: str) -> None:
    """Convert markdown content to PDF using reportlab."""
    try:
        # Ensure output directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_pdf)), exist_ok=True)
        
        # Extract company name from the first line if it starts with # 
        company_name = "Company Research Report"
        first_line = markdown_content.split('\n')[0].strip()
        if first_line.startswith('# '):
            company_name = first_line[2:].strip()
        
        # Get current date for the footer
        current_date = datetime.datetime.now().strftime("%B %d, %Y")
        
        # Create a function to add page numbers and footer
        def add_page_number(canvas, doc):
            canvas.saveState()
            canvas.setFont('Helvetica', 8)
            # Footer with company name, date and page number
            footer_text = f"{company_name} | {current_date} | Page {doc.page}"
            canvas.drawCentredString(letter[0]/2, 20, footer_text)
            canvas.restoreState()
        
        # Create the PDF document
        doc = SimpleDocTemplate(
            output_pdf,
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40
        )

        # Create styles
        styles = getSampleStyleSheet()
        
        # Define custom styles with more compact spacing
        custom_styles = {
            'MainTitle': ParagraphStyle(
                'MainTitle',
                parent=styles['Heading1'],
                fontSize=20,
                spaceAfter=12,
                spaceBefore=4,
                textColor=colors.HexColor('#1a1a1a'),
                leading=24,
                keepWithNext=True  # Keep title with next content
            ),
            'CustomHeading2': ParagraphStyle(
                'CustomHeading2',
                parent=styles['Heading2'],
                fontSize=16,
                spaceBefore=12,
                spaceAfter=6,
                textColor=colors.HexColor('#2c3e50'),
                leading=20,
                keepWithNext=True  # Keep h2 with next content
            ),
            'CustomHeading3': ParagraphStyle(
                'CustomHeading3',
                parent=styles['Heading3'],
                fontSize=12,
                spaceBefore=10,
                spaceAfter=4,
                textColor=colors.HexColor('#2c3e50'), 
                leading=16,
                fontName='Helvetica-Bold',
                italic=0,  # Remove italics
                keepWithNext=True  # Keep h3 with next content
            ),
            'CustomBody': ParagraphStyle(
                'CustomBody',
                parent=styles['Normal'],
                fontSize=10,
                spaceBefore=2,
                spaceAfter=2,
                leading=12,
                textColor=colors.HexColor('#2c3e50')
            ),
            'ListItem': ParagraphStyle(
                'ListItem',
                parent=styles['Normal'],
                fontSize=10,
                spaceBefore=2,
                spaceAfter=2,
                leading=12,
                textColor=colors.HexColor('#2c3e50'),
                firstLineIndent=0,  # No indent for list items
                leftIndent=0  # No left indent as ListFlowable handles this
            ),
            'Link': ParagraphStyle(
                'Link',
                parent=styles['Normal'],
                fontSize=9,
                textColor=colors.HexColor('#3498db'),
                spaceBefore=1,
                spaceAfter=1,
                leading=11
            ),
            'Reference': ParagraphStyle(
                'Reference',
                parent=styles['Normal'],
                fontSize=9,
                spaceBefore=1,
                spaceAfter=1,
                leading=11,
                textColor=colors.HexColor('#333333'),
                leftIndent=15,
                firstLineIndent=-10  # Creates a hanging indent effect
            )
        }
        
        # Function to process markdown formatting
        def process_markdown_formatting(text):
            # Handle bold text (**text**)
            text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
            # Handle italic text (*text*)
            text = re.sub(r'(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)', r'<i>\1</i>', text)
            # Handle any remaining asterisks that might cause issues with ReportLab
            text = text.replace('**', '').replace('*', '')
            return text
        
        # Process the entire markdown content for bold and italic formatting
        markdown_content = process_markdown_formatting(markdown_content)
        
        # Split content into lines and clean each line
        lines = [clean_text(line) for line in markdown_content.split('\n')]
        story = []
        current_list_items = []
        in_list = False
        in_references = False  # Track if we're in the References section
        
        # Add a small spacer at the beginning for better layout
        story.append(Spacer(1, 2))
        
        for line in lines:
            line = line.strip()
            if not line:
                if in_list and current_list_items:
                    # Add the current list to the story
                    story.append(ListFlowable(
                        [ListItem(Paragraph(item, custom_styles['ListItem'])) for item in current_list_items],
                        bulletType='bullet',
                        leftIndent=15,
                        bulletOffsetX=-5,
                        bulletOffsetY=1,
                        bulletFontSize=8,
                        spaceBefore=4,
                        spaceAfter=4
                    ))
                    current_list_items = []
                    in_list = False
                story.append(Spacer(1, 2))
                continue
                
            # Handle headers
            if line.startswith('# '):
                text = clean_text(line[2:])
                # Keep title with next paragraph only
                story.append(KeepTogether([
                    Paragraph(text, custom_styles['MainTitle']),
                    Spacer(1, 2)
                ]))
                in_references = False
            elif line.startswith('## '):
                text = clean_text(line[3:])
                # Check if we're entering the References section
                if text.lower() == 'references':
                    in_references = True
                else:
                    in_references = False
                # Keep h2 with next paragraph only
                story.append(KeepTogether([
                    Paragraph(text, custom_styles['CustomHeading2']),
                    Spacer(1, 2)
                ]))
            elif line.startswith('### '):
                text = clean_text(line[4:])
                # Keep h3 with next paragraph only
                story.append(KeepTogether([
                    Paragraph(text, custom_styles['CustomHeading3']),
                    Spacer(1, 2)
                ]))
                in_references = False
            # Handle bullet points with links
            elif line.startswith('* '):
                text = line[2:].strip()
                
                # Special handling for references section
                if in_references:
                    # For references, use the Reference style with hanging indent
                    if '[' in text and '](' in text:
                        # Try to extract website, title, and URL
                        website = ""
                        title = ""
                        url = ""
                        
                        # Check for MLA-style format
                        mla_match = re.match(r'(.*?)\.\s*"(.*?)\."\s*\[(.*?)\]\((.*?)\)', text)
                        if mla_match:
                            website = clean_text(mla_match.group(1))
                            title = clean_text(mla_match.group(2))
                            url = clean_text(mla_match.group(4))
                            
                            # If website is empty or just a period, extract from URL
                            if not website or website == ".":
                                website = extract_domain_name(url)
                            
                            # If title is empty, try to extract from URL
                            if not title or title == ".":
                                title = extract_title_from_url_path(url)
                                if not title:
                                    title = f"Information from {website}"
                            
                            # Format reference with proper website name and title
                            ref_text = f'• {website}. "{title}." <link href="{url}">{url}</link>'
                        else:
                            # Standard link format
                            match = re.match(r'\[(.*?)\]\((.*?)\)', text)
                            if match:
                                url = clean_text(match.group(2))
                                website = extract_domain_name(url)
                                ref_text = f'• {website}. <link href="{url}">{url}</link>'
                            else:
                                ref_text = f'• {text}'
                        
                        story.append(Paragraph(ref_text, custom_styles['Reference']))
                    else:
                        # Plain text reference
                        story.append(Paragraph(f'• {text}', custom_styles['Reference']))
                else:
                    # Normal bullet point handling for non-reference sections
                    in_list = True
                    # Check if this bullet point contains a link
                    if text.startswith('[') and '](' in text and text.endswith(')'):
                        title, url = extract_link_info(text)
                        text = f'<link href="{url}">{title}</link>'
                    else:
                        text = clean_text(text)
                        # Process markdown formatting for bold and italic
                        text = process_markdown_formatting(text)
                    current_list_items.append(text)
            # Handle standalone links
            elif line.startswith('[') and '](' in line and line.endswith(')'):
                title, url = extract_link_info(line)
                text = f'<link href="{url}">{title}</link>'
                story.append(Paragraph(text, custom_styles['Link']))
            # Regular paragraph
            else:
                if in_list and current_list_items:
                    # Add the current list to the story
                    story.append(ListFlowable(
                        [ListItem(Paragraph(item, custom_styles['ListItem'])) for item in current_list_items],
                        bulletType='bullet',
                        leftIndent=15,
                        bulletOffsetX=-5,
                        bulletOffsetY=1,
                        bulletFontSize=8,
                        spaceBefore=4,
                        spaceAfter=4
                    ))
                    current_list_items = []
                    in_list = False
                
                # Process markdown formatting for bold and italic
                line = process_markdown_formatting(line)
                story.append(Paragraph(line, custom_styles['CustomBody']))
        
        # Add any remaining list items
        if current_list_items:
            story.append(ListFlowable(
                [ListItem(Paragraph(item, custom_styles['ListItem'])) for item in current_list_items],
                bulletType='bullet',
                leftIndent=15,
                bulletOffsetX=-5,
                bulletOffsetY=1,
                bulletFontSize=8,
                spaceBefore=4,
                spaceAfter=4
            ))

        # Build the PDF with page numbers
        doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
        logger.info(f"Successfully generated PDF: {output_pdf}")

    except Exception as e:
        error_msg = f"Error generating PDF: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)

# Example usage:
if __name__ == '__main__':
    with open('example.md', 'r', encoding='utf-8') as f:
        md_text = f.read()
    generate_pdf_from_md(md_text, 'output.pdf')
