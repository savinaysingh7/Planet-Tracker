from skyfield.api import load
from datetime import datetime, timedelta, UTC
import numpy as np
import requests
from concurrent.futures import ThreadPoolExecutor
import time
from skyfield.elementslib import osculating_elements_of
from functools import lru_cache  # Added for caching

# Load Skyfield data
planets = load('de421.bsp')
ts = load.timescale()
sun = planets['sun']
earth = planets['earth']

# Planet dictionary with Skyfield bodies, colors, and radii
planet_dict = {
    "Mercury": {"body": planets['mercury'], "color": "#B0C4DE", "radius": 2440},
    "Venus": {"body": planets['venus'], "color": "#F0F8FF", "radius": 6052},
    "Earth": {"body": planets['earth'], "color": "#00FF00", "radius": 6371},
    "Moon": {"body": planets['moon'], "color": "#FFFFFF", "radius": 1737},
    "Mars": {"body": planets['mars barycenter'], "color": "#FF6347", "radius": 3390},
    "Jupiter": {"body": planets['jupiter barycenter'], "color": "#FF4500", "radius": 69911},
    "Saturn": {"body": planets['saturn barycenter'], "color": "#FFD700", "radius": 58232},
    "Uranus": {"body": planets['uranus barycenter'], "color": "#00CED1", "radius": 25362},
    "Neptune": {"body": planets['neptune barycenter'], "color": "#0000FF", "radius": 24622}
}

# Ephemeris bounds
EPHEMERIS_START = datetime(1899, 7, 29, tzinfo=UTC)
EPHEMERIS_END = datetime(2053, 10, 9, tzinfo=UTC)

# API setup (kept for now, will transition to astroquery later)
API_KEY = "e4DaIssgKChVTbypjUeacg==0bS11B9YahMDJUXG"
BASE_URL = "https://api.api-ninjas.com/v1/planets"
PLANETS = ["mercury", "venus", "earth", "mars", "jupiter", "saturn", "uranus", "neptune"]

# Scaling factor for Moon's geocentric position
MOON_SCALE_FACTOR = 1000

def fetch_planet_data(planet_name, retries=3):
    """Fetch planetary data from API Ninjas with retries."""
    for attempt in range(retries):
        try:
            headers = {"X-Api-Key": API_KEY}
            response = requests.get(f"{BASE_URL}?name={planet_name}", headers=headers, timeout=20)
            response.raise_for_status()
            data = response.json()
            return data[0] if data else None
        except requests.RequestException as e:
            print(f"Attempt {attempt+1}/{retries} failed for {planet_name}: {e}")
            if attempt < retries - 1:
                time.sleep(2)
    print(f"Failed to fetch data for {planet_name} after {retries} attempts")
    return None

def fetch_all_planet_data(planets=PLANETS):
    """Fetch data for all planets in parallel."""
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = {planet.capitalize(): fetch_planet_data(planet) for planet in planets}
    return results

def parse_date_time(date_str, time_str):
    """Parse date and time strings into a Skyfield time object."""
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
    """
    Calculate orbit positions with caching using Julian Dates.
    
    Args:
        planet_name: Name of the planet.
        t_start_jd: Start time in Julian Date.
        t_end_jd: End time in Julian Date.
        num_points: Number of points in the orbit.
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
    """Calculate positions: heliocentric for planets, geocentric for Moon."""
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
    """Calculate orbital elements for a planet at a given time."""
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
    """Calculate opposition, inferior conjunction, and superior conjunction events."""
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

if __name__ == "__main__":
    t = parse_date_time("2025-03-24", "12:00")
    positions = get_heliocentric_positions(["Earth", "Mars"], t)
    print("Heliocentric Positions:", positions)
    orbit = calculate_orbit("Earth", t.tt, parse_date_time("2026-03-24", "12:00").tt)
    print("Earth Orbit Shape:", orbit.shape)
    events = calculate_events(t)
    print("Events:", events)