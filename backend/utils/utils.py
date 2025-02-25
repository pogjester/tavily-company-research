import markdown
import logging
import os
import re
import datetime
from typing import List, Dict
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
import tempfile


def extract_domain_name(url: str) -> str:
    """Extract domain name from URL."""
    match = re.search(r'https?://([^/]+)', url)
    if match:
        return match.group(1)
    return url

def extract_title_from_url_path(url: str) -> str:
    """Extract a title from a URL path."""
    parts = url.rstrip('/').split('/')
    return parts[-1] if parts else 'No title found'

def extract_link_info(markdown_link: str) -> tuple[str, str]:
    """Extract text and URL from a Markdown link [text](URL)."""
    match = re.match(r'\[(.*?)\]\((.*?)\)', markdown_link)
    if match:
        return match.group(1), match.group(2)
    return ("", "")

logger = logging.getLogger(__name__)

def clean_text(text: str) -> str:
    """Clean up text by replacing escaped quotes and other special characters."""
    # Remove any trailing JSON artifacts
    text = re.sub(r'",?\s*"pdf_url":.+$', '', text)
    # Replace escaped quotes with regular quotes
    text = text.replace('\\"', '"')
    # Convert literal \n to actual newlines
    text = text.replace('\\n', '\n')
    # Remove any XML/para tags
    text = text.replace('<para>', '').replace('</para>', '')
    return text.strip()

def generate_pdf_from_md(markdown_content: str, output_pdf: str) -> None:
    """Convert markdown content to PDF using a simplified ReportLab approach."""
    try:
        # Ensure output directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_pdf)), exist_ok=True)
        
        # Normalize line endings
        markdown_content = markdown_content.replace('\r\n', '\n')  # Normalize Windows line endings
        markdown_content = markdown_content.replace('\\n', '\n')   # Convert literal \n to newlines
        
        # Extract company name from the first line
        company_name = "Company Research Report"
        first_line = markdown_content.split('\n')[0].strip()
        if first_line.startswith('# '):
            company_name = first_line[2:].strip()
        
        # Current date for the footer
        current_date = datetime.datetime.now().strftime("%B %d, %Y")
        
        # Create the PDF document
        doc = SimpleDocTemplate(
            output_pdf,
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40
        )
        
        # Setup styles
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.black,
            spaceAfter=12
        )
        
        heading2_style = ParagraphStyle(
            'Heading2',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.black,
            spaceBefore=12,
            spaceAfter=6,
            fontName='Helvetica-Bold'
        )
        
        heading3_style = ParagraphStyle(
            'Heading3',
            parent=styles['Heading3'],
            fontSize=12,
            textColor=colors.black,
            spaceBefore=10,
            spaceAfter=4
        )
        
        normal_style = ParagraphStyle(
            'Normal',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            spaceBefore=2,
            spaceAfter=2
        )
        
        list_item_style = ParagraphStyle(
            'ListItem',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            spaceBefore=2,
            spaceAfter=2,
            leftIndent=10,
            firstLineIndent=0,
            bulletIndent=0
        )
        
        # Create the story (content)
        story = []
        
        # Process markdown content into PDF elements
        lines = markdown_content.split('\n')
        i = 0
        
        # Track if we're in a list
        in_list = False
        list_items = []
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines
            if not line:
                if in_list and list_items:
                    # Flush list if we were building one
                    story.append(ListFlowable(
                        [ListItem(Paragraph(item, list_item_style)) for item in list_items],
                        bulletType='bullet',
                        leftIndent=10,
                        bulletFontName='Helvetica',
                        bulletFontSize=10,
                        bulletOffsetY=0,
                        bulletDedent=10,
                        spaceAfter=0
                    ))
                    list_items = []
                    in_list = False
                
                story.append(Spacer(1, 6))
                i += 1
                continue
            
            # Headings
            if line.startswith('# '):
                story.append(Paragraph(line[2:], title_style))
            elif line.startswith('## '):
                story.append(Paragraph(line[3:], heading2_style))
            elif line.startswith('### '):
                story.append(Paragraph(line[4:], heading3_style))
            
            # Bullet points
            elif line.startswith('* '):
                bullet_text = line[2:].strip()  # Remove the '* ' but keep any other asterisks
                
                # For links in bullet points
                if bullet_text.startswith('[') and '](' in bullet_text and bullet_text.endswith(')'):
                    link_text, link_url = extract_link_info(bullet_text)
                    # Simplified link format to avoid potential formatting issues
                    bullet_text = f'<link href="{link_url}" color="blue"><u>{link_text or link_url}</u></link>'
                
                list_items.append(bullet_text)
                in_list = True
            
            # Regular paragraphs (including links)
            else:
                # Handle bold and italic text
                line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)  # Bold
                line = re.sub(r'\*(.*?)\*', r'<i>\1</i>', line)      # Italic
                
                # Check for links in the text
                if '[' in line and '](' in line:
                    try:
                        # Process links
                        parts = []
                        last_idx = 0
                        for match in re.finditer(r'\[(.*?)\]\((.*?)\)', line):
                            # Add text before the link
                            if match.start() > last_idx:
                                parts.append(line[last_idx:match.start()])
                            
                            # Add the link
                            link_text = match.group(1)
                            link_url = match.group(2)
                            parts.append(f'<link href="{link_url}" color="blue"><u>{link_text}</u></link>')
                            
                            last_idx = match.end()
                        
                        # Add any remaining text
                        if last_idx < len(line):
                            parts.append(line[last_idx:])
                        
                        line = ''.join(parts)
                    except Exception as e:
                        # If link processing fails, use the original line
                        logger.error(f"Error processing links: {e}")
                
                # Add the paragraph
                story.append(Paragraph(line, normal_style))
            
            i += 1
        
        # Flush any remaining list
        if in_list and list_items:
            story.append(ListFlowable(
                [ListItem(Paragraph(item, list_item_style)) for item in list_items],
                bulletType='bullet',
                leftIndent=10,
                bulletFontName='Helvetica',
                bulletFontSize=10,
                bulletOffsetY=0,
                bulletDedent=10,
                spaceAfter=0
            ))
        
        # Build the PDF
        doc.build(story)
        
        logger.info(f"Successfully generated PDF: {output_pdf}")
    
    except Exception as e:
        error_msg = f"Error generating PDF: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)

