"""
LLM-based team alias normalization using Claude via the Anthropic API.

This module provides intelligent team name normalization by using an LLM
to map variant team names to their canonical forms.
"""
import os
import json
from anthropic import Anthropic

# Initialize Anthropic client
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

def normalize_team_with_llm(team_name: str, known_aliases: dict) -> str:
    """
    Use Claude to normalize a team name by comparing it against known aliases.
    
    Args:
        team_name: The team name to normalize
        known_aliases: Dictionary of known canonical names to lists of aliases
    
    Returns:
        Canonical team name, or the original name if no match found
    """
    # Create a prompt with known teams
    known_teams_list = "\n".join([f"- {canonical}: {', '.join(aliases[:5])}" 
                                   for canonical, aliases in list(known_aliases.items())[:50]])
    
    prompt = f"""You are a team name normalization expert for Valorant esports.

Given a team name, determine if it matches any of these known teams (showing canonical name and some aliases):

{known_teams_list}

Team name to normalize: "{team_name}"

If this team name matches one of the known teams (considering common abbreviations, spacing variations, special characters, etc.), respond with ONLY the canonical team name.
If it doesn't match any known team, respond with ONLY the original team name exactly as provided.

Response (canonical team name only, no explanation):"""
    
    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=50,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        normalized = message.content[0].text.strip()
        return normalized
    
    except Exception as e:
        print(f"LLM normalization failed for '{team_name}': {e}")
        return team_name


def batch_normalize_teams(team_names: list[str], known_aliases: dict) -> dict[str, str]:
    """
    Normalize multiple team names in a single LLM call for efficiency.
    
    Args:
        team_names: List of team names to normalize
        known_aliases: Dictionary of known canonical names to lists of aliases
    
    Returns:
        Dictionary mapping original names to canonical names
    """
    # Create a prompt with known teams
    known_teams_list = "\n".join([f"- {canonical}: {', '.join(aliases[:5])}" 
                                   for canonical, aliases in list(known_aliases.items())[:50]])
    
    teams_to_check = "\n".join([f"{i+1}. {name}" for i, name in enumerate(team_names)])
    
    prompt = f"""You are a team name normalization expert for Valorant esports.

Known teams (canonical name: aliases):
{known_teams_list}

Normalize these team names. For each team, if it matches a known team, use the canonical name. Otherwise, use the original name.

Teams to normalize:
{teams_to_check}

Respond in JSON format only:
{{
  "1": "canonical_name_1",
  "2": "canonical_name_2",
  ...
}}"""
    
    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        response_text = message.content[0].text.strip()
        # Extract JSON if wrapped in markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        result_json = json.loads(response_text)
        
        # Map back to original names
        result = {}
        for i, original_name in enumerate(team_names):
            key = str(i + 1)
            result[original_name] = result_json.get(key, original_name)
        
        return result
    
    except Exception as e:
        print(f"Batch LLM normalization failed: {e}")
        # Fallback: return original names
        return {name: name for name in team_names}


if __name__ == '__main__':
    # Test the normalization
    from loadDB.aliases.teams import TEAM_ALIASES
    
    test_names = [
        "100T",
        "Gen G",
        "Global eSports",
        "2Game Esports",
        "Kru",
        "Team Vitality",
        "Unknown New Team"
    ]
    
    print("Testing individual normalization:")
    for name in test_names:
        normalized = normalize_team_with_llm(name, TEAM_ALIASES)
        print(f"  {name} -> {normalized}")
    
    print("\nTesting batch normalization:")
    batch_result = batch_normalize_teams(test_names, TEAM_ALIASES)
    for original, normalized in batch_result.items():
        print(f"  {original} -> {normalized}")
