import re
from typing import Optional


def parse_xml_content(text: str, tag: str, include_tags: bool = False) -> Optional[str]:
    """
    Extract content between XML tags.
    
    Args:
        text: The text containing XML tags
        tag: The tag name to extract content from
        include_tags: Whether to include the XML tags in the returned string
        
    Returns:
        The content between the tags (with tags if include_tags=True), or None if no matching tags found
    """
    # Find all opening tags
    opening_pattern = f"<{tag}>"
    opening_matches = list(re.finditer(opening_pattern, text))
    
    if not opening_matches:
        return None
        
    # Find all closing tags
    closing_pattern = f"</{tag}>"
    closing_matches = list(re.finditer(closing_pattern, text))
    
    if not closing_matches:
        return None
        
    # Take the last opening tag
    last_opening = opening_matches[-1]
    
    # Take the last closing tag
    last_closing = closing_matches[-1]
    
    # Extract the content between last opening and last closing
    content = text[last_opening.end():last_closing.start()].strip()
    
    if include_tags:
        return f"<{tag}>{content}</{tag}>"
    return content

def format_xml_prompt(base_prompt: str, tag: str, instruction: str = "") -> str:
    """
    Format a prompt to request XML output.
    
    Args:
        base_prompt: The original prompt
        tag: The XML tag to use
        instruction: Additional instructions about the XML format
        
    Returns:
        The formatted prompt with XML instructions
    """
    xml_instruction = (
        f"\n\nIMPORTANT: Your response MUST include content wrapped in <{tag}> tags. "
        f"Any response without these tags will be considered invalid and may result in penalties.\n\n"
        f"Format your response like this:\n"
        f"<{tag}>Your actual response here</{tag}>\n\n"
        f"You may include additional text before or after the tags if you wish.\n"
        f"Only the content within the <{tag}> tags will be used as your actual response.\n"
        f"Make sure to include exactly one complete <{tag}>...</{tag}> pair in your response.\n"
    )
    if instruction:
        xml_instruction += f"\nAdditional instructions:\n{instruction}\n"
    return base_prompt + xml_instruction