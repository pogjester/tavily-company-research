import logging
import re
from urllib.parse import urlparse
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger(__name__)

def extract_domain_name(url: str) -> str:
    """Extract a readable website name from a URL."""
    try:
        # Remove protocol and www
        domain = url.lower()
        for prefix in ['https://', 'http://', 'www.']:
            if domain.startswith(prefix):
                domain = domain[len(prefix):]
        
        # Get the main domain part (before first slash or query)
        domain = domain.split('/')[0].split('?')[0]
        
        # Extract the main part (e.g., 'tavily' from 'tavily.com')
        parts = domain.split('.')
        if len(parts) >= 2:
            main_name = parts[0]
            # Capitalize the name
            return main_name.capitalize()
        return domain.capitalize()
    except Exception as e:
        logger.error(f"Error extracting domain name from {url}: {e}")
        return "Website"

def extract_title_from_url_path(url: str) -> str:
    """Extract a meaningful title from the URL path."""
    try:
        # Remove protocol, www, and domain
        path = url.lower()
        for prefix in ['https://', 'http://', 'www.']:
            if path.startswith(prefix):
                path = path[len(prefix):]
        
        # Remove domain
        if '/' in path:
            path = path.split('/', 1)[1]
        else:
            path = ""
            
        # Clean up the path to create a title
        if path:
            # Remove file extensions and query parameters
            path = path.split('?')[0].split('#')[0]
            if path.endswith('/'):
                path = path[:-1]
                
            # Replace hyphens and underscores with spaces
            path = path.replace('-', ' ').replace('_', ' ').replace('/', ' - ')
            
            # Capitalize words
            title = ' '.join(word.capitalize() for word in path.split())
            
            # If title is still too long, truncate it
            if len(title) > 100:
                title = title[:97] + "..."
                
            return title
        return ""
    except Exception as e:
        logger.error(f"Error extracting title from URL path: {e}")
        return ""

def clean_title(title: str) -> str:
    """Clean up a title by removing dates, trailing periods or quotes, and truncating if needed."""
    if not title:
        return ""
    
    original_title = title
    
    # Remove any trailing periods or quotes
    title = title.strip().rstrip('.').strip('"\'')
    
    # Remove date patterns like "2024 - 10 - 03 -" or "2024-10-03-" or similar variations
    title = re.sub(r'^\d{4}[-\s]*\d{1,2}[-\s]*\d{1,2}[-\s]*', '', title)
    
    # Remove any leading/trailing hyphens and whitespace after date removal
    title = title.strip('- ').strip()
    
    # If title became empty after cleaning, return empty string
    if not title:
        logger.warning(f"Title became empty after cleaning: '{original_title}'")
        return ""
    
    # Log if we made changes to the title
    if title != original_title:
        logger.info(f"Cleaned title from '{original_title}' to '{title}'")
    
    return title

def normalize_url(url: str) -> str:
    """Normalize a URL by removing query parameters and fragments."""
    try:
        if not url:
            return ""
            
        # Ensure URL has a scheme
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        parsed = urlparse(url)
        normalized_url = parsed._replace(query='', fragment='').geturl().rstrip('/')
        
        return normalized_url
    except Exception as e:
        logger.error(f"Error normalizing URL {url}: {e}")
        return url

def extract_website_name_from_domain(domain: str) -> str:
    """Extract a readable website name from a domain."""
    if domain.startswith('www.'):
        domain = domain[4:]  # Remove www. prefix
    
    # Extract the main part (e.g., 'tavily' from 'tavily.com')
    website_name = domain.split('.')[0].capitalize()
    
    # Handle special cases
    if website_name == "Com":
        # Try to get a better name from the second part
        parts = domain.split('.')
        if len(parts) > 1:
            website_name = parts[0].capitalize()
    
    return website_name

