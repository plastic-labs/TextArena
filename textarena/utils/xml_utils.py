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
    # Find all matches of the pattern
    pattern = f"<{tag}>(.*?)</{tag}>"
    matches = list(re.finditer(pattern, text, re.DOTALL))
    
    if matches:
        # Take the last match if there are multiple
        match = matches[-1]
        if include_tags:
            return match.group(0).strip()  # Return the entire match including tags
        return match.group(1).strip()  # Return just the content
    return None

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
        f"\n\nPlease provide your response in XML format using the <{tag}> tag. "
        f"For example: <{tag}>Your response here</{tag}>\n"
    )
    if instruction:
        xml_instruction += f"\n{instruction}\n"
    
    return base_prompt + xml_instruction