# Example usage (uncomment if you want to run directly):
# if __name__ == '__main__':
#     with open('example.md', 'r', encoding='utf-8') as f:
#         md_text = f.read()
#     generate_pdf_from_md(md_text, 'output.pdf')

def convert_markdown_to_pdf_elements(markdown_text: str, custom_styles: Dict) -> List:
    """
    Example function that converts a Markdown string into a list of
    ReportLab Flowable elements. This is separate from generate_pdf_from_md.
    """
    story = []
    current_list_items = []
    in_list = False
    in_references = False

    lines = markdown_text.split('\n')
    i = 0

    def process_markdown_formatting(text):
        # Bold
        text = re.sub(r'(?<!\*)\*\*(.*?)\*\*(?!\*)', r'<b>\1</b>', text)
        
        # Clean up any remaining double asterisks (bold markers) but preserve single asterisks for bullet points
        text = text.replace('**', '')
        return text

    while i < len(lines):
        line = lines[i].strip()

        # Blank line
        if not line:
            if in_list and current_list_items:
                story.append(ListFlowable(
                    [
                        ListItem(
                            Paragraph(item, custom_styles['ListItem']),
                            value='bullet',
                            leftIndent=20,
                            bulletColor=colors.HexColor('#2c3e50'),
                            bulletType='bullet',
                            bulletFontName='Helvetica',
                            bulletFontSize=10
                        ) for item in current_list_items
                    ],
                    bulletType='bullet',
                    leftIndent=20,
                    bulletOffsetX=10,
                    bulletOffsetY=2,
                    start=None,
                    bulletDedent=20,
                    bulletFormat='•',
                    spaceBefore=4,
                    spaceAfter=4
                ))
                current_list_items = []
                in_list = False
            story.append(Spacer(1, 6))
            i += 1
            continue

        # Headings
        if line.startswith('#'):
            if in_list and current_list_items:
                # Flush the list
                story.append(ListFlowable(
                    [
                        ListItem(
                            Paragraph(item, custom_styles['ListItem']),
                            value='bullet',
                            leftIndent=20,
                            bulletColor=colors.HexColor('#2c3e50'),
                            bulletType='bullet',
                            bulletFontName='Helvetica',
                            bulletFontSize=10
                        ) for item in current_list_items
                    ],
                    bulletType='bullet',
                    leftIndent=20,
                    bulletOffsetX=10,
                    bulletOffsetY=2,
                    start=None,
                    bulletDedent=20,
                    bulletFormat='•',
                    spaceBefore=4,
                    spaceAfter=4
                ))
                current_list_items = []
                in_list = False

            heading_level = len(line.split()[0])  # number of '#' characters
            heading_text = ' '.join(line.split()[1:])
            style_name = f'Heading{heading_level}'
            # Use an existing style or a custom style
            story.append(Paragraph(heading_text, custom_styles.get(style_name, custom_styles['BodyText'])))

            if heading_text.lower() == 'references':
                in_references = True
            else:
                in_references = False
            i += 1
            continue

        # Bullets
        if line.startswith('* '):
            bullet_text = line[2:].strip()  # Remove the '* ' but keep any other asterisks
            
            # For non-references bullet points
            if bullet_text.startswith('[') and '](' in bullet_text and bullet_text.endswith(')'):
                # It's a link bullet
                title, url = extract_link_info(bullet_text)
                bullet_text = f'<link href="{url}" color="blue" textColor="blue"><u>{title or url}</u></link>'
            else:
                # Only process non-link text
                bullet_text = process_markdown_formatting(bullet_text)

            # Add it immediately as a single bullet item with explicit bullet styling
            story.append(ListFlowable(
                [
                    ListItem(
                        Paragraph(bullet_text, custom_styles['ListItem']),
                        value='bullet',
                        leftIndent=20,
                        bulletColor=colors.HexColor('#2c3e50'),
                        bulletType='bullet',
                        bulletFontName='Helvetica',
                        bulletFontSize=10,
                        bulletFormat='•'
                    )
                ],
                bulletType='bullet',
                leftIndent=20,
                bulletOffsetX=10,
                bulletOffsetY=2,
                start=None,
                bulletDedent=20,
                bulletFormat='•',
                spaceBefore=4,
                spaceAfter=4
            ))

        # If we were in a list but found something else
        if in_list and current_list_items:
            story.append(ListFlowable(
                [
                    ListItem(
                        Paragraph(item, custom_styles['ListItem']),
                        value='bullet',
                        leftIndent=20,
                        bulletColor=colors.HexColor('#2c3e50'),
                        bulletType='bullet',
                        bulletFontName='Helvetica',
                        bulletFontSize=10
                    ) for item in current_list_items
                ],
                bulletType='bullet',
                leftIndent=20,
                bulletOffsetX=10,
                bulletOffsetY=2,
                start=None,
                bulletDedent=20,
                bulletFormat='•',
                spaceBefore=4,
                spaceAfter=4
            ))
            current_list_items = []
            in_list = False

        # Standalone link
        if line.startswith('[') and '](' in line and line.endswith(')'):
            link_title, link_url = extract_link_info(line)
            # Don't process the URL again since it's already a raw URL
            link_paragraph = f'<link href="{link_url}" color="blue" textColor="blue"><u>{link_title or link_url}</u></link>'
            story.append(Paragraph(link_paragraph, custom_styles['Link']))
            i += 1
            continue

        # Regular paragraph
        line = clean_text(line)
        line = process_markdown_formatting(line)
        story.append(Paragraph(line, custom_styles['BodyText']))
        i += 1

    # Flush any remaining bullet items at the end
    if in_list and current_list_items:
        story.append(ListFlowable(
            [
                ListItem(
                    Paragraph(item, custom_styles['ListItem']),
                    value='bullet',
                    leftIndent=20,
                    bulletColor=colors.HexColor('#2c3e50'),
                    bulletType='bullet',
                    bulletFontName='Helvetica',
                    bulletFontSize=10
                ) for item in current_list_items
            ],
            bulletType='bullet',
            leftIndent=20,
            bulletOffsetX=10,
            bulletOffsetY=2,
            start=None,
            bulletDedent=20,
            bulletFormat='•',
            spaceBefore=4,
            spaceAfter=4
        ))

    return story

