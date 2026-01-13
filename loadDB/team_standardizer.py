"""
Team name standardization using LLM to identify duplicate team names.

This module uses an LLM to identify teams that are the same but have different
name variations, then generates standardized mappings.
"""
import json
import sqlite3
from typing import Dict, List, Tuple
from .config import DB_PATH, ALIASES_FILE, TEAM_ALIASES


def get_all_team_names() -> List[str]:
    """
    Get all unique team names from the database.
    
    Returns:
        List of unique team names
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT team_a FROM Matches WHERE team_a IS NOT NULL
        UNION
        SELECT DISTINCT team_b FROM Matches WHERE team_b IS NOT NULL
        ORDER BY team_a
    """)
    teams = [row[0] for row in cur.fetchall()]
    conn.close()
    return teams


def standardize_with_heuristics(team_names: List[str]) -> Dict[str, str]:
    """
    Use heuristics to identify duplicate team names (fallback when LLM unavailable).
    
    Handles common patterns:
    - Names with parentheses: "Team Name(Short)" -> prefers the shorter canonical form
    - Sponsor prefixes: "VISA KRÜ" -> "KRÜ Esports"
    - Full names with abbreviations in parentheses
    
    Args:
        team_names: List of all team names to standardize
    
    Returns:
        Dictionary mapping variant names to canonical names
    """
    import re
    mappings = {}
    
    for name in team_names:
        # Pattern: "Full Name(Short Name)" or "Full Name(Short)"
        paren_match = re.match(r'^(.+?)\((.+?)\)$', name)
        if paren_match:
            full_name = paren_match.group(1).strip()
            short_name = paren_match.group(2).strip()
            
            # Prefer the shorter canonical name (usually the one in parentheses)
            # Check if the short name exists as a standalone team name
            short_exists = any(short_name.lower() == t.lower() for t in team_names if t != name)
            full_exists = any(full_name.lower() == t.lower() for t in team_names if t != name)
            
            if short_exists:
                # Short name exists separately, use it
                mappings[name] = short_name
            elif full_exists:
                # Full name exists separately, use it
                mappings[name] = full_name
            else:
                # Neither exists separately, prefer shorter canonical form
                # Usually the one in parentheses is the canonical name
                if len(short_name) <= len(full_name) and "esports" not in short_name.lower():
                    mappings[name] = short_name
                else:
                    mappings[name] = full_name
        
        # Pattern: "SPONSOR TEAM" where team name appears elsewhere
        # e.g., "VISA KRÜ" -> "KRÜ Esports"
        if "visa" in name.lower() or "sponsor" in name.lower():
            # Try to find the team name without sponsor prefix
            for other_name in team_names:
                if other_name == name:
                    continue
                # Check if name contains the other team name
                name_lower = name.lower()
                other_lower = other_name.lower()
                if other_lower in name_lower and len(other_lower) > 5:
                    # Found a match, map to the canonical form
                    mappings[name] = other_name
                    break
    
    return mappings


def standardize_with_llm(team_names: List[str], api_key: str | None = None) -> Dict[str, str]:
    """
    Use LLM to identify duplicate team names and generate standardization mappings.
    
    Args:
        team_names: List of all team names to standardize
        api_key: Optional API key for LLM service (if None, uses environment variable)
    
    Returns:
        Dictionary mapping variant names to canonical names
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("openai package required. Install with: pip install openai")
    
    import os
    if api_key is None:
        api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API key required. Set OPENAI_API_KEY env var or pass --api-key")
    
    client = OpenAI(api_key=api_key)
    
    # Create prompt for LLM
    teams_json = json.dumps(team_names, indent=2, ensure_ascii=False)
    prompt = f"""You are a Valorant esports expert. Analyze the following list of team names and identify which ones refer to the same team but with different name variations.

Team names to analyze:
{teams_json}

For each group of names that refer to the same team, identify the most canonical/official name and create mappings from variants to the canonical name.

Consider:
- Teams with parentheses showing alternative names (e.g., "Team Name(Short Name)" should map to the canonical form)
- Abbreviations vs full names (e.g., "G2" -> "G2 Esports")
- Spelling variations or special characters
- Sponsor name changes (e.g., "Visa KRÜ" -> "KRÜ Esports")

Return ONLY a valid JSON object mapping variant names to canonical names. Format:
{{
  "variant_name_1": "Canonical Name",
  "variant_name_2": "Canonical Name",
  ...
}}

Only include mappings where a variant should be changed. If a name is already canonical, don't include it.
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that standardizes esports team names. Always return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        raise


