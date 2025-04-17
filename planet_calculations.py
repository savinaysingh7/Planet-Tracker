import skyfield # Use top-level import for clarity
from skyfield.api import load, Angle # Import specific types if needed
from skyfield.timelib import Time # Import Time for type hinting
from datetime import datetime, timedelta, UTC
import numpy as np
from skyfield.elementslib import osculating_elements_of
from skyfield.searchlib import find_discrete, find_maxima, find_minima # Import find_minima too
from functools import lru_cache
from typing import List, Dict, Tuple, Union, Optional # Added Optional
import logging
import sys # Import sys for SystemExit

# Configure logging (Ensure this is configured suitably by the main application)
logger = logging.getLogger(__name__)

# --- Ephemeris Loading ---
# Define ephemeris file name for easier modification
EPHEMERIS_FILE = 'de421.bsp'
planets = None # Initialize planets to None
ts = None      # Initialize ts to None
# Define Moon object holder after planets loaded
moon = None

try:
    # Attempt to load the ephemeris and timescale
    planets = load(EPHEMERIS_FILE)
    ts = load.timescale()
    logger.info(f"Timescale loaded successfully.")

    # Use fallback if ephemeris doesn't directly expose jalpha/jomega
    # Adding a small buffer to avoid potential edge issues with calculations
    # These are the bounds Skyfield *can* calculate for based on the loaded file.
    ephem_start_jd = getattr(planets, 'jalpha', ts.from_datetime(datetime(1900, 1, 1, tzinfo=UTC)).tt) + 0.1
    ephem_end_jd = getattr(planets, 'jomega', ts.from_datetime(datetime(2050, 1, 1, tzinfo=UTC)).tt) - 0.1

    # Log the effective range loaded from the ephemeris file
    try:
         start_time_obj = ts.tt(jd=ephem_start_jd)
         end_time_obj = ts.tt(jd=ephem_end_jd)
         logger.info(f"Ephemeris '{EPHEMERIS_FILE}' loaded. Effective calculation range: "
                     f"{start_time_obj.utc_strftime('%Y-%m-%d')} to {end_time_obj.utc_strftime('%Y-%m-%d')}")
    except Exception as e:
        logger.error(f"Could not format ephemeris range dates: {e}")
        logger.info(f"Ephemeris '{EPHEMERIS_FILE}' loaded. Effective JD range: {ephem_start_jd:.2f} to {ephem_end_jd:.2f}")

except FileNotFoundError:
    err_msg = f"FATAL: Ephemeris file ('{EPHEMERIS_FILE}') not found. Download it first (e.g., using skyfield.iokit.load_file)."
    logger.critical(err_msg)
    sys.exit(err_msg) # Use sys.exit for clarity on critical startup failure
except Exception as e:
    err_msg = f"FATAL: Failed to load ephemeris ('{EPHEMERIS_FILE}'): {e}"
    logger.critical(err_msg, exc_info=True)
    sys.exit(err_msg)

# Check if essential bodies were loaded
if planets is None or ts is None:
     # This case should be caught above, but added as a failsafe
     err_msg = "FATAL: Ephemeris or timescale failed to initialize."
     logger.critical(err_msg)
     sys.exit(err_msg)

# Standardize access to Earth, preferring 'earth' if available
# Need to handle case where 'earth barycenter' exists but 'earth' itself does not
earth_body_name = None
if 'earth' in planets:
    earth_body_name = 'earth'
elif 'earth barycenter' in planets:
    earth_body_name = 'earth barycenter'

# Check if sun, a valid earth representation, and moon are loaded
moon_loaded = 'moon' in planets
if 'sun' not in planets or earth_body_name is None or not moon_loaded:
     err_msg = f"FATAL: Essential body missing: " \
               f"sun={'found' if 'sun' in planets else 'MISSING'}, " \
               f"Earth={'found ('+earth_body_name+')' if earth_body_name else 'MISSING'}, " \
               f"Moon={'found' if moon_loaded else 'MISSING'}."
     logger.critical(err_msg)
     sys.exit("Ephemeris file seems incomplete or invalid (Missing Sun, Earth, or Moon).")

