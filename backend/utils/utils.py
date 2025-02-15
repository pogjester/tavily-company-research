import re
from fpdf import FPDF
import logging

logger = logging.getLogger(__name__)

class CustomPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_left_margin(25)
        self.set_right_margin(25)
        self.set_auto_page_break(auto=True, margin=25)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "C")

def remove_emojis(content):
    """Remove all emojis and special characters."""
    # This regex pattern matches all emojis and special unicode characters
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"  # dingbats
        "\U000024C2-\U0001F251" 
        "]+", flags=re.UNICODE)
    
    return emoji_pattern.sub('', content)

def sanitize_content(content):
    """Clean and prepare content for PDF generation."""
    # Remove all emojis
    content = remove_emojis(content)
    
    # Replace problematic characters
    content = replace_problematic_characters(content)
    
    # Remove any remaining non-ASCII characters
    content = ''.join(char if ord(char) < 128 else ' ' for char in content)
    
    # Log the sanitized content for debugging
    logger.info("Sanitized content:")
    logger.info("-" * 80)
    logger.info(content)
    logger.info("-" * 80)
    
    return content

def replace_problematic_characters(content):
    """Replace Unicode characters with ASCII equivalents."""
    replacements = {
        '\u2013': '-',    # en dash
        '\u2014': '--',   # em dash
        '\u2018': "'",    # left single quote
        '\u2019': "'",    # right single quote
        '\u201c': '"',    # left double quote
        '\u201d': '"',    # right double quote
        '\u2026': '...',  # ellipsis
        '\u2022': '*',    # bullet
        '\u2122': '(TM)', # trademark
        '\u00a0': ' ',    # non-breaking space
        '\u200b': '',     # zero-width space
        '\u2212': '-',    # minus sign
        '\u00b7': '*',    # middle dot
        '\u2023': '*',    # triangular bullet
        '\u25e6': '*',    # white bullet
        '\u2043': '-',    # hyphen bullet
        '\u2010': '-',    # hyphen
        '\u2011': '-',    # non-breaking hyphen
        '\u2012': '-',    # figure dash
        '\u2015': '--',   # horizontal bar
    }
    for char, replacement in replacements.items():
        content = content.replace(char, replacement)
    return content

def generate_pdf_from_md(content, filename='output.pdf'):
    try:
        logger.info(f"Starting PDF generation for file: {filename}")
        
        if not content or not content.strip():
            raise ValueError("No content provided for PDF generation")
        
        # Log original content
        logger.info("Original content:")
        logger.info("-" * 80)
        logger.info(content)
        logger.info("-" * 80)
            
        # Clean the content first
        content = sanitize_content(content)
        logger.info(f"Content sanitized, length: {len(content)}")
        
        pdf = CustomPDF()
        pdf.add_page()
        
        # Set initial font
        pdf.set_font('Arial', '', 12)
        
        # Split content into lines and process each line
        lines = content.split('\n')
        logger.info(f"Processing {len(lines)} lines")
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                pdf.ln(8)  # Add space for empty lines
                continue
                
            try:
                # Handle section headers
                if any(marker in line for marker in ['Overview', 'Analysis', 'Developments', 'References']):
                    pdf.set_font('Arial', 'B', 16)
                    pdf.ln(8)
                    pdf.cell(0, 10, line)
                    pdf.ln(8)
                    pdf.set_font('Arial', '', 12)
                    continue
                    
                # Handle separator lines
                if all(c == '=' for c in line):
                    pdf.ln(4)
                    continue
                    
                # Handle bullet points
                if line.startswith(('-', '*', '•')):
                    pdf.set_font('Arial', '', 12)
                    # Clean up bullet point format
                    line = '* ' + line.lstrip('*- •').strip()
                    # Add indentation for bullet points
                    pdf.set_x(35)
                    pdf.multi_cell(0, 8, line)
                    pdf.set_x(25)
                    continue
                
                # Regular text
                pdf.set_font('Arial', '', 12)
                pdf.multi_cell(0, 8, line)
                
            except Exception as e:
                logger.error(f"Error processing line {line_num}: {line}")
                logger.error(f"Error details: {str(e)}")
                raise
            
        logger.info("Saving PDF file...")
        pdf.output(filename)
        logger.info(f"PDF generated successfully: {filename}")
        
        # Verify the output
        if not pdf.page_no():
            raise ValueError("PDF was generated but contains no pages")
            
        return f"PDF generated: {filename}"
        
    except Exception as e:
        error_msg = f"Error generating PDF: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise Exception(error_msg)

def process_markdown_line(pdf, line):
    """Parses line for Markdown styling, including bold, italics, and links."""
    parts = re.split(r'(\*\*.*?\*\*|\*.*?\*|\[.*?\]\(.*?\)|https?://\S+)', line)
    for part in parts:
        if re.match(r'\*\*.*?\*\*', part):  # Bold
            text = part.strip('*')
            pdf.set_font('Arial', 'B', 12)
            pdf.write(10, text)
        elif re.match(r'\*.*?\*', part):  # Italics
            text = part.strip('*')
            pdf.set_font('Arial', 'I', 12)
            pdf.write(10, text)
        elif re.match(r'\[.*?\]\(.*?\)', part):  # Markdown link
            display_text = re.search(r'\[(.*?)\]', part).group(1)
            url = re.search(r'\((.*?)\)', part).group(1)
            pdf.set_text_color(0, 0, 255)
            pdf.set_font('Arial', 'U', 12)
            pdf.write(10, display_text, url)
            pdf.set_text_color(0, 0, 0)  # Reset color
            pdf.set_font('Arial', '', 12)
        elif re.match(r'https?://\S+', part):  # Plain URL
            url = part
            pdf.set_text_color(0, 0, 255)
            pdf.set_font('Arial', 'U', 12)
            pdf.write(10, url, url)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Arial', '', 12)
        else:
            pdf.set_font('Arial', '', 12)
            pdf.write(10, part)