def get_custom_styles():
    """
    Example helper to retrieve a base stylesheet and then augment with custom styles.
    """
    styles = getSampleStyleSheet()

    # Update ListItem style
    styles.add(ParagraphStyle(
        name='ListItem',
        parent=styles['BodyText'],
        leftIndent=30,
        firstLineIndent=0,
        spaceBefore=2,
        spaceAfter=2,
        bulletIndent=15,
        bulletFontName='Helvetica-Bold',
        bulletFontSize=12,
        textColor=colors.HexColor('#2c3e50'),
        leading=14
    ))
    
    # Update BodyText
    styles['BodyText'].textColor = colors.HexColor('#2c3e50')
    styles['BodyText'].fontSize = 10
    styles['BodyText'].leading = 14
    
    # Heading styles
    styles['Heading1'].textColor = colors.HexColor('#2c3e50')
    styles['Heading1'].fontSize = 24
    styles['Heading1'].leading = 28

    styles['Heading2'].textColor = colors.HexColor('#2c3e50')
    styles['Heading2'].fontSize = 18
    styles['Heading2'].leading = 22

    styles['Heading3'].textColor = colors.HexColor('#2c3e50')
    styles['Heading3'].fontSize = 14
    styles['Heading3'].leading = 18

    # Link style
    styles.add(ParagraphStyle(
        name='Link',
        parent=styles['BodyText'],
        textColor=colors.HexColor('#3498db'),
        fontSize=10,
        leading=14
    ))
    
    return styles
