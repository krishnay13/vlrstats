#!/usr/bin/env python3
import urllib.request
import json
import time

# Wait a moment for server to respond
time.sleep(2)

try:
    # Test the API
    response = urllib.request.urlopen('http://localhost:3002/api/teams/MIBR')
    data = json.loads(response.read().decode())
    
    print("✓ API response received!")
    print(f"Team: {data.get('name')}")
    print(f"Roster players: {len(data.get('roster', []))}")
    print("\nRoster:")
    for player in data.get('roster', [])[:5]:
        print(f"  - {player.get('player')} ({player.get('team')})")
    
except Exception as e:
    print(f"✗ Error: {e}")
    print(f"  Type: {type(e).__name__}")
