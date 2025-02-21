import re

def standardize_markdown(text: str) -> str:
    """
    Standardizes markdown formatting for consistent rendering.
    Handles:
    1. Section headers (##)
    2. Subsection headers (**text**)
    3. Bullet points (• or *)
    4. Newlines and spacing
    """
    if not text:
        return ""

    # Split into sections (by ##)
    sections = re.split(r'(?m)^##\s*', text)
    
    # Process each section
    processed_sections = []
    
    for i, section in enumerate(sections):
        if not section.strip():
            continue
            
        # First section might not start with ##
        if i == 0 and not text.startswith('##'):
            processed_sections.append(section)
            continue
            
        # Process section content
        lines = section.split('\n')
        if not lines:
            continue
            
        # First line is the section header
        header = lines[0].strip()
        content = '\n'.join(lines[1:]).strip()
        
        # Process subsections
        subsections = re.split(r'\n\n\*\*(.*?)\*\*\n', content)
        processed_content = []
        
        for j, subsection in enumerate(subsections):
            if not subsection.strip():
                continue
                
            if j % 2 == 0:  # Regular content
                # Process any bullet points
                processed_lines = []
                current_list = []
                
                for line in subsection.split('\n'):
                    line = line.strip()
                    if not line:
                        if current_list:
                            processed_lines.append('\n'.join(current_list))
                            current_list = []
                        continue
                        
                    # Check if line is a bullet point
                    if line.startswith('•') or line.startswith('*'):
                        line = '* ' + line[1:].strip()
                        current_list.append(line)
                    else:
                        if current_list:
                            processed_lines.append('\n'.join(current_list))
                            current_list = []
                        processed_lines.append(line)
                
                if current_list:
                    processed_lines.append('\n'.join(current_list))
                
                processed_content.append('\n\n'.join(processed_lines))
            else:  # Subsection header
                processed_content.append(f"\n### {subsection}\n")
        
        # Combine section
        processed_section = f"## {header}\n\n{'\n'.join(processed_content)}"
        processed_sections.append(processed_section)
    
    # Combine all sections
    result = '\n\n'.join(processed_sections)
    
    # Final cleanup
    result = re.sub(r'\n{3,}', '\n\n', result)  # Remove extra newlines
    result = re.sub(r'(?m)^\s*[•]\s*', '* ', result)  # Standardize bullet points
    
    return result.strip() 