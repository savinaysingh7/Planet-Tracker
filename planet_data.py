import requests
import json
import os
import logging
from typing import Dict, List, Optional, Union

# Setup logger for this module
logger = logging.getLogger(__name__)

# Planet dictionary with default colors and radii (our source of truth for which bodies to track)
# Using more standard/common hex codes where applicable, but keeping originals if specific
planet_dict = {
    "Mercury": {"color": "#A9A9A9", "radius": 2440},   # DarkGray
    "Venus": {"color": "#FFF8DC", "radius": 6052},    # Cornsilk (Creamy yellow)
    "Earth": {"color": "#4682B4", "radius": 6371},    # SteelBlue (Dominant ocean color)
    "Moon": {"color": "#D3D3D3", "radius": 1737},     # LightGray
    "Mars": {"color": "#CD5C5C", "radius": 3390},     # IndianRed (Rusty)
    "Jupiter": {"color": "#DEB887", "radius": 69911},  # BurlyWood (Banded appearance)
    "Saturn": {"color": "#F5DEB3", "radius": 58232},  # Wheat (Pale yellow)
    "Uranus": {"color": "#AFEEEE", "radius": 25362},  # PaleTurquoise (Pale blue-green)
    "Neptune": {"color": "#4169E1", "radius": 24622}   # RoyalBlue (Deep blue)
}