sun = planets['sun']
earth = planets[earth_body_name]
moon = planets['moon'] # Assign Moon object now that we know it exists
logger.info(f"Using '{earth_body_name}' for Earth calculations.")

# --- Planet Dictionary (for body object lookup) ---
# Map user-facing names to Skyfield body objects loaded from the ephemeris
# Includes fallbacks for common naming variations (e.g., barycenter vs body)
planet_dict = {}
default_bodies = {
    "Mercury": 'mercury',
    "Venus": 'venus',
    "Earth": earth_body_name, # Use the dynamically determined Earth name
    "Moon": 'moon', # Reference the specific Moon object
    "Mars": 'mars barycenter', # Prefer barycenter for outer planets if available
    "Jupiter": 'jupiter barycenter',
    "Saturn": 'saturn barycenter',
    "Uranus": 'uranus barycenter',
    "Neptune": 'neptune barycenter'
}
fallback_bodies = { # Map names to fallback keys if primary isn't found
    "Mars": "mars",
    "Jupiter": "jupiter",
    "Saturn": "saturn",
    "Uranus": "uranus",
    "Neptune": "neptune"
}

for name, primary_key in default_bodies.items():
    if primary_key in planets:
         planet_dict[name] = {"body": planets[primary_key]}
         logger.debug(f"Mapped '{name}' to ephemeris object '{primary_key}'.")
    elif name in fallback_bodies and fallback_bodies[name] in planets:
         fallback_key = fallback_bodies[name]
         planet_dict[name] = {"body": planets[fallback_key]}
         logger.info(f"Mapped '{name}' using fallback ephemeris object '{fallback_key}' (primary '{primary_key}' not found).")
    else:
        # Check if body name itself exists (for standard planets)
        body_exists = planets.names().get(name.lower()) is not None
        if primary_key not in planets and not body_exists:
            logger.warning(f"Body for '{name}' (tried keys: '{primary_key}'"
                           f"{f', fallback: \'{fallback_bodies[name]}\'' if name in fallback_bodies else ''})"
                           f" not found in loaded ephemeris. Calculations for '{name}' will fail.")

logger.info(f"Mapped {len(planet_dict)} bodies from configuration to ephemeris objects: {list(planet_dict.keys())}")

# --- Constants for Application Logic ---
# Application Date Range Constants (used for GUI constraints, user input validation)
# These define the *intended* operational range of the application.
EPHEMERIS_START = datetime(1900, 1, 1, tzinfo=UTC)
EPHEMERIS_END = datetime(2050, 1, 1, tzinfo=UTC)

# Validate the application's desired range against the actual loaded ephemeris effective range
try:
    app_start_jd = ts.from_datetime(EPHEMERIS_START).tt
    app_end_jd = ts.from_datetime(EPHEMERIS_END).tt
    # Compare app range to buffered ephem range
    if app_start_jd < ephem_start_jd or app_end_jd > ephem_end_jd:
         logger.warning(f"Application's configured date range ({EPHEMERIS_START.strftime('%Y-%m-%d')} to {EPHEMERIS_END.strftime('%Y-%m-%d')}) "
                        f"partially exceeds the loaded ephemeris' effective calculation range "
                        f"({ts.tt(jd=ephem_start_jd).utc_strftime('%Y-%m-%d')} to {ts.tt(jd=ephem_end_jd).utc_strftime('%Y-%m-%d')}). "
                        "Calculations requested outside the ephemeris range will be clamped or may fail.")
    else:
         logger.info("Application date range is within the effective ephemeris range.")
except Exception as e:
    logger.error(f"Could not validate application date range against ephemeris bounds: {e}")

# MOON_SCALE_FACTOR Removed - Coordinate scaling distorted position.
# Scaling for visual purposes should be done in the plotting layer (e.g., marker size).

