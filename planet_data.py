import requests
import json
import os

planet_dict = {
    "Mercury": {"color": "#B0C4DE", "radius": 2440},
    "Venus": {"color": "#F0F8FF", "radius": 6052},
    "Earth": {"color": "#00FF00", "radius": 6371},
    "Moon": {"color": "#FFFFFF", "radius": 1737},
    "Mars": {"color": "#FF6347", "radius": 3390},
    "Jupiter": {"color": "#FF4500", "radius": 69911},
    "Saturn": {"color": "#FFD700", "radius": 58232},
    "Uranus": {"color": "#00CED1", "radius": 25362},
    "Neptune": {"color": "#0000FF", "radius": 24622}
}

class PlanetData:
    """Manages planet metadata with API fetching and caching."""

    def __init__(self, cache_file: str = 'planet_data_cache.json') -> None:
        self.cache_file = cache_file
        self.api_data = self.load_cached_data() or self.fetch_all_planet_data()
        if not os.path.exists(self.cache_file):
            self.save_data_to_cache()

    def load_cached_data(self) -> dict | None:
        """Load cached data from JSON file."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Failed to load cached data: {e}")
        return None

    def save_data_to_cache(self) -> None:
        """Save API data to JSON cache."""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.api_data, f, indent=4)
            print(f"Data cached to {self.cache_file}")
        except IOError as e:
            print(f"Failed to save cache: {e}")

    def fetch_all_planet_data(self) -> dict:
        """Fetch planet data from the API."""
        url = "https://api.le-systeme-solaire.net/rest/bodies/"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            planets = {body['englishName']: body for body in data['bodies'] 
                       if body.get('isPlanet', False) or body['englishName'] == "Moon"}
            all_data = {}
            for planet in planet_dict.keys():
                all_data[planet] = planets.get(planet, {
                    "englishName": planet, "mass": {"massValue": 0, "massExponent": 0},
                    "avgTemp": "N/A", "semimajorAxis": "N/A", "sideralOrbit": "N/A",
                    "meanRadius": planet_dict[planet]["radius"], "density": "N/A", "gravity": "N/A"
                })
            return all_data
        except requests.RequestException as e:
            print(f"Failed to fetch API data: {e}")
            return {planet: {"englishName": planet, "mass": {"massValue": 0, "massExponent": 0},
                            "avgTemp": "N/A", "semimajorAxis": "N/A", "sideralOrbit": "N/A",
                            "meanRadius": planet_dict[planet]["radius"], "density": "N/A", "gravity": "N/A"}
                    for planet in planet_dict.keys()}

    def get_planet_info(self, planet_name: str) -> dict | None:
        """Retrieve detailed planet info."""
        data = self.api_data.get(planet_name)
        if data:
            mass = data.get('mass', {})
            mass_value = mass.get('massValue', 0) * 10 ** mass.get('massExponent', 0)
            distance_km = data.get('semimajorAxis', "N/A")
            distance_au = float(distance_km) / 149597870.7 if distance_km != "N/A" else "N/A"
            return {
                "mass": f"{mass_value:.2e} kg" if mass_value else "N/A",
                "temperature": f"{data.get('avgTemp', 'N/A')} K",
                "distance": f"{distance_au:.6f} AU" if distance_au != "N/A" else "N/A",
                "orbital_period": f"{data.get('sideralOrbit', 'N/A')} days",
                "radius": f"{data.get('meanRadius', planet_dict.get(planet_name, {}).get('radius', 1000))} km",
                "density": f"{data.get('density', 'N/A')} g/cm³",
                "gravity": f"{data.get('gravity', 'N/A')} m/s²"
            }
        print(f"No data for {planet_name}")
        return None

    def get_planet_color(self, planet_name: str) -> str:
        """Get planet display color."""
        return planet_dict.get(planet_name, {}).get("color", "#808080")

    def get_planet_radius(self, planet_name: str) -> float:
        """Get planet radius in kilometers."""
        data = self.api_data.get(planet_name)
        return float(data['meanRadius']) if data and data.get('meanRadius') not in [None, "N/A", 0] else \
               planet_dict.get(planet_name, {}).get("radius", 1000)

    def get_all_planet_names(self) -> list[str]:
        """Get list of all planet names."""
        return list(planet_dict.keys())

# Singleton instance
planet_data = PlanetData()

if __name__ == "__main__":
    print("Earth Data:", planet_data.get_planet_info("Earth"))
    print("Earth Color:", planet_data.get_planet_color("Earth"))
    print("Earth Radius:", planet_data.get_planet_radius("Earth"))
    print("All Planets:", planet_data.get_all_planet_names())