import re

def standardize_markdown(text: str) -> str:
    """
    Simple markdown standardization that's forgiving and handles Gemini output gracefully.
    Focuses on basic readability while preserving the original formatting intent.
    """
    if not text:
        return ""

    # Normalize Unicode bullet points and tabs first
    text = text.replace('\u2022\t', '* ')  # Convert "•\t" to "* "
    text = text.replace('\u2022', '*')     # Convert remaining "•" to "*"
    text = text.replace('\t', ' ')         # Convert tabs to spaces

    # Split the text into lines
    lines = text.split('\n')
    processed_lines = []
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines
        if not line:
            processed_lines.append('')
            continue
            
        # Handle headers (both # and ##)
        if line.startswith('#'):
            # Remove all # symbols and extra spaces
            header = line.lstrip('#').strip()
            if not processed_lines or processed_lines[-1] != '':
                processed_lines.append('')
            processed_lines.append('## ' + header)
            processed_lines.append('')
            continue
            
        # Handle main section headers (lines followed by empty lines)
        if (len(processed_lines) >= 2 and 
            processed_lines[-1] == '' and 
            processed_lines[-2] == '' and
            not line.startswith('*') and
            not line.startswith('-')):
            processed_lines.append('## ' + line)
            processed_lines.append('')
            continue
            
        # Handle subsection headers (lines starting with * and ending with **)
        if line.startswith('* ') and line.endswith('**'):
            # Remove the asterisks and add proper header formatting
            header = line.strip('* ').rstrip('*')  # Remove both leading and trailing asterisks
            processed_lines.append('### ' + header)
            processed_lines.append('')
            continue
            
        # Handle bullet points (- * and other variants)
        if line.startswith('-') or line.startswith('*'):
            # Check if it's a subsection header first (contains ** anywhere in the line)
            if '**' in line:
                # Remove asterisks and add proper header formatting
                header = line.replace('*', '').strip()  # Remove all asterisks
                if header.endswith('*'):  # Extra safety check
                    header = header.rstrip('*')
                processed_lines.append('### ' + header)
                processed_lines.append('')
            else:
                # Convert any bullet point to a simple *
                bullet_content = line.lstrip('-* ').strip()
                processed_lines.append('* ' + bullet_content)
            continue
            
        # Regular line
        processed_lines.append(line)
    
    # Join lines and clean up multiple newlines
    text = '\n'.join(processed_lines)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip() 