# --- Time Parsing Utility ---
def parse_date_time(date_str: str, time_str: str = "12:00:00") -> Time:
    """
    Parses date and optional time strings into a Skyfield Time object (UTC).

    Args:
        date_str: Date string in "YYYY-MM-DD" format.
        time_str: Time string in "HH:MM" or "HH:MM:SS" format (default: "12:00:00").

    Returns:
        A Skyfield Time object.

    Raises:
        ValueError: If the date/time format is invalid or outside the supported ephemeris range.
    """
    if ts is None: # Should not happen if module loads correctly, but safety check
         raise RuntimeError("Timescale (ts) is not initialized. Cannot parse date/time.")
    # Try parsing with seconds, fall back to minutes
    try:
        dt_obj = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            dt_obj = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        except ValueError as e:
             err = f"Invalid date/time format: '{date_str} {time_str}'. Use YYYY-MM-DD and HH:MM[:SS]. Error: {e}"
             logger.error(err)
             raise ValueError(err) from e

    dt_utc = dt_obj.replace(tzinfo=UTC)
    t = ts.from_datetime(dt_utc)

    # Validate against *actual loaded ephemeris bounds* (most critical check)
    # Use the buffered bounds to avoid edge case errors
    if not (ephem_start_jd <= t.tt <= ephem_end_jd):
         err = (f"Date {dt_utc.strftime('%Y-%m-%d %H:%M:%S')} (JD {t.tt:.4f}) is outside loaded ephemeris effective range "
                f"(JD {ephem_start_jd:.4f} to {ephem_end_jd:.4f}).")
         logger.error(err)
         raise ValueError(err)
    return t

# --- Orbit Calculation ---
@lru_cache(maxsize=32) # Cache recent orbit calculations
def calculate_orbit(planet_name: str, t_start_jd_input: float, t_end_jd_input: float, num_points: int = 365) -> np.ndarray:
    """
    Calculates heliocentric orbit positions for planets or Moon
    between two Julian Dates (TT), clamped to ephemeris bounds.

    Args:
        planet_name: The name of the body (e.g., "Mars", "Moon").
        t_start_jd_input: Requested start Julian Date (TT).
        t_end_jd_input: Requested end Julian Date (TT).
        num_points: Number of points to calculate along the orbit.

    Returns:
        A numpy array of shape (3, num_points) containing heliocentric [x, y, z] coordinates in AU,
        or an empty array (3, 0) if calculation fails or planet is invalid.
    """
    if planet_name not in planet_dict:
        logger.warning(f"Invalid planet name '{planet_name}' requested for orbit calculation.")
        return np.empty((3, 0))

    if num_points <= 1:
        logger.warning(f"Cannot calculate orbit with num_points <= 1 (got {num_points}) for {planet_name}.")
        return np.empty((3, 0))
    if ts is None or planets is None: # Should not happen
         logger.critical("Ephemeris/timescale not loaded, cannot calculate orbit.")
         return np.empty((3, 0))

    # Clamp requested times to the actual loaded ephemeris bounds (using buffered values)
    t_start_clamped_jd = max(t_start_jd_input, ephem_start_jd)
    t_end_clamped_jd = min(t_end_jd_input, ephem_end_jd)

    # Check for valid duration *after* clamping
    if t_start_clamped_jd >= t_end_clamped_jd - 1e-6: # Allow very small intervals, prevent negative/zero
        logger.warning(f"Orbit range for {planet_name} has zero or negative duration after clamping to ephemeris bounds: "
                       f"Clamped Start JD {t_start_clamped_jd:.4f}, Clamped End JD {t_end_clamped_jd:.4f} "
                       f"(Requested: {t_start_jd_input:.4f} to {t_end_jd_input:.4f})")
        return np.empty((3, 0))

    # Convert clamped JDs to Time objects
    try:
        t_start = ts.tt(jd=t_start_clamped_jd)
        t_end = ts.tt(jd=t_end_clamped_jd)
    except ValueError as e:
        logger.error(f"Failed to create Time objects from clamped JDs ({t_start_clamped_jd}, {t_end_clamped_jd}) "
                     f"for {planet_name} orbit: {e}", exc_info=True)
        return np.empty((3, 0))

    logger.info(f"Calculating orbit for {planet_name} from {t_start.utc_iso()} to {t_end.utc_iso()} ({num_points} points).")
    try:
        times = ts.linspace(t_start, t_end, num_points)
    except ValueError as e:
        logger.error(f"Failed during ts.linspace for {planet_name} ({t_start.utc_iso()} to {t_end.utc_iso()}) "
                     f"with {num_points} points: {e}", exc_info=True)
        return np.empty((3, 0))

    planet_body = planet_dict[planet_name]["body"]
    positions = np.empty((3, 0)) # Initialize as empty
    try:
        if planet_name == "Moon":
            # Calculate Earth's heliocentric position vector at all times
            earth_pos_helio = (earth - sun).at(times)
            # Calculate Moon's geocentric position vector relative to Earth at all times
            moon_pos_geo = (moon - earth).at(times)
            # Add vectors to get Moon's heliocentric position
            # Access .position.au which returns the (3, N) array
            positions = earth_pos_helio.position.au + moon_pos_geo.position.au
            logger.debug(f"Calculated heliocentric orbit for Moon (Earth vector + Moon vector).")
        else:
            # Standard heliocentric position relative to Sun body
            pos_vectors = (planet_body - sun).at(times)
            positions = pos_vectors.position.au # shape (3, N)
            logger.debug(f"Calculated heliocentric orbit for {planet_name}")

        # Check result shape
        if not isinstance(positions, np.ndarray) or positions.ndim != 2 or positions.shape[0] != 3:
             logger.error(f"Orbit calculation for {planet_name} resulted in unexpected position data shape: {getattr(positions,'shape',type(positions))}")
             return np.empty((3,0))

    except ValueError as e:
        logger.error(f"ValueError during orbit points calculation for {planet_name}: {e}", exc_info=False)
        return np.empty((3, 0))
    except Exception as e:
        logger.error(f"Unexpected error calculating orbit points for {planet_name}: {e}", exc_info=True)
        return np.empty((3, 0))

    # Final validation on the computed array shape vs expected num_points
    if positions.shape[1] != num_points:
        logger.error(f"Orbit calculation for {planet_name} resulted in wrong number of points: {positions.shape[1]} (expected {num_points})")
        # Decide whether to return partial result or empty (returning empty is safer)
        return np.empty((3,0))

    logger.debug(f"Orbit calculation successful for {planet_name}: shape={positions.shape}")
    return positions

