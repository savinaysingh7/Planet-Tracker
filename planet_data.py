import requests
import json
import os

# Planet dictionary with colors and radii (bodies are defined in planet_calculations.py)
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
    """Class to manage planet metadata using L'OpenData du Système solaire API with caching."""

    def __init__(self, cache_file='planet_data_cache.json'):
        """Initialize with cached or freshly fetched data from the API."""
        self.cache_file = cache_file
        self.api_data = self.load_cached_data()
        if not self.api_data:
            self.api_data = self.fetch_all_planet_data()
            self.save_data_to_cache()

    def load_cached_data(self):
        """Load cached data from a local JSON file if it exists."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Failed to load cached data: {e}")
                return None
        return None

    def save_data_to_cache(self):
        """Save fetched API data to a local JSON file."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.api_data, f)
            print(f"Data cached to {self.cache_file}")
        except IOError as e:
            print(f"Failed to save cache: {e}")

    def fetch_all_planet_data(self):
        """Fetch data for all planets from L'OpenData du Système solaire API.

        Returns:
            dict: Dictionary mapping planet names to their metadata.
        """
        url = "https://api.le-systeme-solaire.net/rest/bodies/"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            # Filter for planets and include Moon as a special case
            planets = {body['englishName']: body for body in data['bodies'] 
                      if body.get('isPlanet', False) or body['englishName'] == "Moon"}
            # Ensure all planets in planet_dict are present, even if API fails for some
            all_data = {}
            for planet in planet_dict.keys():
                if planet in planets:
                    all_data[planet] = planets[planet]
                else:
                    # Fallback for missing data
                    all_data[planet] = {
                        "englishName": planet,
                        "mass": {"massValue": 0, "massExponent": 0},
                        "avgTemp": "N/A",
                        "semimajorAxis": "N/A",
                        "sideralOrbit": "N/A",
                        "meanRadius": planet_dict[planet]["radius"],
                        "density": "N/A",
                        "gravity": "N/A"
                    }
            return all_data
        except requests.RequestException as e:
            print(f"Failed to fetch data from API: {e}")
            # Fallback to minimal hardcoded data if API fails
            return {planet: {
                "englishName": planet,
                "mass": {"massValue": 0, "massExponent": 0},
                "avgTemp": "N/A",
                "semimajorAxis": "N/A",
                "sideralOrbit": "N/A",
                "meanRadius": planet_dict[planet]["radius"],
                "density": "N/A",
                "gravity": "N/A"
            } for planet in planet_dict.keys()}

    def get_planet_info(self, planet_name):
        """Retrieve detailed info for a planet from stored API data.

        Args:
            planet_name (str): Name of the planet.

        Returns:
            dict: Dictionary with mass, temperature, distance, orbital period, radius, density, and gravity.
        """
        data = self.api_data.get(planet_name)
        if data:
            mass = data.get('mass', {})
            mass_value = mass.get('massValue', 0) * 10 ** mass.get('massExponent', 0)
            # Convert semimajorAxis from km to AU (1 AU = 149,597,870.7 km)
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
        print(f"No data available for {planet_name}")
        return None

    def get_planet_color(self, planet_name):
        """Get the display color for a planet.

        Args:
            planet_name (str): Name of the planet.

        Returns:
            str: Hex color code or default gray if not found.
        """
        color = planet_dict.get(planet_name, {}).get("color")
        if not color:
            print(f"No color defined for {planet_name}, defaulting to gray")
            return "#808080"  # Default gray for undefined bodies
        return color

    def get_planet_radius(self, planet_name):
        """Get the radius of a planet in kilometers.

        Args:
            planet_name (str): Name of the planet.

        Returns:
            int: Radius in km or default 1000 if not found.
        """
        data = self.api_data.get(planet_name)
        if data and data.get('meanRadius') not in [None, "N/A", 0]:
            return float(data['meanRadius'])
        radius = planet_dict.get(planet_name, {}).get("radius")
        if not radius:
            print(f"No radius defined for {planet_name}, defaulting to 1000 km")
            return 1000  # Default radius for undefined bodies
        return radius

    def get_all_planet_names(self):
        """Get a list of all planet names.

        Returns:
            list: List of planet names.
        """
        return list(planet_dict.keys())

# Singleton instance for global access
planet_data = PlanetData()

if __name__ == "__main__":
    print("Data for Earth:", planet_data.get_planet_info("Earth"))
    print("Earth Color:", planet_data.get_planet_color("Earth"))
    print("Earth Radius:", planet_data.get_planet_radius("Earth"))
    print("All Planets:", planet_data.get_all_planet_names())