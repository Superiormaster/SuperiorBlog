import requests
from datetime import datetime

API_KEY = "YOUR_API_KEY"
BASE_URL = "https://api.football-data.org/v4"

HEADERS = {"X-Auth-Token": API_KEY}

def get_live_matches(league_code="PL"):  # PL = Premier League
    url = f"{BASE_URL}/competitions/{league_code}/matches?status=LIVE"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json().get("matches", [])
    return []

def get_upcoming_matches(league_code="PL"):
    url = f"{BASE_URL}/competitions/{league_code}/matches?status=SCHEDULED"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json().get("matches", [])
    return []
"""
def get_league_table(league_code="PL"):
    url = f"{BASE_URL}/competitions/{league_code}/standings"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json().get("standings", [])
    return []"""
def get_league_table(league_code="PL"):
    url = f"{BASE_URL}/competitions/{league_code}/standings"
    r = requests.get(url, headers=HEADERS)

    print("STATUS:", r.status_code)
    print("RAW RESPONSE:", r.text[:300])

    return r.json().get("standings", []) if r.status_code == 200 else []