# --- Instantaneous Position Calculation ---
def get_heliocentric_positions(selected_planets: List[str], t: Time) -> Dict[str, np.ndarray]:
    """
    Calculates heliocentric positions for selected planets (including Moon)
    at a specific time `t`, checking ephemeris bounds.

    Args:
        selected_planets: List of planet names (must be keys in `planet_dict`).
        t: Skyfield Time object for the desired time.

    Returns:
        A dictionary mapping planet names to their heliocentric [x, y, z] position vectors
        (np.ndarray, shape (3,)) in AU. Returns an empty dictionary if the time `t`
        is invalid or outside ephemeris range.
    """
    positions = {}
    if not isinstance(t, Time):
        logger.error(f"Invalid time object provided to get_heliocentric_positions: {type(t)}")
        return {}
    if ts is None or planets is None or earth is None or sun is None or moon is None: # Check all needed globals
        logger.critical("Core objects (ts, planets, earth, sun, moon) not loaded. Cannot get positions.")
        return {}

    # Check if time t is within the effective ephemeris range (critical)
    if not (ephem_start_jd <= t.tt <= ephem_end_jd):
        logger.error(f"Time {t.utc_iso()} (JD {t.tt:.4f}) is outside loaded ephemeris effective range. Cannot calculate positions.")
        return {}

    # Pre-calculate Earth's heliocentric position at time t if Moon is requested
    earth_pos_helio_au = None
    if "Moon" in selected_planets:
        try:
             earth_pos_helio_au = (earth - sun).at(t).position.au
        except Exception as e:
             logger.error(f"Failed to calculate Earth's heliocentric position for Moon calculation at {t.utc_iso()}: {e}")
             return {} # Cannot calculate Moon without Earth position

    for name in selected_planets:
        if name not in planet_dict:
            logger.warning(f"Planet '{name}' not found in planet_dict, skipped in get_heliocentric_positions.")
            continue

        planet_body = planet_dict[name]["body"]
        pos_au = None # Initialize position for this body
        try:
            if name == "Moon":
                # Use pre-calculated Earth position if available
                if earth_pos_helio_au is None:
                     logger.warning("Skipping Moon position as Earth position calculation failed earlier.")
                     continue
                # Calculate Moon's position relative to Earth
                moon_pos_geo_vector = (moon - earth).at(t)
                moon_pos_geo_au = moon_pos_geo_vector.position.au
                # Add vectors to get Moon's heliocentric position
                pos_au = earth_pos_helio_au + moon_pos_geo_au
                logger.debug(f"Calculated heliocentric position for Moon at {t.utc_iso()}")
            else:
                # Standard Heliocentric relative to Sun
                pos_vector = (planet_body - sun).at(t)
                pos_au = pos_vector.position.au # pos_au is a (3,) numpy array
                logger.debug(f"Calculated heliocentric position for {name} at {t.utc_iso()}")

            # Validate shape and store
            if isinstance(pos_au, np.ndarray) and pos_au.shape == (3,):
                 positions[name] = pos_au
            else:
                 logger.error(f"Position calculation for {name} at {t.utc_iso()} returned invalid shape/type: {getattr(pos_au, 'shape', type(pos_au))}")
        except ValueError as e:
             logger.error(f"ValueError calculating position for {name} at {t.utc_iso()}: {e}", exc_info=False)
             continue # Continue to next planet
        except Exception as e:
            logger.error(f"Unexpected error calculating position for {name} at {t.utc_iso()}: {e}", exc_info=True)
            continue # Continue to next planet

    return positions