class PlanetData:
    """
    Manages planet metadata using L'OpenData du Système solaire API
    with caching, fallback data, and type hinting.

    Fetches data for planets defined in `planet_dict` and the Moon.
    Provides methods to access formatted information, colors, and radii.
    """

    def __init__(self, cache_file: str = 'planet_data_cache.json', api_timeout: int = 15) -> None:
        """
        Initialize with cached or freshly fetched data from the API.

        Args:
            cache_file (str): Path to the JSON file for caching API data.
            api_timeout (int): Timeout in seconds for the API request.
        """
        self.cache_file = cache_file
        self.api_timeout = api_timeout
        self.api_data: Dict[str, Dict] = {} # Initialize with correct type hint

        loaded_data = self.load_cached_data()
        if loaded_data:
            # Use print here as logging might not be fully configured during import
            print(f"PlanetData: Loaded data from cache: {self.cache_file}")
            self.api_data = loaded_data
            # Optional: Could add a check here for data staleness if needed
        else:
            # Use print here for initial status
            print("PlanetData: No cache found or cache invalid/empty. Fetching from API...")
            fetched_data = self.fetch_all_planet_data()
            if fetched_data:
                self.api_data = fetched_data
                self.save_data_to_cache()
            else:
                # API fetch failed completely, use fallback based on defaults
                logger.warning("API fetch failed. Generating fallback data from defaults.")
                self.api_data = self._create_fallback_data()
                # Optionally cache the fallback data too, or leave cache empty
                # self.save_data_to_cache() # Decide if caching fallback is desired
        logger.info(f"PlanetData initialized. Tracking {len(self.api_data)} bodies.")

    def load_cached_data(self) -> Optional[Dict]:
        """
        Load cached data from a local JSON file if it exists and is valid.

        Returns:
            Optional[Dict]: The loaded data as a dictionary, or None if loading fails.
        """
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Basic validation: check if it's a non-empty dictionary
                    if isinstance(data, dict) and data:
                        return data
                    else:
                        logger.warning(f"Cache file {self.cache_file} is empty or not a valid dictionary.")
                        self._remove_invalid_cache()
                        return None
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading or parsing cache file {self.cache_file}: {e}")
                self._remove_invalid_cache()
                return None
            except Exception as e: # Catch unexpected errors during load
                 logger.error(f"Unexpected error loading cache {self.cache_file}: {e}", exc_info=True)
                 self._remove_invalid_cache()
                 return None
        return None

    def _remove_invalid_cache(self) -> None:
        """Attempts to remove the cache file, logging errors."""
        try:
            os.remove(self.cache_file)
            logger.info(f"Removed potentially invalid cache file: {self.cache_file}")
        except OSError as remove_err:
            logger.error(f"Error removing cache file {self.cache_file}: {remove_err}")

    def save_data_to_cache(self) -> None:
        """Save the current API data to a local JSON file."""
        if not self.api_data:
            logger.warning("No planet data available to save to cache.")
            return # Avoid writing an empty cache file if fetch and fallback failed

        try:
            # Create directory if it doesn't exist (e.g., cache_file='cache/data.json')
            cache_dir = os.path.dirname(self.cache_file)
            if cache_dir and not os.path.exists(cache_dir):
                os.makedirs(cache_dir)
                logger.info(f"Created cache directory: {cache_dir}")

            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.api_data, f, indent=4, ensure_ascii=False) # ensure_ascii=False for potential non-latin names if API changes
            logger.info(f"Planet data successfully cached to {self.cache_file}")
        except IOError as e:
            logger.error(f"Failed to write cache to {self.cache_file}: {e}")
        except TypeError as e:
            logger.error(f"Failed to serialize data for caching: {e}")
        except Exception as e: # Catch unexpected errors during save
            logger.error(f"Unexpected error saving cache to {self.cache_file}: {e}", exc_info=True)


    def _create_fallback_data(self) -> Dict[str, Dict]:
        """
        Creates a fallback data structure based on `planet_dict` defaults
        if the API fetch fails entirely. Matches expected keys for `get_planet_info`.
        """
        logger.debug("Creating fallback data structure from planet_dict defaults.")
        fallback = {}
        for planet_name, defaults in planet_dict.items():
            fallback[planet_name] = {
                "englishName": planet_name,
                "isPlanet": (planet_name != "Moon"), # Assume Moon is not a planet
                "mass": None, # Indicate missing data clearly
                "vol": None,
                "density": None,
                "gravity": None,
                "meanRadius": defaults.get("radius", 1000.0), # Use default radius
                "equaRadius": defaults.get("radius", 1000.0),
                "polarRadius": defaults.get("radius", 1000.0),
                "flattening": 0.0,
                "dimension": "",
                "sideralOrbit": None,
                "sideralRotation": None,
                "aroundPlanet": None, # Relevant for Moon
                "discoveredBy": "",
                "discoveryDate": "",
                "alternativeName": "",
                "semimajorAxis": None,
                "perihelion": None,
                "aphelion": None,
                "eccentricity": None,
                "inclination": None,
                "escape": None,
                "avgTemp": None, # Kelvin temp, will be handled in get_planet_info
                "moons": None, # List of moons, None if unknown/not applicable
                "axialTilt": None,
                 # Add other keys returned by API if needed, with None/default values
            }
        # Special handling for Moon if needed (e.g., aroundPlanet)
        if "Moon" in fallback:
             fallback["Moon"]["aroundPlanet"] = {"planet": "Earth", "rel": "https://api.le-systeme-solaire.net/rest/bodies/terre"}
             fallback["Moon"]["isPlanet"] = False
             fallback["Moon"]["semimajorAxis"] = 384400 # Approximate Moon orbit radius in km

        return fallback


    def fetch_all_planet_data(self) -> Optional[Dict[str, Dict]]:
        """
        Fetch data for all bodies from L'OpenData du Système solaire API
        and filter for those defined in `planet_dict`.

        Returns:
            Optional[Dict[str, Dict]]: Dictionary mapping planet names to their
                                      metadata, or None if the fetch fails critically.
        """
        # API endpoint documented at: https://api.le-systeme-solaire.net/en/
        # We fetch all bodies and filter locally, as filtering via API params can be complex
        # URL excludes filters to get all bodies, including Moon, asteroids etc. We filter later.
        url = "https://api.le-systeme-solaire.net/rest/bodies/"
        params = {
             "data": "englishName,isPlanet,mass,vol,density,gravity,meanRadius,sideralOrbit,semimajorAxis,avgTemp", # Request relevant fields
             # Add more fields if needed: equaRadius, polarRadius, flattening, sideralRotation, aroundPlanet, escape, axialTilt, moons, discoveredBy, discoveryDate, alternativeName
             "order": "semimajorAxis,asc" # Optional: Order by distance might make debugging slightly easier
        }

        # Use print here for initial status message
        print(f"PlanetData: Attempting to fetch data from {url}...")
        try:
            response = requests.get(url, params=params, timeout=self.api_timeout)
            response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
            api_response_data = response.json()
            logger.info(f"API data fetched successfully ({response.elapsed.total_seconds():.2f}s).")

            # Process the response
            fetched_bodies = {}
            if 'bodies' in api_response_data and isinstance(api_response_data['bodies'], list):
                 num_fetched = len(api_response_data['bodies'])
                 logger.debug(f"Processing {num_fetched} bodies received from API.")
                 for body in api_response_data['bodies']:
                     # Use englishName as key, ensure it exists
                     name = body.get('englishName')
                     if name:
                         # Normalize name for consistency (e.g., 'La Lune' -> 'Moon', 'Terre' -> 'Earth' - API seems to use English mainly now)
                         # But use capitalization matching our planet_dict
                         name_cap = name.capitalize()
                         # Store if it's one of the bodies we care about defined in planet_dict
                         if name_cap in planet_dict:
                             fetched_bodies[name_cap] = body
            else:
                 logger.warning("API response did not contain a valid 'bodies' list.")
                 return None # Indicate fetch failure if structure is wrong

            # Ensure all planets from our planet_dict are present, using fetched data if available
            final_data = {}
            for planet_name in planet_dict.keys():
                if planet_name in fetched_bodies:
                    final_data[planet_name] = fetched_bodies[planet_name]
                else:
                    # This body was expected (in planet_dict) but not found in the API response
                    logger.warning(f"'{planet_name}' not found in API response. Creating partial fallback entry.")
                    # Create a minimal entry based on defaults, similar to _create_fallback_data but just for one
                    final_data[planet_name] = {
                        "englishName": planet_name,
                        "isPlanet": (planet_name != "Moon"),
                         "mass": None, "avgTemp": None,
                         "semimajorAxis": 384400 if planet_name == "Moon" else None, # Add Moon's SMA default
                         "sideralOrbit": None,
                         "meanRadius": planet_dict[planet_name].get("radius", 1000.0),
                         "density": None, "gravity": None
                    }

            if not final_data:
                 logger.warning("No bodies defined in planet_dict were found in the API response after filtering.")
                 return None # Return None if nothing matched our list

            logger.debug(f"Filtered API data to {len(final_data)} relevant bodies: {list(final_data.keys())}")
            return final_data

        except requests.exceptions.Timeout:
            logger.error(f"API request timed out after {self.api_timeout} seconds.")
            return None
        except requests.exceptions.HTTPError as e:
             logger.error(f"HTTP Error fetching data from API: {e.response.status_code} {e.response.reason}")
             return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to API or other network issue: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response from API: {e}")
            # Log response text safely (limit length)
            try: logger.debug(f"API Response Text (first 500 chars): {response.text[:500]}")
            except NameError: logger.debug("Response object not available.")
            return None
        except Exception as e: # Catch unexpected errors during fetch/processing
            logger.error(f"An unexpected error occurred during API fetch: {e}", exc_info=True)
            return None

    def get_planet_info(self, planet_name: str) -> Optional[Dict[str, str]]:
        """
        Retrieve formatted, human-readable information for a specific planet
        from the stored data.

        Args:
            planet_name (str): The capitalized English name of the planet (e.g., "Mars").

        Returns:
            Optional[Dict[str, str]]: A dictionary containing formatted strings for
                                      various properties, or None if the planet is not found.
        """
        if planet_name not in self.api_data:
             logger.warning(f"No data available for '{planet_name}' in stored API data.")
             # Attempt to provide minimal info based on planet_dict if it exists there
             if planet_name in planet_dict:
                 return {
                     "Name": planet_name,
                     "Mass": "N/A",
                     "Temperature": "N/A",
                     "Distance (AU)": "N/A",
                     "Distance (km)": "N/A",
                     "Orbital Period (days)": "N/A",
                     "Radius (km)": f"{planet_dict[planet_name].get('radius', 'N/A'):,}" if 'radius' in planet_dict[planet_name] else "N/A",
                     "Density (g/cm³)": "N/A",
                     "Gravity (m/s²)": "N/A"
                 }
             return None

        data = self.api_data[planet_name]
        logger.debug(f"Retrieving formatted info for {planet_name} from data: {list(data.keys())}")

        # Helper function for safe formatting of numeric values
        def format_numeric(value: Optional[Union[int, float]], unit: str = "", precision: int = 2, sci_notation: bool = False, allow_zero: bool = True) -> str:
            if value is None or not isinstance(value, (int, float)):
                return "N/A"
            if not allow_zero and abs(value) < 1e-9: # Use tolerance for float comparison
                 return "N/A"
            try:
                if sci_notation:
                    return f"{value:.{precision}e} {unit}".strip()
                else:
                    # Use comma separators for thousands only for integer part
                    # Format spec: ',': Use comma as thousands separator. '.{precision}f': Fixed point number with precision.
                    return f"{value:,.{precision}f} {unit}".strip()
            except (ValueError, TypeError):
                 return "N/A" # Handle potential formatting errors

        # --- Format Individual Properties ---

        # Mass (handle scientific notation format from API)
        mass_str = "N/A"
        mass_data = data.get('mass')
        if mass_data and isinstance(mass_data, dict):
            mass_val = mass_data.get('massValue')
            mass_exp = mass_data.get('massExponent')
            if isinstance(mass_val, (int, float)) and isinstance(mass_exp, int):
                 mass_kg = mass_val * (10 ** mass_exp)
                 mass_str = format_numeric(mass_kg, "kg", 2, sci_notation=True)

        # Temperature (API provides Kelvin)
        temp_k = data.get('avgTemp')
        temp_str = "N/A"
        if isinstance(temp_k, (int, float)) and temp_k > 0: # API often uses 0 for unknown, so >0 is safer
            temp_c = temp_k - 273.15
            # Show only Celsius for brevity, maybe Kelvin in parenthesis if useful
            temp_str = f"{temp_c:.1f} °C" # ({temp_k:.0f} K)"

        # Distance (Semimajor Axis in km from API)
        distance_km = data.get('semimajorAxis')
        distance_au_str = "N/A"
        distance_km_str = "N/A"
        if isinstance(distance_km, (int, float)) and distance_km > 0:
            # Format distance in km with commas
            distance_km_str = format_numeric(distance_km, "", 0) # Precision 0 for integer km
            # Convert km to AU (1 AU ≈ 149,597,870.7 km)
            distance_au = distance_km / 149_597_870.7
            distance_au_str = format_numeric(distance_au, "", 3, allow_zero=False) # AU usually shown with 2-3 decimal places

        # Orbital Period (API provides days)
        orbital_period_days = data.get('sideralOrbit')
        orbital_period_str = format_numeric(orbital_period_days, "days", 2, allow_zero=False)

        # Radius (API provides mean radius in km)
        radius_km = data.get('meanRadius')
        # Fallback to planet_dict radius if API value is missing/invalid
        if not isinstance(radius_km, (int, float)) or radius_km <= 0:
             logger.debug(f"API radius missing/invalid for {planet_name}, falling back to planet_dict.")
             radius_km = planet_dict.get(planet_name, {}).get('radius')
        # Format radius in km with commas
        radius_str = format_numeric(radius_km, "km", 0) # Radius usually shown as integer km

        # Density (API provides g/cm³)
        density_gcm3 = data.get('density')
        density_str = format_numeric(density_gcm3, "g/cm³", 3, allow_zero=False) # Use 3 decimal places for density

        # Gravity (API provides m/s²)
        gravity_ms2 = data.get('gravity')
        gravity_str = format_numeric(gravity_ms2, "m/s²", 2) # Allow zero gravity for edge cases

        # Construct the final dictionary with user-friendly keys
        return {
            "Name": data.get('englishName', planet_name), # Should match planet_name
            "Mass": mass_str,
            "Avg Temp": temp_str,
            "Orbit Radius (AU)": distance_au_str,
            "Orbit Radius (km)": distance_km_str,
            "Orbital Period (days)": orbital_period_str,
            "Mean Radius (km)": radius_str,
            "Density (g/cm³)": density_str,
            "Surface Gravity (m/s²)": gravity_str
        }

    def get_planet_color(self, planet_name: str) -> str:
        """
        Get the display color defined in `planet_dict` for a planet.

        Args:
            planet_name (str): Name of the planet.

        Returns:
            str: Hex color code (#RRGGBB), or default gray if not found.
        """
        return planet_dict.get(planet_name, {}).get("color", "#808080") # Default gray

    def get_planet_radius(self, planet_name: str) -> float:
        """
        Get the mean radius of a planet in kilometers. Prioritizes API data,
        then falls back to `planet_dict`, then to a default value.

        Args:
            planet_name (str): Name of the planet.

        Returns:
            float: Radius in km. Returns 1000.0 as a last resort default.
        """
        # 1. Try API data
        planet_api_data = self.api_data.get(planet_name)
        if planet_api_data:
            radius_api = planet_api_data.get('meanRadius')
            if isinstance(radius_api, (int, float)) and radius_api > 0:
                return float(radius_api)
            else:
                logger.debug(f"API radius data missing or invalid for {planet_name}: {radius_api}")

        # 2. Try hardcoded planet_dict data
        planet_default_data = planet_dict.get(planet_name, {})
        radius_default = planet_default_data.get("radius")
        if isinstance(radius_default, (int, float)) and radius_default > 0:
            logger.debug(f"Using default radius from planet_dict for {planet_name}.")
            return float(radius_default)

        # 3. Ultimate fallback
        logger.warning(f"No valid radius found for {planet_name} from API or defaults. Using fallback: 1000.0 km")
        return 1000.0


    def get_all_planet_names(self) -> List[str]:
        """
        Get a list of all planet names defined in the `planet_dict`.
        These are the bodies this instance is configured to track.

        Returns:
            List[str]: Sorted list of planet names.
        """
        return sorted(list(planet_dict.keys()))

