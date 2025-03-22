import requests
from concurrent.futures import ThreadPoolExecutor

API_KEY = "e4DaIssgKChVTbypjUeacg==0bS11B9YahMDJUXG"
BASE_URL = "https://api.api-ninjas.com/v1/planets"
PLANETS = ["mercury", "venus", "earth", "mars", "jupiter", "saturn", "uranus", "neptune"]

def fetch_planet_data(planet_name):
    try:
        headers = {"X-Api-Key": API_KEY}
        response = requests.get(f"{BASE_URL}?name={planet_name}", headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()
        return data[0] if data else None
    except requests.RequestException as e:
        print(f"Failed to fetch data for {planet_name}: {e}")
        return None

def fetch_all_planet_data(planets=PLANETS):
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = {planet: fetch_planet_data(planet) for planet in planets}
    return results