# --- Orbital Elements ---
# Note: This function calculates elements RELATIVE TO THE CENTER (Sun or Earth for Moon).
# It does NOT return heliocentric elements for the Moon, which is usually correct for analysis.
def get_orbital_elements(planet_name: str, t: Time) -> Dict[str, float]:
    """
    Calculates instantaneous osculating orbital elements (semi-major axis and eccentricity)
    relative to the appropriate center (Sun, or Earth for Moon), checking ephemeris bounds.

    Args:
        planet_name: The name of the planet (must be key in `planet_dict`).
        t: Skyfield Time object.

    Returns:
        A dictionary with 'semi_major_axis' (AU) and 'eccentricity' (dimensionless),
        or default values (0.0) if calculation fails or inputs invalid.
    """
    default_elements = {"semi_major_axis": 0.0, "eccentricity": 0.0}

    if planet_name not in planet_dict:
        logger.warning(f"Invalid planet name '{planet_name}' for orbital elements calculation.")
        return default_elements
    if not isinstance(t, Time):
        logger.error(f"Invalid time object provided for orbital elements: {type(t)}")
        return default_elements
    # Check prerequisites
    if ts is None or planets is None or sun is None or earth is None or moon is None:
        logger.critical("Core objects not loaded, cannot get elements.")
        return default_elements

    # Check if time t is within the effective ephemeris range (critical)
    if not (ephem_start_jd <= t.tt <= ephem_end_jd):
        logger.error(f"Time {t.utc_iso()} (JD {t.tt:.4f}) is outside loaded ephemeris effective range. Cannot calculate elements for {planet_name}.")
        return default_elements

    planet_body = planet_dict[planet_name]["body"]
    try:
        # Determine the center body for element calculation
        center_body = earth if planet_name == "Moon" else sun
        center_name = "Earth" if planet_name == "Moon" else "Sun"
        logger.debug(f"Calculating orbital elements for {planet_name} relative to {center_name} at {t.utc_iso()}")

        relative_vector = (planet_body - center_body).at(t)
        elements = osculating_elements_of(relative_vector)

        semi_major_axis_au = elements.semi_major_axis.au
        ecc = elements.eccentricity
        # Basic validation
        if not (isinstance(semi_major_axis_au, float) and semi_major_axis_au >= 0):
             logger.warning(f"Calculated semi-major axis for {planet_name} is invalid: {semi_major_axis_au}")
             semi_major_axis_au = 0.0 # Fallback
        # Eccentricity check: usually < 1 for bound orbits, but elements can be slightly >= 1 near parabola
        if not (isinstance(ecc, float) and ecc >= 0.0):
            logger.warning(f"Calculated eccentricity for {planet_name} is negative or invalid: {ecc}")
            ecc = 0.0 # Fallback
        elif ecc > 1.1: # Warn if clearly hyperbolic/unusual for typical request
             logger.warning(f"Calculated eccentricity for {planet_name} is high (hyperbolic?): {ecc:.5f}")


        return {"semi_major_axis": semi_major_axis_au, "eccentricity": ecc}

    except ValueError as e: # Skyfield internal value error
         logger.error(f"ValueError calculating elements for {planet_name} at {t.utc_iso()}: {e}", exc_info=False)
         return default_elements
    except AttributeError as e: # Structure changes
        logger.error(f"AttributeError calculating elements for {planet_name} at {t.utc_iso()}: {e}", exc_info=True)
        return default_elements
    except Exception as e: # Other errors
         logger.error(f"Unexpected error calculating orbital elements for {planet_name} at {t.utc_iso()}: {e}", exc_info=True)
         return default_elements

