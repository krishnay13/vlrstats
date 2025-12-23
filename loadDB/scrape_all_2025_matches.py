"""
Scrape all VCT 2025 match URLs from the complete tournament list.
Fetches matches from all 15 completed tournaments.
"""
import requests
from bs4 import BeautifulSoup
import time
from typing import List, Set


# All VCT 2025 events from https://www.vlr.gg/vct-2025
VCT_2025_EVENTS = [
    "https://www.vlr.gg/event/2275/vct-2025-china-kickoff",
    "https://www.vlr.gg/event/2274/vct-2025-americas-kickoff",
    "https://www.vlr.gg/event/2277/vct-2025-pacific-kickoff",
    "https://www.vlr.gg/event/2276/vct-2025-emea-kickoff",
    "https://www.vlr.gg/event/2281/valorant-masters-bangkok-2025",
    "https://www.vlr.gg/event/2347/vct-2025-americas-stage-1",
    "https://www.vlr.gg/event/2359/vct-2025-china-stage-1",
    "https://www.vlr.gg/event/2379/vct-2025-pacific-stage-1",
    "https://www.vlr.gg/event/2380/vct-2025-emea-stage-1",
    "https://www.vlr.gg/event/2282/valorant-masters-toronto-2025",
    "https://www.vlr.gg/event/2499/vct-2025-china-stage-2",
    "https://www.vlr.gg/event/2500/vct-2025-pacific-stage-2",
    "https://www.vlr.gg/event/2498/vct-2025-emea-stage-2",
    "https://www.vlr.gg/event/2501/vct-2025-americas-stage-2",
    "https://www.vlr.gg/event/2283/valorant-champions-2025",
]


def scrape_matches_from_event(event_url: str) -> List[str]:
    """
    Scrape all match URLs from a specific event's matches page.
    """
    # Get event ID from URL
    event_id = event_url.split('/')[4]
    matches_url = f"https://www.vlr.gg/event/matches/{event_id}/"
    
    print(f"Fetching: {matches_url}")
    match_urls = []
    
    try:
        response = requests.get(matches_url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all match links - they're in <a> tags with class containing 'match-item'
        # or in the wf-module-item containers
        match_links = soup.find_all('a', href=True)
        
        for link in match_links:
            href = link['href']
            # Match URLs follow pattern: /542264/team1-vs-team2-event-round
            if href.startswith('/') and '-vs-' in href:
                # Extract the numeric match ID and construct full URL
                parts = href.split('/')
                if len(parts) >= 2 and parts[1].isdigit():
                    full_url = f"https://www.vlr.gg{href}"
                    # Skip showmatches (easy to filter: they typically have "showmatch" in URL)
                    if 'showmatch' not in href.lower():
                        match_urls.append(full_url)
        
        # Deduplicate while preserving order
        seen = set()
        unique_matches = []
        for url in match_urls:
            if url not in seen:
                seen.add(url)
                unique_matches.append(url)
        
        print(f"  Found {len(unique_matches)} unique matches")
        return unique_matches
        
    except Exception as e:
        print(f"  [ERROR] Failed to scrape {matches_url}: {e}")
        return []


def scrape_all_vct_2025_matches() -> List[str]:
    """
    Scrape match URLs from all VCT 2025 events.
    """
    all_matches: Set[str] = set()
    
    print(f"Scraping {len(VCT_2025_EVENTS)} VCT 2025 tournaments...")
    print("=" * 70)
    
    for i, event_url in enumerate(VCT_2025_EVENTS, 1):
        event_name = event_url.split('/')[-1].replace('-', ' ').title()
        print(f"\n[{i}/{len(VCT_2025_EVENTS)}] {event_name}")
        
        matches = scrape_matches_from_event(event_url)
        all_matches.update(matches)
        
        # Be polite to the server
        time.sleep(2)
    
    print("\n" + "=" * 70)
    print(f"Total unique matches found: {len(all_matches)}")
    
    # Sort by match ID (ascending chronological order)
    sorted_matches = sorted(all_matches, key=lambda url: int(url.split('/')[3]))
    
    return sorted_matches


def save_matches_to_file(matches: List[str], filename: str = "matches_2025_full.txt"):
    """
    Save match URLs to a text file.
    """
    with open(filename, 'w') as f:
        for url in matches:
            f.write(f"{url}\n")
    print(f"\n[OK] Saved {len(matches)} match URLs to {filename}")


if __name__ == "__main__":
    print("VCT 2025 Match URL Scraper")
    print("=" * 70)
    
    # Scrape all matches
    matches = scrape_all_vct_2025_matches()
    
    # Save to file
    if matches:
        save_matches_to_file(matches)
        
        # Show sample
        print(f"\nFirst 5 matches:")
        for url in matches[:5]:
            print(f"  {url}")
        
        print(f"\nLast 5 matches:")
        for url in matches[-5:]:
            print(f"  {url}")
    else:
        print("\n[ERROR] No matches found!")