def process_references_from_search_results(state: Dict[str, Any]) -> Tuple[List[str], Dict[str, str], Dict[str, Dict[str, Any]]]:
    """Process references from search results and return top references, titles, and info."""
    all_top_references = []
    
    # Collect references with scores from all data types
    data_types = ['curated_company_data', 'curated_industry_data', 'curated_financial_data', 'curated_news_data']
    
    # Log the start of reference processing
    logger.info("Starting to process references from search results")
    
    for data_type in data_types:
        if curated_data := state.get(data_type, {}):
            for url, doc in curated_data.items():
                try:
                    # Ensure we have a valid score
                    if 'evaluation' in doc and 'overall_score' in doc['evaluation']:
                        score = float(doc['evaluation']['overall_score'])
                    else:
                        # Fallback to raw score if available
                        score = float(doc.get('score', 0))
                    
                    logger.info(f"Found reference in {data_type}: URL={url}, Score={score:.4f}")
                    all_top_references.append((url, score))
                except (KeyError, ValueError, TypeError) as e:
                    logger.warning(f"Error processing score for {url} in {data_type}: {e}")
                    continue
    
    logger.info(f"Collected a total of {len(all_top_references)} references before deduplication")
    
    # Sort references by score in descending order
    all_top_references.sort(key=lambda x: float(x[1]), reverse=True)
    
    # Log top 20 references before deduplication to verify sorting
    logger.info("Top 20 references by score before deduplication:")
    for i, (url, score) in enumerate(all_top_references[:20]):
        logger.info(f"{i+1}. Score: {score:.4f} - URL: {url}")
    
    # Use a set to store unique URLs, keeping only the highest scored version of each URL
    seen_urls = set()
    unique_references = []
    reference_titles = {}  # Store titles for references
    reference_info = {}  # Store additional information for MLA-style references
    
    for url, score in all_top_references:
        # Skip if URL is not valid
        if not url or not url.startswith(('http://', 'https://')):
            logger.info(f"Skipping invalid URL: {url}")
            continue

        # Normalize URL
        normalized_url = normalize_url(url)
        
        if normalized_url not in seen_urls:
            seen_urls.add(normalized_url)
            unique_references.append((normalized_url, score))
            
            # Extract domain name for website citation
            parsed = urlparse(url)
            domain = parsed.netloc
            
            # Find and store the title and other info for this URL
            title = None
            website_name = None
            
            # Look for the document info in all data types
            for data_type in data_types:
                if not title and (curated_data := state.get(data_type, {})):
                    for doc in curated_data.values():
                        if doc.get('url') == url:
                            title = doc.get('title', '')
                            if title:
                                # Clean up the title
                                title = clean_title(title)
                                if title and title.strip() and title != url:
                                    reference_titles[normalized_url] = title
                                    logger.info(f"Found title for URL {url}: '{title}'")
                                    break
            
            # If no title was found, log it
            if not title:
                logger.info(f"No valid title found for URL {url}")
            
            # Extract a better website name from the domain
            website_name = extract_website_name_from_domain(domain)
            
            # Store additional information for MLA citation
            reference_info[normalized_url] = {
                'title': title or '',
                'domain': domain,
                'website': website_name,
                'url': normalized_url,
                'score': score
            }
            logger.info(f"Stored reference info for {normalized_url} with score {score:.4f}")
    
    # Sort unique references by score again to ensure proper ordering
    unique_references.sort(key=lambda x: float(x[1]), reverse=True)
    
    # Log unique references by score to verify sorting
    logger.info(f"Found {len(unique_references)} unique references after deduplication")
    logger.info("Unique references by score (sorted):")
    for i, (url, score) in enumerate(unique_references):
        logger.info(f"{i+1}. Score: {score:.4f} - URL: {url}")
    
    # Take exactly 10 unique references (or all if less than 10)
    top_references = unique_references[:10]
    top_reference_urls = [url for url, _ in top_references]
    
    # Log final top 10 references
    logger.info(f"Final top {len(top_reference_urls)} references selected:")
    for i, url in enumerate(top_reference_urls):
        score = next((s for u, s in unique_references if u == url), 0)
        logger.info(f"{i+1}. Score: {score:.4f} - URL: {url}")
    
    return top_reference_urls, reference_titles, reference_info