# --- Event Calculation Helpers ---
def _calculate_angle(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Helper: Calculate angle degrees between two 3D vectors. Handles zero vectors, clips cosine."""
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 < 1e-12 or norm2 < 1e-12: # Use tolerance for near-zero norms
        return 0.0
    dot_product = np.dot(vec1, vec2)
    cos_angle = np.clip(dot_product / (norm1 * norm2), -1.0, 1.0)
    angle_rad = np.arccos(cos_angle)
    return np.degrees(angle_rad)

# --- Approximate Geometric Event Check (for specific time) ---
def calculate_events(t: Time, angle_threshold: float = 5.0) -> List[Tuple[str, str]]:
    """Detects approximate geometric events at time t. Checks bounds."""
    # Implementation remains the same as previous corrected version, as it calculates relative geometry.
    # Adding checks for prerequisites at the start.
    if not isinstance(t, Time):
        logger.error(f"Invalid time object provided to calculate_events: {type(t)}")
        return []
    if ts is None or planets is None or sun is None or earth is None:
        logger.critical("Core objects not loaded, cannot calculate events.")
        return []
    if not (ephem_start_jd <= t.tt <= ephem_end_jd):
        logger.error(f"Time {t.utc_iso()} (JD {t.tt:.4f}) is outside loaded ephemeris range. Cannot calculate events.")
        return []

    events = []
    try:
        earth_observer = earth.at(t)
        sun_pos_geo = earth_observer.observe(sun).position.au
        earth_pos_helio = (earth - sun).at(t).position.au
        dist_earth_sun = np.linalg.norm(sun_pos_geo)
        if dist_earth_sun < 1e-6: # Avoid division by zero if something weird happens
            logger.error("Earth-Sun distance near zero at {t.utc_iso()}. Cannot calculate geometric events.")
            return []

        for name, data in planet_dict.items():
            if name in ["Earth", "Moon"]: continue
            if "body" not in data: continue
            planet_body = data["body"]
            try:
                 planet_pos_helio = (planet_body - sun).at(t).position.au
                 earth_to_planet_geo = earth_observer.observe(planet_body).position.au
                 elongation_angle = _calculate_angle(sun_pos_geo, earth_to_planet_geo)
                 dist_sun_planet = np.linalg.norm(planet_pos_helio)
                 is_inner_planet = dist_sun_planet < dist_earth_sun

                 if is_inner_planet:
                     if elongation_angle < angle_threshold: events.append((name, "Inferior Conjunction"))
                     elif abs(elongation_angle - 180.0) < angle_threshold: events.append((name, "Superior Conjunction"))
                 else:
                     if abs(elongation_angle - 180.0) < angle_threshold: events.append((name, "Opposition"))
                     elif elongation_angle < angle_threshold: events.append((name, "Superior Conjunction"))
            except ValueError as e: logger.warning(f"ValueError during geometric event check for {name} at {t.utc_iso()}: {e}")
            except Exception as e: logger.warning(f"Unexpected error during geometric event check for {name} at {t.utc_iso()}: {e}")

    except ValueError as e: logger.error(f"ValueError during base vector calculation for geometric events at {t.utc_iso()}: {e}")
    except Exception as e: logger.error(f"Unexpected error during setup for geometric event check at {t.utc_iso()}: {e}", exc_info=True)

    if events: logger.debug(f"Found approximate geometric events at {t.utc_iso()}: {events}")
    return events


# --- Precise Event Finding (using Skyfield Search) ---
def find_next_events( selected_planets: List[str], t_start: Time, t_end: Time,
                     angle_threshold_degrees: float = 1.0, step_days: float = 0.5
                    ) -> List[Tuple[str, str, str]]:
    """Finds precise events based on apparent elongation. Checks bounds."""
    # Implementation remains the same as previous corrected version. It uses apparent positions
    # relative to Earth, so Moon's heliocentric correction isn't directly relevant here.
    # Added prerequisite checks.
    events = []
    if not isinstance(t_start, Time) or not isinstance(t_end, Time):
        logger.error("Invalid Time objects provided to find_next_events.")
        return []
    if t_start.tt >= t_end.tt:
        logger.error(f"Start time ({t_start.utc_iso()}) must be before end time ({t_end.utc_iso()}).")
        return []
    if ts is None or planets is None or sun is None or earth is None:
        logger.critical("Core objects not loaded, cannot find events.")
        return []

    # Clamp search range
    search_start_clamped_jd = max(t_start.tt, ephem_start_jd)
    search_end_clamped_jd = min(t_end.tt, ephem_end_jd)
    if search_start_clamped_jd >= search_end_clamped_jd - 1e-6:
        logger.warning(f"Event search range clamps to zero duration.")
        return []
    search_start_clamped = ts.tt(jd=search_start_clamped_jd)
    search_end_clamped = ts.tt(jd=search_end_clamped_jd)

    logger.info(f"Searching for precise events involving {selected_planets} between {search_start_clamped.utc_iso()} and {search_end_clamped.utc_iso()}")

    for name in selected_planets:
        if name not in planet_dict: continue
        if name in ["Earth", "Moon"]: continue
        planet_body = planet_dict[name]["body"]

        # Elongation function (same as before)
        def elongation_angle_degrees(t: Time) -> Union[float, np.ndarray]:
            try:
                earth_observer = earth.at(t)
                sun_app_vector = earth_observer.observe(sun).apparent().position.au
                planet_app_vector = earth_observer.observe(planet_body).apparent().position.au
                if isinstance(sun_app_vector, np.ndarray) and sun_app_vector.ndim > 1:
                    angles = np.array([_calculate_angle(sv, pv) for sv, pv in zip(sun_app_vector.T, planet_app_vector.T)])
                    return angles
                else: return _calculate_angle(sun_app_vector, planet_app_vector)
            except ValueError as e: return np.nan # Signal error to search
            except Exception as e: logger.warning(f"Elongation calc error for {name}: {e}"); return np.nan
        elongation_angle_degrees.step_days = step_days

        # Perform search (same as before)
        try:
            times_min, angles_min = find_minima(search_start_clamped, search_end_clamped, elongation_angle_degrees)
            times_max, angles_max = find_maxima(search_start_clamped, search_end_clamped, elongation_angle_degrees)

            if times_min is not None: # Process minima
                 for t_event, angle_event_deg in zip(times_min, angles_min):
                    if not np.isnan(angle_event_deg) and angle_event_deg < angle_threshold_degrees:
                        event_date_str = t_event.utc_strftime('%Y-%m-%d %H:%M UTC')
                        try: # Distinguish conjunction type
                            dist_sun_planet = (planet_body - sun).at(t_event).distance().au
                            dist_earth_sun = (earth - sun).at(t_event).distance().au
                            event_type = "Inferior Conjunction" if dist_sun_planet < dist_earth_sun else "Superior Conjunction"
                        except ValueError as e_dist: event_type = "Conjunction (Unknown Type)"
                        events.append((name, event_type, event_date_str)); logger.info(f"Found {event_type} for {name} near {event_date_str}")

            if times_max is not None: # Process maxima
                 for t_event, angle_event_deg in zip(times_max, angles_max):
                     if not np.isnan(angle_event_deg) and abs(angle_event_deg - 180.0) < angle_threshold_degrees:
                         event_date_str = t_event.utc_strftime('%Y-%m-%d %H:%M UTC')
                         try: # Distinguish opposition/conj type
                             dist_sun_planet = (planet_body - sun).at(t_event).distance().au
                             dist_earth_sun = (earth - sun).at(t_event).distance().au
                             event_type = "Opposition" if dist_sun_planet > dist_earth_sun else "Superior Conjunction"
                         except ValueError as e_dist: event_type = "Opposition/Superior Conj. (Unknown Type)"
                         events.append((name, event_type, event_date_str)); logger.info(f"Found {event_type} for {name} near {event_date_str}")

        except ValueError as e: logger.error(f"Skyfield search ValueError for {name}: {e}")
        except Exception as e: logger.error(f"Unexpected error during event search for {name}: {e}", exc_info=True)

    return sorted(events, key=lambda item: item[2])


# --- Module Test Block ---
if __name__ == "__main__":
    # Setup basic logging only when run standalone
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s [%(name)s] - %(message)s')
    module_logger = logging.getLogger(__name__)
    module_logger.info("\n--- Testing Planet Calculations Module (with Moon corrections) ---")

    if planets is None or ts is None or not planet_dict or earth is None or sun is None or moon is None:
        module_logger.critical("Prerequisites not met. Cannot run tests.")
    else:
        try:
            t_test_ref = parse_date_time("2024-06-01", "00:00:00")
            module_logger.info(f"Reference time: {t_test_ref.utc_iso()}")

            # Test Moon position
            module_logger.info("\nTesting Moon Heliocentric Position:")
            moon_pos = get_heliocentric_positions(["Moon"], t_test_ref)
            if "Moon" in moon_pos:
                 module_logger.info(f"  Moon Heliocentric Position (AU): {moon_pos['Moon']}")
                 # Simple sanity check: Moon distance from Earth should be small AU
                 earth_pos = get_heliocentric_positions(["Earth"], t_test_ref)["Earth"]
                 moon_geo_dist = np.linalg.norm(moon_pos["Moon"] - earth_pos)
                 module_logger.info(f"  Implied Moon Geocentric Distance (AU): {moon_geo_dist:.6f} (Expected ~0.0026 AU)")
                 if not (0.002 < moon_geo_dist < 0.003):
                     module_logger.warning("  => Moon geocentric distance seems unexpected.")
            else:
                 module_logger.error("  Failed to calculate Moon position.")

            # Test Moon orbit calculation
            module_logger.info("\nTesting Moon Heliocentric Orbit (5 days):")
            t_orbit_end = ts.tt(jd=t_test_ref.tt + 5)
            moon_orbit = calculate_orbit("Moon", t_test_ref.tt, t_orbit_end.tt, num_points=50)
            if moon_orbit.shape == (3, 50):
                 module_logger.info(f"  Moon orbit calculated, shape {moon_orbit.shape}")
                 # Check first and last point distances from Earth again
                 earth_orbit_vec = (earth-sun).at(ts.linspace(t_test_ref, t_orbit_end, 50)).position.au
                 moon_geo_dist_orbit_start = np.linalg.norm(moon_orbit[:,0] - earth_orbit_vec[:,0])
                 moon_geo_dist_orbit_end = np.linalg.norm(moon_orbit[:,-1] - earth_orbit_vec[:,-1])
                 module_logger.info(f"  Implied Moon Geo Dist Start/End (AU): {moon_geo_dist_orbit_start:.6f} / {moon_geo_dist_orbit_end:.6f}")
                 if not (0.002 < moon_geo_dist_orbit_start < 0.003) or not (0.002 < moon_geo_dist_orbit_end < 0.003):
                     module_logger.warning("  => Moon geocentric distance during orbit seems unexpected.")
            else:
                 module_logger.error(f"  Moon orbit calculation failed or returned wrong shape: {moon_orbit.shape}")

             # Test orbital elements for Moon (should still be geocentric)
            module_logger.info("\nTesting Moon Orbital Elements (Geocentric):")
            moon_elements = get_orbital_elements("Moon", t_test_ref)
            if moon_elements["semi_major_axis"] != 0.0:
                module_logger.info(f"  Moon: SMA={moon_elements['semi_major_axis']:.6f} AU, Ecc={moon_elements['eccentricity']:.5f}")
            else:
                module_logger.warning("  Moon elements calculation failed.")

            module_logger.info("\n--- Other Calculation Tests (as before) ---")
            # (Previous tests for other planets, parsing, events etc. would run here)

        except Exception as e:
             module_logger.critical(f"An unexpected error occurred during tests: {e}", exc_info=True)

    module_logger.info("\n--- Planet Calculations Test Complete ---")

# --- END OF FULL CORRECTED FILE planet_calculations.py ---