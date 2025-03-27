from skyfield.api import load
from datetime import datetime, timedelta, UTC
import numpy as np
from skyfield.elementslib import osculating_elements_of
from skyfield.searchlib import find_discrete
from functools import lru_cache

# Load Skyfield data
planets = load('de421.bsp')
ts = load.timescale()
sun = planets['sun']
earth = planets['earth']

# Planet dictionary with Skyfield bodies (colors and radii sourced from planet_data.py)
planet_dict = {
    "Mercury": {"body": planets['mercury']},
    "Venus": {"body": planets['venus']},
    "Earth": {"body": planets['earth']},
    "Moon": {"body": planets['moon']},
    "Mars": {"body": planets['mars barycenter']},
    "Jupiter": {"body": planets['jupiter barycenter']},
    "Saturn": {"body": planets['saturn barycenter']},
    "Uranus": {"body": planets['uranus barycenter']},
    "Neptune": {"body": planets['neptune barycenter']}
}

# Ephemeris bounds
EPHEMERIS_START = datetime(1899, 7, 29, tzinfo=UTC)
EPHEMERIS_END = datetime(2053, 10, 9, tzinfo=UTC)

# Scaling factor for Moon's geocentric position
MOON_SCALE_FACTOR = 1000

def parse_date_time(date_str, time_str):
    """Parse date and time strings into a Skyfield time object.

    Args:
        date_str (str): Date in 'YYYY-MM-DD' format.
        time_str (str): Time in 'HH:MM' format.

    Returns:
        skyfield.timelib.Time: A Skyfield time object.

    Raises:
        ValueError: If date or time format is invalid or outside ephemeris range.
    """
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Invalid date format: '{date_str}'. Use YYYY-MM-DD (e.g., 2025-03-24).")
    
    try:
        hour, minute = map(int, time_str.split(":"))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
    except ValueError:
        raise ValueError(f"Invalid time format: '{time_str}'. Use HH:MM (e.g., 12:00, 00-23 for hours, 00-59 for minutes).")
    
    dt = datetime(date.year, date.month, date.day, hour, minute, tzinfo=UTC)
    if not (EPHEMERIS_START <= dt <= EPHEMERIS_END):
        raise ValueError(f"Date {dt.strftime('%Y-%m-%d %H:%M')} is outside ephemeris range ({EPHEMERIS_START.date()} to {EPHEMERIS_END.date()}).")
    return ts.from_datetime(dt)

@lru_cache(maxsize=128)
def calculate_orbit(planet_name, t_start_jd, t_end_jd, num_points=100):
    """Calculate orbit positions with caching using Julian Dates.

    Args:
        planet_name (str): Name of the planet.
        t_start_jd (float): Start time in Julian Date.
        t_end_jd (float): End time in Julian Date.
        num_points (int): Number of points in the orbit (default: 100).

    Returns:
        numpy.ndarray: Array of shape (3, num_points) with x, y, z positions in AU.
    """
    t_start = ts.tt(jd=t_start_jd)
    t_end = ts.tt(jd=min(t_end_jd, ts.from_datetime(EPHEMERIS_END).tt))
    t_start = ts.tt(jd=max(t_start.tt, ts.from_datetime(EPHEMERIS_START).tt))
    
    days_covered = (t_end.utc_datetime() - t_start.utc_datetime()).days
    if days_covered <= 0:
        print(f"Invalid orbit range for {planet_name}: {t_start.utc_strftime('%Y-%m-%d')} to {t_end.utc_strftime('%Y-%m-%d')}")
        return np.array([[0], [0], [0]])
    
    times = ts.linspace(t_start, t_end, num_points)
    planet_body = planet_dict[planet_name]["body"]
    
    if planet_name == "Moon":
        positions = [(planet_body - earth).at(ti).position.au * MOON_SCALE_FACTOR for ti in times]
        print(f"Moon orbit calculated (scaled by {MOON_SCALE_FACTOR}x): {len(positions)} points")
    else:
        positions = [(planet_body - sun).at(ti).position.au for ti in times]
    
    result = np.array(positions).T
    print(f"Orbit for {planet_name}: shape={result.shape}")
    return result

def get_heliocentric_positions(selected_planets, t):
    """Calculate positions: heliocentric for planets, geocentric for Moon.

    Args:
        selected_planets (list): List of planet names to calculate positions for.
        t (skyfield.timelib.Time): Time at which to calculate positions.

    Returns:
        dict: Dictionary mapping planet names to their positions (x, y, z) in AU.
    """
    positions = {}
    for name in selected_planets:
        if name == "Moon":
            pos = (planet_dict[name]["body"] - earth).at(t).position.au * MOON_SCALE_FACTOR
            print(f"Moon position scaled by {MOON_SCALE_FACTOR}x: {pos}")
        else:
            pos = (planet_dict[name]["body"] - sun).at(t).position.au
        positions[name] = pos
    return positions

def get_orbital_elements(planet_name, t):
    """Calculate orbital elements for a planet at a given time.

    Args:
        planet_name (str): Name of the planet.
        t (skyfield.timelib.Time): Time at which to calculate elements.

    Returns:
        dict: Dictionary with semi-major axis (AU) and eccentricity.
    """
    if planet_name == "Moon":
        pos_vel = (planet_dict[planet_name]["body"] - earth).at(t)
    else:
        pos_vel = (planet_dict[planet_name]["body"] - sun).at(t)
    elements = osculating_elements_of(pos_vel)
    return {
        "semi_major_axis": elements.semi_major_axis.au,
        "eccentricity": elements.eccentricity
    }

