"""
URL processing utilities for ingestion.

Handles loading URLs from files and validating them.
Supports per-line match type specification via comments.
"""
import re
from typing import List, Optional, Tuple
from ..scrapers.base import match_id_from_url


def load_urls_from_file(filepath: str) -> List[Tuple[str, Optional[str]]]:
    """
    Load URLs from a text file (one per line).
    
    Supports match type specification per line:
    - URL only: auto-detect match type
    - URL # VCT: specify match type (VCT, VCL, OFFSEASON)
    - URL #VCT: also works without space
    
    Args:
        filepath: Path to the text file
    
    Returns:
        List of tuples: (url, match_type) where match_type is None or one of VCT/VCL/OFFSEASON
    """
    urls = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comment-only lines
                if not line or line.startswith('#'):
                    continue
                
                # Check for match type in comment
                match_type = None
                if '#' in line:
                    parts = line.split('#', 1)
                    url = parts[0].strip()
                    comment = parts[1].strip().upper() if len(parts) > 1 else ''
                    
                    # Check if comment specifies match type
                    if comment in ['VCT', 'VCL', 'OFFSEASON']:
                        match_type = comment
                    elif comment == 'SHOWMATCH':
                        # Skip showmatches - don't set match_type, will be filtered later
                        print(f"Warning: SHOWMATCH specified for {url} - will be skipped")
                        continue
                else:
                    url = line
                
                if url:
                    urls.append((url, match_type))
    except FileNotFoundError:
        raise FileNotFoundError(f"URL file not found: {filepath}")
    except Exception as e:
        raise Exception(f"Error reading URL file {filepath}: {e}")
    
    return urls


def validate_url(url: str) -> bool:
    """
    Check if a URL is a valid VLR.gg match URL.
    
    Args:
        url: URL to validate
    
    Returns:
        True if URL appears to be a valid VLR.gg match URL
    """
    if not url:
        return False
    
    # Check if it's a VLR.gg URL
    if 'vlr.gg' not in url.lower():
        return False
    
    # Check if it has a match ID pattern
    match_id = match_id_from_url(url)
    if not match_id:
        return False
    
    # Basic validation: match ID should be reasonable
    if match_id < 1000 or match_id > 9999999:
        return False
    
    return True


def extract_match_id(url: str) -> Optional[int]:
    """
    Extract match ID from a URL.
    
    Args:
        url: VLR.gg match URL
    
    Returns:
        Match ID if found, None otherwise
    """
    return match_id_from_url(url)
