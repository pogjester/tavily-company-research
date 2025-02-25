import markdown
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    ListFlowable,
    ListItem,
    KeepTogether
)
import logging
import os
import re
import datetime
from typing import List, Dict

#############################################
# references.py placeholders. Adjust as needed
#############################################
def extract_domain_name(url: str) -> str:
    """Placeholder for domain extraction."""
    # Basic example using regex:
    match = re.search(r'https?://([^/]+)', url)
    if match:
        return match.group(1)
    return url

def extract_title_from_url_path(url: str) -> str:
    """Placeholder for extracting a title from a URL path."""
    # Very naive approach: use last path segment
    parts = url.rstrip('/').split('/')
    return parts[-1] if parts else 'No title found'

def extract_link_info(markdown_link: str) -> tuple[str, str]:
    """
    Extract the text and URL from a Markdown link of the form:
      [text](URL)
    """
    match = re.match(r'\[(.*?)\]\((.*?)\)', markdown_link)
    if match:
        return match.group(1), match.group(2)
    return ("", "")

#############################################
# Main code below
#############################################

logger = logging.getLogger(__name__)

def clean_text(text: str) -> str:
    """Clean up text by replacing escaped quotes and other special characters."""
    # Remove any trailing JSON artifacts
    text = re.sub(r'",?\s*"pdf_url":.+$', '', text)
    # Replace escaped quotes with regular quotes
    text = text.replace('\\"', '"')
    # Replace multiple spaces with a single space, but preserve spaces after asterisks
    text = re.sub(r'(?<!\*)\s+', ' ', text)
    # Remove any XML/para tags as they'll be added during processing
    text = text.replace('<para>', '').replace('</para>', '')
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
        
        # Current date for the footer
        current_date = datetime.datetime.now().strftime("%B %d, %Y")
        
        def add_page_number(canvas, doc):
            """Add page numbers and a footer on every page."""
            canvas.saveState()
            canvas.setFont('Helvetica', 8)
            footer_text = f"{company_name} | {current_date} | Page {doc.page}"
            # Draw the footer text at the bottom, centered
            canvas.drawCentredString(letter[0] / 2, 20, footer_text)
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

        # Create base styles
        base_styles = getSampleStyleSheet()

        # Create custom styles
        custom_styles = {
            'MainTitle': ParagraphStyle(
                'MainTitle',
                parent=base_styles['Heading1'],
                fontSize=20,
                spaceAfter=12,
                spaceBefore=4,
                textColor=colors.HexColor('#1a1a1a'),
                leading=24,
                keepWithNext=True  # Keep title with next content
            ),
            'CustomHeading2': ParagraphStyle(
                'CustomHeading2',
                parent=base_styles['Heading2'],
                fontSize=16,
                spaceBefore=12,
                spaceAfter=6,
                textColor=colors.HexColor('#2c3e50'),
                leading=20,
                keepWithNext=True
            ),
            'CustomHeading3': ParagraphStyle(
                'CustomHeading3',
                parent=base_styles['Heading3'],
                fontSize=12,
                spaceBefore=10,
                spaceAfter=4,
                textColor=colors.HexColor('#2c3e50'),
                leading=16,
                fontName='Helvetica-Bold',
                italic=0,
                keepWithNext=True
            ),
            'CustomBody': ParagraphStyle(
                'CustomBody',
                parent=base_styles['Normal'],
                fontSize=10,
                spaceBefore=2,
                spaceAfter=2,
                leading=12,
                textColor=colors.HexColor('#2c3e50')
            ),
            'ListItem': ParagraphStyle(
                'ListItem',
                parent=base_styles['Normal'],
                fontSize=10,
                spaceBefore=2,
                spaceAfter=2,
                leading=12,
                textColor=colors.HexColor('#2c3e50'),
                firstLineIndent=0,
                leftIndent=20
            ),
            'Link': ParagraphStyle(
                'Link',
                parent=base_styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#0066cc'),
                spaceBefore=2,
                spaceAfter=2,
                leading=12,
                underline=True
            ),
            'Reference': ParagraphStyle(
                'Reference',
                parent=base_styles['Normal'],
                fontSize=9,
                spaceBefore=1,
                spaceAfter=1,
                leading=11,
                textColor=colors.HexColor('#333333'),
                leftIndent=15,
                firstLineIndent=-10  # Creates a hanging indent effect
            )
        }
        
        def process_markdown_formatting(text):
            """Convert **bold** and *italic* markers to ReportLab tags and auto-hyperlink URLs."""
            # First handle URLs before any other processing, but only if they're not already in a link tag
            if '<link' not in text:
                text = re.sub(
                    r'(https?://[^\s<>"]+)',
                    lambda m: f'<link href="{m.group(1)}" color="blue" textColor="blue"><u>{m.group(1)}</u></link>',
                    text
                )
            
            # Process bold text (but not bullet points)
            text = re.sub(r'(?<!\*)\*\*(.*?)\*\*(?!\*)', lambda m: f'<b>{m.group(1)}</b>', text)
            
            # Process italic text (but not bullet points)
            text = re.sub(r'(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)', lambda m: f'<i>{m.group(1)}</i>', text)
            
            # Clean up any remaining double asterisks (bold markers)
            text = text.replace('**', '')
            
            # Do NOT remove single asterisks as they might be bullet points
            
            # Ensure proper XML structure
            if not text.startswith('<para>'):
                text = f'<para>{text}</para>'
            
            return text
        
        # Process entire markdown for bold/italic, then split into lines
        markdown_content = process_markdown_formatting(markdown_content)
        lines = [clean_text(line) for line in markdown_content.split('\n')]

        story = []
        in_list = False
        current_list_items = []
        in_references = False
        reference_section = []

        # Add a small spacer at the beginning
        story.append(Spacer(1, 2))
        
        for line in lines:
            line = line.strip()
            
            # Handle blank lines
            if not line:
                # If we were building a multi-item list, flush it
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
                            )
                            for item in current_list_items
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

                story.append(Spacer(1, 2))
                continue
            
            # Handle # , ##, ### headings
            if line.startswith('# '):
                text = clean_text(line[2:])
                story.append(KeepTogether([
                    Paragraph(text, custom_styles['MainTitle']),
                    Spacer(1, 2)
                ]))
                in_references = False

            elif line.startswith('## '):
                text = clean_text(line[3:])
                if text.lower() == 'references':
                    in_references = True
                    reference_section.append(Paragraph(text, custom_styles['CustomHeading2']))
                    reference_section.append(Spacer(1, 2))
                else:
                    in_references = False
                    story.append(KeepTogether([
                        Paragraph(text, custom_styles['CustomHeading2']),
                        Spacer(1, 2)
                    ]))

            elif line.startswith('### '):
                text = clean_text(line[4:])
                in_references = False
                story.append(KeepTogether([
                    Paragraph(text, custom_styles['CustomHeading3']),
                    Spacer(1, 2)
                ]))

            # Handle bullet points
            elif line.startswith('* '):
                bullet_text = line[2:].strip()  # Remove the '* ' but keep any other asterisks

                # If we have been building a bullet list, we'll continue
                # but in the original code, we tried to add them immediately.
                # We'll do immediate addition in this approach:
                
                if in_references:
                    # For references, we can look for MLA-style or standard link
                    # Attempt MLA pattern: (site)."Title." [text](URL)
                    mla_match = re.match(r'(.*?)\.\s*"(.*?)\."\s*\[(.*?)\]\((.*?)\)', bullet_text)
                    if mla_match:
                        website = clean_text(mla_match.group(1))
                        title = clean_text(mla_match.group(2))
                        url = clean_text(mla_match.group(4))
                        
                        # If website is empty, try from URL
                        if not website or website == ".":
                            website = extract_domain_name(url)
                        if not title or title == ".":
                            title = extract_title_from_url_path(url) or f"Information from {website}"
                        
                        # Don't process the URL again since it's already a raw URL
                        ref_text = f'{website}. "{title}." <link href="{url}" color="blue" textColor="blue"><u>{url}</u></link>'
                        reference_section.append(ListFlowable(
                            [
                                ListItem(
                                    Paragraph(ref_text, custom_styles['Reference']),
                                    value='bullet',
                                    leftIndent=20,
                                    bulletColor=colors.HexColor('#2c3e50'),
                                    bulletType='bullet',
                                    bulletFontName='Helvetica',
                                    bulletFontSize=10
                                )
                            ],
                            bulletType='bullet',
                            leftIndent=20,
                            bulletOffsetX=10,
                            bulletOffsetY=2,
                            bulletFontSize=12,
                            bulletColor=colors.HexColor('#2c3e50'),
                            bulletDedent=20,
                            bulletFormat='•',
                            spaceBefore=4,
                            spaceAfter=4
                        ))
                        # Add spacing between references
                        reference_section.append(Spacer(1, 8))
                    else:
                        # Possibly standard link format [title](url)
                        link_match = re.match(r'\[(.*?)\]\((.*?)\)', bullet_text)
                        if link_match:
                            url = clean_text(link_match.group(2))
                            website = extract_domain_name(url)
                            # Don't process the URL again since it's already a raw URL
                            ref_text = f'{website}. <link href="{url}" color="blue" textColor="blue"><u>{url}</u></link>'
                            reference_section.append(ListFlowable(
                                [
                                    ListItem(
                                        Paragraph(ref_text, custom_styles['Reference']),
                                        value='bullet',
                                        leftIndent=20,
                                        bulletColor=colors.HexColor('#2c3e50'),
                                        bulletType='bullet',
                                        bulletFontName='Helvetica',
                                        bulletFontSize=10
                                    )
                                ],
                                bulletType='bullet',
                                leftIndent=20,
                                bulletOffsetX=10,
                                bulletOffsetY=2,
                                bulletFontSize=12,
                                bulletColor=colors.HexColor('#2c3e50'),
                                bulletDedent=20,
                                bulletFormat='•',
                                spaceBefore=4,
                                spaceAfter=4
                            ))
                            # Add spacing between references
                            reference_section.append(Spacer(1, 8))
                        else:
                            # Just treat it as a normal reference line
                            bullet_text = process_markdown_formatting(bullet_text)
                            reference_section.append(ListFlowable(
                                [
                                    ListItem(
                                        Paragraph(bullet_text, custom_styles['Reference']),
                                        value='bullet',
                                        leftIndent=20,
                                        bulletColor=colors.HexColor('#2c3e50'),
                                        bulletType='bullet',
                                        bulletFontName='Helvetica',
                                        bulletFontSize=10
                                    )
                                ],
                                bulletType='bullet',
                                leftIndent=20,
                                bulletOffsetX=10,
                                bulletOffsetY=2,
                                bulletFontSize=12,
                                bulletColor=colors.HexColor('#2c3e50'),
                                bulletDedent=20,
                                bulletFormat='•',
                                spaceBefore=4,
                                spaceAfter=4
                            ))
                            # Add spacing between references
                            reference_section.append(Spacer(1, 8))
                else:
                    # For non-references bullet points
                    if bullet_text.startswith('[') and '](' in bullet_text and bullet_text.endswith(')'):
                        # It's a link bullet
                        title, url = extract_link_info(bullet_text)
                        # Don't process the URL again since it's already a raw URL
                        bullet_text = f'<link href="{url}" color="blue" textColor="blue"><u>{title or url}</u></link>'
                    else:
                        # Only process non-link text
                        bullet_text = process_markdown_formatting(bullet_text)

                    # We'll add it immediately as a single bullet item
                    story.append(ListFlowable(
                        [
                            ListItem(
                                Paragraph(bullet_text, custom_styles['ListItem']),
                                value='bullet',
                                leftIndent=20,
                                bulletColor=colors.HexColor('#2c3e50'),
                                bulletType='bullet',
                                bulletFontName='Helvetica',
                                bulletFontSize=10
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

            # Handle standalone Markdown links
            elif line.startswith('[') and '](' in line and line.endswith(')'):
                link_title, link_url = extract_link_info(line)
                # Don't process the URL again since it's already a raw URL
                link_paragraph = f'<link href="{link_url}" color="blue" textColor="blue"><u>{link_title or link_url}</u></link>'
                story.append(Paragraph(link_paragraph, custom_styles['Link']))
            
            # Regular paragraph
            else:
                # If we were in a multi-item list, flush any leftover bullets
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
                            )
                            for item in current_list_items
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

                if in_references:
                    # We are in references but it's not a bullet -> just a paragraph reference
                    line = process_markdown_formatting(line)
                    reference_section.append(Paragraph(line, custom_styles['CustomBody']))
                else:
                    # Normal text paragraph
                    line = process_markdown_formatting(line)
                    story.append(Paragraph(line, custom_styles['CustomBody']))
        
        # If there's a half-finished list at the end, flush it
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
                    )
                    for item in current_list_items
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

        # If we have references, add them at the end
        if reference_section:
            story.append(KeepTogether(reference_section))

        # Build the PDF
        doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
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
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        # Italic
        text = re.sub(
            r'(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)',
            r'<i>\1</i>',
            text
        )
        text = text.replace('**', '').replace('*', '')
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
        if line.startswith('* ') or line.startswith('- '):
            in_list = True
            bullet_text = line[2:].strip()
            bullet_text = clean_text(bullet_text)
            bullet_text = process_markdown_formatting(bullet_text)

            # If there's a link
            if bullet_text.startswith('[') and '](' in bullet_text and bullet_text.endswith(')'):
                link_title, link_url = extract_link_info(bullet_text)
                # Don't process the URL again since it's already a raw URL
                bullet_text = f'<link href="{url}" color="blue" textColor="blue"><u>{title or url}</u></link>'
            else:
                # Only process non-link text
                bullet_text = process_markdown_formatting(bullet_text)

            current_list_items.append(bullet_text)
            i += 1
            continue

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
