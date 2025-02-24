import markdown
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, KeepTogether
from reportlab.lib.units import inch
import logging
import os
import re

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

def extract_link_info(line: str) -> tuple[str, str]:
    """Extract title and URL from markdown link."""
    try:
        # First clean any JSON artifacts that might interfere with link parsing
        line = re.sub(r'",?\s*"pdf_url":.+$', '', line)
        match = re.match(r'\[(.*?)\]\((.*?)\)', line)
        if match:
            title = clean_text(match.group(1))
            url = clean_text(match.group(2))
            # If the title is a URL and matches the URL, just use the URL
            if title.startswith('http') and title == url:
                return url, url
            return title, url
        logger.debug(f"No link match found in line: {line}")
        return '', ''
    except Exception as e:
        logger.error(f"Error extracting link info from line: {line}, error: {str(e)}")
        return '', ''

def generate_pdf_from_md(markdown_content: str, output_pdf: str) -> None:
    """Convert markdown content to PDF using reportlab."""
    try:
        # Ensure output directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_pdf)), exist_ok=True)
        
        # Create the PDF document
        doc = SimpleDocTemplate(
            output_pdf,
            pagesize=letter,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50
        )

        # Create styles
        styles = getSampleStyleSheet()
        
        # Define custom styles with more compact spacing
        custom_styles = {
            'MainTitle': ParagraphStyle(
                'MainTitle',
                parent=styles['Heading1'],
                fontSize=24,
                spaceAfter=16,
                spaceBefore=5,
                textColor=colors.HexColor('#1a1a1a'),
                leading=28,
                keepWithNext=True  # Keep title with next content
            ),
            'CustomHeading2': ParagraphStyle(
                'CustomHeading2',
                parent=styles['Heading2'],
                fontSize=18,
                spaceBefore=16,
                spaceAfter=8,
                textColor=colors.HexColor('#2c3e50'),
                leading=22,
                keepWithNext=True  # Keep h2 with next content
            ),
            'CustomHeading3': ParagraphStyle(
                'CustomHeading3',
                parent=styles['Heading3'],
                fontSize=14,
                spaceBefore=16,
                spaceAfter=8,
                textColor=colors.HexColor('#2c3e50'), 
                leading=22,
                fontName='Helvetica-Bold',
                italic=0,  # Remove italics
                keepWithNext=True  # Keep h3 with next content
            ),
            'CustomBody': ParagraphStyle(
                'CustomBody',
                parent=styles['Normal'],
                fontSize=11,
                spaceBefore=4,
                spaceAfter=4,
                leading=14,
                textColor=colors.HexColor('#2c3e50')
            ),
            'ListItem': ParagraphStyle(
                'ListItem',
                parent=styles['Normal'],
                fontSize=11,
                spaceBefore=4,
                spaceAfter=4,
                leading=14,
                textColor=colors.HexColor('#2c3e50'),
                firstLineIndent=0,  # No indent for list items
                leftIndent=0  # No left indent as ListFlowable handles this
            ),
            'Link': ParagraphStyle(
                'Link',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#3498db'),
                spaceBefore=2,
                spaceAfter=2,
                leading=12
            )
        }
        
        # Split content into lines and clean each line
        lines = [clean_text(line) for line in markdown_content.split('\n')]
        story = []
        current_list_items = []
        in_list = False
        
        for line in lines:
            line = line.strip()
            if not line:
                if in_list and current_list_items:
                    # Add the current list to the story
                    story.append(ListFlowable(
                        [ListItem(Paragraph(item, custom_styles['ListItem'])) for item in current_list_items],
                        bulletType='bullet',
                        leftIndent=20,
                        bulletOffsetX=-6,
                        bulletOffsetY=2,
                        bulletFontSize=10,
                        spaceBefore=6,
                        spaceAfter=6
                    ))
                    current_list_items = []
                    in_list = False
                story.append(Spacer(1, 4))
                continue
                
            # Handle headers
            if line.startswith('# '):
                text = clean_text(line[2:])
                # Keep title with next paragraph only
                story.append(KeepTogether([
                    Paragraph(text, custom_styles['MainTitle']),
                    Spacer(1, 4)
                ]))
            elif line.startswith('## '):
                text = clean_text(line[3:])
                # Keep h2 with next paragraph only
                story.append(KeepTogether([
                    Paragraph(text, custom_styles['CustomHeading2']),
                    Spacer(1, 4)
                ]))
            elif line.startswith('### '):
                text = clean_text(line[4:])
                # Keep h3 with next paragraph only
                story.append(KeepTogether([
                    Paragraph(text, custom_styles['CustomHeading3']),
                    Spacer(1, 4)
                ]))
            # Handle bullet points with links
            elif line.startswith('* '):
                in_list = True
                text = line[2:].strip()
                # Check if this bullet point contains a link
                if text.startswith('[') and '](' in text and text.endswith(')'):
                    title, url = extract_link_info(text)
                    text = f'<link href="{url}">{title}</link>'
                else:
                    text = clean_text(text)
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
                        leftIndent=20,
                        bulletOffsetX=-6,
                        bulletOffsetY=2,
                        bulletFontSize=10,
                        spaceBefore=6,
                        spaceAfter=6
                    ))
                    current_list_items = []
                    in_list = False
                story.append(Paragraph(line, custom_styles['CustomBody']))
        
        # Add any remaining list items
        if current_list_items:
            story.append(ListFlowable(
                [ListItem(Paragraph(item, custom_styles['ListItem'])) for item in current_list_items],
                bulletType='bullet',
                leftIndent=20,
                bulletOffsetX=-6,
                bulletOffsetY=2,
                bulletFontSize=10,
                spaceBefore=6,
                spaceAfter=6
            ))

        # Build the PDF
        doc.build(story)
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