def calculate_events(t, angle_threshold=1.0):
    """Calculate opposition, inferior conjunction, and superior conjunction events.

    Args:
        t (skyfield.timelib.Time): Time at which to check for events.
        angle_threshold (float): Angular threshold in degrees for event detection (default: 1.0).

    Returns:
        list: List of tuples (planet_name, event_type) for detected events.
    """
    events = []
    earth_pos = (planet_dict["Earth"]["body"] - sun).at(t).position.au
    sun_pos = sun.at(t).position.au
    
    for name in planet_dict:
        if name in ["Earth", "Moon"]:
            continue
        planet_pos = (planet_dict[name]["body"] - sun).at(t).position.au
        
        earth_to_planet = planet_pos - earth_pos
        earth_to_sun = sun_pos - earth_pos
        planet_to_sun = sun_pos - planet_pos
        
        cos_angle = np.dot(earth_to_planet, earth_to_sun) / (np.linalg.norm(earth_to_planet) * np.linalg.norm(earth_to_sun))
        angle = np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0)))
        print(f"Angle for {name}: {angle:.2f} degrees")
        
        if name in ["Mercury", "Venus"]:
            if angle < angle_threshold:
                if np.dot(earth_to_planet, earth_to_sun) > 0 and np.linalg.norm(earth_to_planet) < np.linalg.norm(earth_to_sun):
                    events.append((name, "Inferior Conjunction"))
                    print(f"{name} Inferior Conjunction: angle={angle:.2f} degrees")
            elif abs(angle - 180) < angle_threshold and np.linalg.norm(earth_to_sun) < np.linalg.norm(earth_to_planet):
                events.append((name, "Superior Conjunction"))
                print(f"{name} Superior Conjunction: angle={angle:.2f} degrees")
        else:
            if abs(angle - 180) < angle_threshold:
                events.append((name, "Opposition"))
                print(f"{name} Opposition: angle={angle:.2f} degrees")
    
    return events

def find_next_events(selected_planets, t_start, t_end, angle_threshold=1.0):
    """Find upcoming astronomical events (oppositions and conjunctions) within a time range.

    Args:
        selected_planets (list): List of planet names to check for events.
        t_start (skyfield.timelib.Time): Start time for the search.
        t_end (skyfield.timelib.Time): End time for the search.
        angle_threshold (float): Angular threshold in degrees for event detection (default: 1.0).

    Returns:
        list: List of tuples (planet_name, event_type, date_str) for upcoming events.
    """
    events = []
    
    for name in selected_planets:
        if name in ["Earth", "Moon"]:
            continue
        
        planet_body = planet_dict[name]["body"]
        
        def elongation_at(t):
            """Calculate the elongation angle between the Sun and the planet as seen from Earth."""
            e = earth.at(t)
            s = sun.at(t)
            p = planet_body.at(t)
            earth_to_sun = (s - e).position.au
            earth_to_planet = (p - e).position.au
            cos_angle = np.dot(earth_to_planet, earth_to_sun) / (np.linalg.norm(earth_to_planet) * np.linalg.norm(earth_to_sun))
            return np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0)))
        
        elongation_at.step_days = 0.5  # Check every half day for precision
        
        if name in ["Mercury", "Venus"]:
            # Inner planets: Look for conjunctions (elongation ~0° or ~180°)
            times, elongations = find_discrete(t_start, t_end, elongation_at)
            for t, elong in zip(times, elongations):
                if abs(elong) < angle_threshold:
                    # Inferior conjunction: Planet between Earth and Sun
                    planet_dist = (planet_body - sun).at(t).distance().au
                    earth_dist = (earth - sun).at(t).distance().au
                    if planet_dist < earth_dist:
                        events.append((name, "Inferior Conjunction", t.utc_strftime('%Y-%m-%d %H:%M UTC')))
                elif abs(elong - 180) < angle_threshold:
                    # Superior conjunction: Sun between Earth and Planet
                    planet_dist = (planet_body - sun).at(t).distance().au
                    earth_dist = (earth - sun).at(t).distance().au
                    if planet_dist > earth_dist:
                        events.append((name, "Superior Conjunction", t.utc_strftime('%Y-%m-%d %H:%M UTC')))
        else:
            # Outer planets: Look for oppositions (elongation ~180°)
            times, elongations = find_discrete(t_start, t_end, elongation_at)
            for t, elong in zip(times, elongations):
                if abs(elong - 180) < angle_threshold:
                    events.append((name, "Opposition", t.utc_strftime('%Y-%m-%d %H:%M UTC')))
    
    return sorted(events, key=lambda x: x[2])  # Sort by date

if __name__ == "__main__":
    # Test existing functionality
    t = parse_date_time("2025-03-24", "12:00")
    positions = get_heliocentric_positions(["Earth", "Mars"], t)
    print("Heliocentric Positions:", positions)
    orbit = calculate_orbit("Earth", t.tt, parse_date_time("2026-03-24", "12:00").tt)
    print("Earth Orbit Shape:", orbit.shape)
    events = calculate_events(t)
    print("Current Events:", events)
    
    # Test new upcoming events feature
    t_start = ts.now()
    t_end = ts.utc(t_start.utc_datetime().year + 1, t_start.utc_datetime().month, t_start.utc_datetime().day)
    upcoming_events = find_next_events(["Mercury", "Venus", "Mars", "Jupiter"], t_start, t_end)
    print("Upcoming Events:")
    for event in upcoming_events:
        print(f"{event[0]}: {event[1]} on {event[2]}")