def format_reference_for_markdown(reference_entry: Dict[str, Any]) -> str:
    """Format a reference entry for markdown output."""
    website = reference_entry.get('website', '')
    title = reference_entry.get('title', '')
    url = reference_entry.get('url', '')
    
    # Ensure we have a website name
    if not website or website.strip() == "":
        website = extract_domain_name(url)
    
    # Ensure we have a title
    if not title or title.strip() == "" or title == url:
        # Try to extract a meaningful title from the URL
        title = extract_title_from_url_path(url)
        
        # If still no title, use default format
        if not title:
            title = f"Information from {website}"
    
    # Format: * Website. "Title." URL
    return f"* {website}. \"{title}.\" {url}"

def extract_link_info(line: str) -> tuple[str, str]:
    """Extract title and URL from markdown link."""
    try:
        # First clean any JSON artifacts that might interfere with link parsing
        line = re.sub(r'",?\s*"pdf_url":.+$', '', line)
        
        # Check for MLA-style references with website and title before the link
        # Format: * Website. "Title." [URL](URL)
        mla_match = re.match(r'\*?\s*(.*?)\s*\.\s*"(.*?)\."\s*\[(.*?)\]\((.*?)\)', line)
        if mla_match:
            website = clean_title(mla_match.group(1))
            title = clean_title(mla_match.group(2))
            link_text = clean_title(mla_match.group(3))
            url = clean_title(mla_match.group(4))
            
            # If website is empty or just a period, extract from URL
            if not website or website == ".":
                website = extract_domain_name(url)
            
            # Format for PDF: "Website. Title. URL"
            return f"{website}. {title}. {link_text}", url
        
        # Fallback for standard markdown links
        match = re.match(r'\[(.*?)\]\((.*?)\)', line)
        if match:
            title = clean_title(match.group(1))
            url = clean_title(match.group(2))
            # If the title is a URL and matches the URL, just use the URL
            if title.startswith('http') and title == url:
                return url, url
            return title, url
        
        logger.debug(f"No link match found in line: {line}")
        return '', ''
    except Exception as e:
        logger.error(f"Error extracting link info from line: {line}, error: {str(e)}")
        return '', ''

def format_references_section(references: List[str], reference_info: Dict[str, Dict[str, Any]], reference_titles: Dict[str, str]) -> str:
    """Format the references section for the final report."""
    if not references:
        return ""
    
    logger.info(f"Formatting {len(references)} references for the report")
    
    # Create a list of reference entries with all the information needed
    reference_entries = []
    for ref in references:
        info = reference_info.get(ref, {})
        website = info.get('website', '')
        title = info.get('title', '')
        score = info.get('score', 0)
        
        # If title is not in reference_info, try to get it from reference_titles
        if not title or title.strip() == "":
            title = reference_titles.get(ref, '')
            logger.info(f"Using title from reference_titles for {ref}: '{title}'")
        
        domain = info.get('domain', '')
        
        # If we don't have a title, use the URL
        if not title or title.strip() == "" or title == ref:
            title = ref
            logger.info(f"No title found for {ref}, using URL as title")
        
        # If we don't have a website name, extract it from the URL
        if not website or website.strip() == "":
            website = extract_domain_name(ref)
            logger.info(f"No website name found for {ref}, extracted: {website}")
        
        # Create a reference entry with all information
        entry = {
            'website': website,
            'title': title,
            'url': ref,
            'domain': domain,
            'score': score
        }
        logger.info(f"Created reference entry: {entry}")
        reference_entries.append(entry)
    
    # Keep references in the same order they were provided (which should be by score)
    # This preserves the top 10 scoring order from process_references_from_search_results
    logger.info("Maintaining reference order based on scores")
    
    # Format references in MLA style
    reference_lines = ["\n## References"]
    for entry in reference_entries:
        reference_line = format_reference_for_markdown(entry)
        reference_lines.append(reference_line)
        logger.info(f"Added reference: {reference_line}")
    
    reference_text = "\n".join(reference_lines)
    logger.info(f"Completed references section with {len(reference_entries)} entries")
    
    return reference_text 