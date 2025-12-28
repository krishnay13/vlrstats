import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re

ROOT_URL = "https://www.vlr.gg/vct-2025"

async def fetch(session: aiohttp.ClientSession, url: str) -> str:
    async with session.get(url, timeout=20) as resp:
        resp.raise_for_status()
        return await resp.text()

def parse_event_links(html: str) -> list[tuple[str,str]]:
    soup = BeautifulSoup(html, 'html.parser')
    events = []
    for link in soup.find_all('a', href=re.compile(r'/event/\d+')):
        href = link.get('href', '')
        name = link.get_text(strip=True)
        if href.startswith('/event/') and name:
            events.append((name, f"https://www.vlr.gg{href}"))
    # Deduplicate
    seen = set()
    unique = []
    for name, url in events:
        if url not in seen:
            seen.add(url)
            unique.append((name, url))
    return unique

def parse_match_links(html: str, event_url: str) -> list[str]:
    soup = BeautifulSoup(html, 'html.parser')
    matches = []
    for a in soup.find_all('a', href=re.compile(r'^/\d+/[^/]+')):
        href = a.get('href', '')
        if re.match(r'^/\d+/[^/]+', href):
            matches.append(f"https://www.vlr.gg{href}")
    # Deduplicate
    return list(dict.fromkeys(matches))

async def fetch_event_matches(session: aiohttp.ClientSession, event: tuple[str,str], sem: asyncio.Semaphore) -> tuple[str,list[str]]:
    name, url = event
    async with sem:
        # try matches subpage first
        matches_url = url.rstrip('/') + '/matches'
        try:
            html = await fetch(session, matches_url)
        except Exception:
            html = await fetch(session, url)
    match_urls = parse_match_links(html, url)
    return name, match_urls

async def main():
    sem = asyncio.Semaphore(10)
    async with aiohttp.ClientSession() as session:
        root_html = await fetch(session, ROOT_URL)
        events = parse_event_links(root_html)
        tasks = [fetch_event_matches(session, ev, sem) for ev in events]
        results = await asyncio.gather(*tasks)
    all_match_urls = []
    counts = []
    for name, urls in results:
        counts.append((name, len(urls)))
        all_match_urls.extend(urls)
    # Deduplicate
    all_match_urls = list(dict.fromkeys(all_match_urls))
    # Write to root canonical file
    out_path = 'matches_2025_full.txt'
    with open(out_path, 'w') as f:
        for u in all_match_urls:
            f.write(u + '\n')
    print(f"[OK] Saved {len(all_match_urls)} match URLs to {out_path}")
    for name, cnt in counts[:10]:
        print(f"  {name}: {cnt}")

if __name__ == '__main__':
    asyncio.run(main())