def standardize_with_anthropic(team_names: List[str], api_key: str | None = None) -> Dict[str, str]:
    """
    Use Anthropic Claude to identify duplicate team names and generate standardization mappings.
    
    Args:
        team_names: List of all team names to standardize
        api_key: Optional API key for Anthropic (if None, uses environment variable)
    
    Returns:
        Dictionary mapping variant names to canonical names
    """
    try:
        from anthropic import Anthropic
    except ImportError:
        raise ImportError("anthropic package required. Install with: pip install anthropic")
    
    import os
    if api_key is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("Anthropic API key required. Set ANTHROPIC_API_KEY env var or pass --api-key")
    
    client = Anthropic(api_key=api_key)
    
    teams_json = json.dumps(team_names, indent=2, ensure_ascii=False)
    prompt = f"""You are a Valorant esports expert. Analyze the following list of team names and identify which ones refer to the same team but with different name variations.

Team names to analyze:
{teams_json}

For each group of names that refer to the same team, identify the most canonical/official name and create mappings from variants to the canonical name.

Consider:
- Teams with parentheses showing alternative names (e.g., "Team Name(Short Name)" should map to the canonical form)
- Abbreviations vs full names (e.g., "G2" -> "G2 Esports")
- Spelling variations or special characters
- Sponsor name changes (e.g., "Visa KRÜ" -> "KRÜ Esports")

Return ONLY a valid JSON object mapping variant names to canonical names. Format:
{{
  "variant_name_1": "Canonical Name",
  "variant_name_2": "Canonical Name",
  ...
}}

Only include mappings where a variant should be changed. If a name is already canonical, don't include it."""
    
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=4096,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    content = message.content[0].text
    # Extract JSON from response (in case there's extra text)
    import re
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    if json_match:
        result = json.loads(json_match.group())
    else:
        result = json.loads(content)
    
    return result


def merge_aliases(new_mappings: Dict[str, str], existing_aliases: Dict[str, str] | None = None) -> Dict[str, str]:
    """
    Merge new LLM-generated mappings with existing aliases.
    
    Args:
        new_mappings: New mappings from LLM
        existing_aliases: Existing aliases to preserve
    
    Returns:
        Merged alias dictionary (all keys lowercase)
    """
    if existing_aliases is None:
        existing_aliases = TEAM_ALIASES.copy()
    
    merged = {k.lower(): v for k, v in existing_aliases.items()}
    
    for variant, canonical in new_mappings.items():
        variant_lower = variant.lower()
        canonical_lower = canonical.lower()
        
        # Don't add if variant is already the canonical form
        if variant_lower != canonical_lower:
            merged[variant_lower] = canonical
    
    return merged


def save_aliases(aliases: Dict[str, str], filepath: str = ALIASES_FILE) -> None:
    """
    Save aliases to JSON file.
    
    Args:
        aliases: Dictionary of aliases (will be saved with lowercase keys)
        filepath: Path to save aliases file
    """
    # Convert to lowercase keys for consistency
    aliases_lower = {k.lower(): v for k, v in aliases.items()}
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(aliases_lower, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Saved {len(aliases_lower)} aliases to {filepath}")


def standardize_teams(provider: str = "openai", api_key: str | None = None, save: bool = True, use_heuristics: bool = False) -> Dict[str, str]:
    """
    Main function to standardize team names using LLM or heuristics.
    
    Args:
        provider: LLM provider ("openai", "anthropic", or "heuristics")
        api_key: Optional API key (uses environment variable if None)
        save: If True, save results to aliases.json
        use_heuristics: If True and LLM fails, fall back to heuristics
    
    Returns:
        Dictionary of standardized mappings
    """
    print("Fetching all team names from database...")
    team_names = get_all_team_names()
    print(f"Found {len(team_names)} unique team names")
    
    new_mappings = {}
    
    if provider == "heuristics":
        print("\nUsing heuristics to identify duplicate team names...")
        new_mappings = standardize_with_heuristics(team_names)
    else:
        print(f"\nUsing {provider} to identify duplicate team names...")
        try:
            if provider == "openai":
                new_mappings = standardize_with_llm(team_names, api_key)
            elif provider == "anthropic":
                new_mappings = standardize_with_anthropic(team_names, api_key)
            else:
                raise ValueError(f"Unknown provider: {provider}. Use 'openai', 'anthropic', or 'heuristics'")
        except Exception as e:
            if use_heuristics:
                print(f"\nLLM failed ({e}), falling back to heuristics...")
                new_mappings = standardize_with_heuristics(team_names)
            else:
                raise
    
    print(f"Identified {len(new_mappings)} name mappings")
    
    print("\nMerging with existing aliases...")
    merged_aliases = merge_aliases(new_mappings)
    print(f"Total aliases after merge: {len(merged_aliases)}")
    
    if save:
        save_aliases(merged_aliases)
    
    return merged_aliases


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Standardize team names using LLM")
    parser.add_argument("--provider", choices=["openai", "anthropic"], default="openai",
                       help="LLM provider to use")
    parser.add_argument("--api-key", type=str, help="API key (or set environment variable)")
    parser.add_argument("--no-save", action="store_true", help="Don't save to aliases.json")
    parser.add_argument("--preview", action="store_true", help="Preview mappings without saving")
    
    args = parser.parse_args()
    
    if args.preview:
        args.no_save = True
    
    try:
        aliases = standardize_teams(
            provider=args.provider,
            api_key=args.api_key,
            save=not args.no_save
        )
        
        if args.preview:
            print("\n" + "=" * 70)
            print("PREVIEW - New mappings (not saved):")
            print("=" * 70)
            team_names = get_all_team_names()
            new_mappings = standardize_with_llm(team_names, args.api_key) if args.provider == "openai" else standardize_with_anthropic(team_names, args.api_key)
            for variant, canonical in sorted(new_mappings.items()):
                print(f"  {variant:50s} -> {canonical}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