# --- Initialization ---
# Create a 'singleton' instance when the module is imported.
# This instance will handle fetching/caching automatically on first use.
try:
    planet_data = PlanetData()
except Exception as e:
    # Catch potential errors during initialization (e.g., disk permission for cache)
    # Use print here as logger might fail if basicConfig wasn't called by importer yet
    print(f"CRITICAL: Failed to initialize PlanetData: {e}. Some features may be unavailable.")
    logger.critical(f"Failed to initialize PlanetData", exc_info=True)
    # Provide a dummy object or raise the exception depending on application needs
    # Assigning None allows the calling code to check if initialization succeeded
    planet_data = None

# --- Main Execution Block (for testing) ---
if __name__ == "__main__":
    # Setup basic logging for standalone testing
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    print("\n--- PlanetData Module Test ---")

    if planet_data:
        # Test getting info for various planets
        print("\n--- Getting Planet Info ---")
        # Use get_all_planet_names() + a non-existent one for test cases
        test_planets = planet_data.get_all_planet_names() + ["Pluto"]
        for name in test_planets:
            print(f"\nRequesting info for: {name}")
            info = planet_data.get_planet_info(name)
            if info:
                # Print formatted info nicely
                for key, value in info.items():
                    print(f"  {key}: {value}")
            else:
                print(f"  Could not retrieve info for {name}.")

        # Test getting colors
        print("\n--- Getting Planet Colors ---")
        test_color_planets = planet_data.get_all_planet_names() + ["Phobos"]
        for name in test_color_planets:
            color = planet_data.get_planet_color(name)
            print(f"Color for {name}: {color}")

        # Test getting radii
        print("\n--- Getting Planet Radii ---")
        test_radius_planets = planet_data.get_all_planet_names() + ["Ceres"]
        for name in test_radius_planets:
            radius = planet_data.get_planet_radius(name)
            print(f"Radius for {name}: {radius:,.1f} km") # Format output

        # Test getting all names
        print("\n--- All Tracked Planet Names ---")
        all_names = planet_data.get_all_planet_names()
        print(all_names)

        # Example Cache Test (Uncomment to run - requires interactive check or file inspection)
        # print("\n--- Cache Test ---")
        # cache_path = planet_data.cache_file
        # print(f"Check if cache file exists: {cache_path} -> {os.path.exists(cache_path)}")
        # print("If this is the first run or cache was deleted, the next run should load from cache.")
        # if os.path.exists(cache_path):
        #      print("  => Next run SHOULD load from cache.")
        # else:
        #      print("  => Cache file doesn't exist. Data fetched/generated now. Next run SHOULD create/use cache.")

    else:
        print("\nPlanetData object failed to initialize. Cannot run tests.")

    print("\n--- PlanetData Test Complete ---")