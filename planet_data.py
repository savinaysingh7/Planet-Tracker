import requests
from concurrent.futures import ThreadPoolExecutor
import time

# Planet dictionary with colors and radii (bodies are defined in planet_calculations.py)
planet_dict = {
    "Mercury": {"color": "#B0C4DE", "radius": 2440},
    "Venus": {"color": "#F0F8FF", "radius": 6052},
    "Earth": {"color": "#00FF00", "radius": 6371},
    "Mars": {"color": "#FF6347", "radius": 3390},
    "Jupiter": {"color": "#FF4500", "radius": 69911},
    "Saturn": {"color": "#FFD700", "radius": 58232},
    "Uranus": {"color": "#00CED1", "radius": 25362},
    "Neptune": {"color": "#0000FF", "radius": 24622}
}

# API setup (temporary, will transition to astroquery for more accurate data later)
API_KEY = "e4DaIssgKChVTbypjUeacg==0bS11B9YahMDJUXG"
BASE_URL = "https://api.api-ninjas.com/v1/planets"
PLANETS = ["mercury", "venus", "earth", "mars", "jupiter", "saturn", "uranus", "neptune"]

class PlanetData:
    """Class to manage planet metadata and API data."""
    
    def __init__(self):
        """Initialize with preloaded API data."""
        self.api_data = self.fetch_all_planet_data()
    
    def fetch_planet_data(self, planet_name, retries=3):
        """Fetch planetary data from API Ninjas with retries."""
        planet_name_lower = planet_name.lower()
        if planet_name_lower not in PLANETS:
            print(f"No API support for {planet_name}")
            return None
        for attempt in range(retries):
            try:
                headers = {"X-Api-Key": API_KEY}
                response = requests.get(f"{BASE_URL}?name={planet_name_lower}", headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()
                return data[0] if data else None
            except requests.RequestException as e:
                print(f"Attempt {attempt+1}/{retries} failed for {planet_name}: {e}")
                if attempt < retries - 1:
                    time.sleep(2)
        print(f"Failed to fetch data for {planet_name} after {retries} attempts")
        return None

    def fetch_all_planet_data(self, planets=PLANETS):
        """Fetch data for all planets in parallel and return as a dictionary."""
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = {planet.capitalize(): self.fetch_planet_data(planet) for planet in planets}
        return results

    def get_planet_info(self, planet_name):
        """Retrieve additional info for a planet from API data."""
        data = self.api_data.get(planet_name)
        if data:
            return {
                "mass": data.get("mass", "N/A"),
                "temperature": data.get("temperature", "N/A"),
                "distance": data.get("distance", "N/A"),
                "orbital_period": data.get("orbital_period", "N/A")
            }
        print(f"No API data available for {planet_name}")
        return None

    def get_planet_color(self, planet_name):
        """Get the display color for a planet."""
        color = planet_dict.get(planet_name, {}).get("color")
        if not color:
            print(f"No color defined for {planet_name}, defaulting to gray")
            return "#808080"  # Default gray for undefined bodies
        return color

    def get_planet_radius(self, planet_name):
        """Get the radius of a planet in kilometers."""
        radius = planet_dict.get(planet_name, {}).get("radius")
        if not radius:
            print(f"No radius defined for {planet_name}, defaulting to 1000 km")
            return 1000  # Default radius for undefined bodies
        return radius

    def get_all_planet_names(self):
        """Get a list of all planet names."""
        return list(planet_dict.keys())

# Singleton instance for global access
planet_data = PlanetData()

if __name__ == "__main__":
    print("API Data for Earth:", planet_data.get_planet_info("Earth"))
    print("Earth Color:", planet_data.get_planet_color("Earth"))
    print("Earth Radius:", planet_data.get_planet_radius("Earth"))
    print("All Planets:", planet_data.get_all_planet_names())