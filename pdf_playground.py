import os
from backend.utils.utils import generate_pdf_from_md
import argparse
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
import time
import re

console = Console()

def format_markdown(content):
    """Format markdown with proper spacing and indentation."""
    lines = content.replace('\\n', '\n').split('\n')
    formatted = []
    
    for line in lines:
        line = line.strip()
        if not line:
            formatted.append('')
            continue
        
        # Add space before headers (except first)
        if line.startswith('#') and formatted and formatted[-1]:
            formatted.append('')
            
        # Handle bullet point indentation
        if formatted and formatted[-1].startswith(('*', '-')) and not line.startswith(('*', '-', '#')):
            line = '  ' + line
            
        formatted.append(line)
    
    # Clean up multiple empty lines
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(formatted))

def process_markdown(input_file, output_dir):
    """Generate PDF from markdown file."""
    try:
        # Read and format content
        with open(input_file, 'r', encoding='utf-8') as f:
            formatted_content = format_markdown(f.read())
        
        # Save formatted markdown and generate PDF
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        formatted_md = os.path.join(output_dir, 'formatted.md')
        pdf_file = os.path.join(output_dir, f"{base_name}_{int(time.time())}.pdf")
        
        # Save files and show preview
        with open(formatted_md, 'w', encoding='utf-8') as f:
            f.write(formatted_content)
            
        console.print("\n[bold blue]Preview:[/bold blue]")
        console.print(Panel(Markdown(formatted_content[:500] + "..." if len(formatted_content) > 500 else formatted_content)))
        
        result = generate_pdf_from_md(formatted_content, pdf_file)
        console.print(f"\n[bold green]Success![/bold green] Files saved:\n- {pdf_file}\n- {formatted_md}")
        
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Generate PDFs from markdown files.')
    parser.add_argument('input', help='Input markdown file')
    parser.add_argument('-o', '--output-dir', default='pdf_output', help='Output directory for PDFs')
    
    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    process_markdown(args.input, args.output_dir)

if __name__ == "__main__":
    main() 