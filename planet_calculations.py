import skyfield
from skyfield.api import load
from datetime import datetime, timedelta, UTC
import numpy as np
from skyfield.elementslib import osculating_elements_of
from skyfield.searchlib import find_discrete
from functools import lru_cache
from typing import List, Dict, Tuple, Union
import logging

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Load Skyfield data
planets = load('de421.bsp')
ts = load.timescale()
sun = planets['sun']
earth = planets['earth']

# Planet dictionary with Skyfield bodies
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

EPHEMERIS_START = datetime(1899, 7, 29, tzinfo=UTC)
EPHEMERIS_END = datetime(2053, 10, 9, tzinfo=UTC)
MOON_SCALE_FACTOR = 1000

def parse_date_time(date_str: str, time_str: str) -> 'skyfield.timelib.Time':
    """Parse date and time strings into a Skyfield time object."""
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
        hour, minute = map(int, time_str.split(":"))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
        dt = datetime(date.year, date.month, date.day, hour, minute, tzinfo=UTC)
        if not (EPHEMERIS_START <= dt <= EPHEMERIS_END):
            raise ValueError(f"Date {dt.strftime('%Y-%m-%d %H:%M')} outside ephemeris range.")
        return ts.from_datetime(dt)
    except ValueError as e:
        raise ValueError(f"Invalid date/time: '{date_str} {time_str}'. Use YYYY-MM-DD HH:MM.") from e

@lru_cache(maxsize=128)
def calculate_orbit(planet_name: str, t_start_jd: float, t_end_jd: float, num_points: int = 100) -> np.ndarray:
    """Calculate orbit positions with caching."""
    if planet_name not in planet_dict:
        logger.warning(f"Invalid planet name '{planet_name}'")
        return np.zeros((3, num_points))
    
    t_start = ts.tt(jd=max(t_start_jd, ts.from_datetime(EPHEMERIS_START).tt))
    t_end = ts.tt(jd=min(t_end_jd, ts.from_datetime(EPHEMERIS_END).tt))
    
    if (t_end.utc_datetime() - t_start.utc_datetime()).days <= 0:
        logger.warning(f"Invalid orbit range for {planet_name}")
        return np.zeros((3, num_points))
    
    times = ts.linspace(t_start, t_end, num_points)
    planet_body = planet_dict[planet_name]["body"]
    positions = [(planet_body - earth if planet_name == "Moon" else planet_body - sun).at(ti).position.au * 
                 (MOON_SCALE_FACTOR if planet_name == "Moon" else 1) for ti in times]
    return np.array(positions).T

def get_heliocentric_positions(selected_planets: List[str], t: 'skyfield.timelib.Time') -> Dict[str, np.ndarray]:
    """Calculate heliocentric positions for planets and geocentric for Moon."""
    positions = {}
    for name in selected_planets:
        if name not in planet_dict:
            logger.warning(f"Invalid planet name '{name}' skipped")
            continue
        planet_body = planet_dict[name]["body"]
        pos = (planet_body - earth if name == "Moon" else planet_body - sun).at(t).position.au
        if name == "Moon":
            pos *= MOON_SCALE_FACTOR
        positions[name] = pos
    return positions

def get_orbital_elements(planet_name: str, t: 'skyfield.timelib.Time') -> Dict[str, float]:
    """Calculate orbital elements for a planet."""
    if planet_name not in planet_dict:
        logger.warning(f"Invalid planet name '{planet_name}'")
        return {"semi_major_axis": 0.0, "eccentricity": 0.0}
    planet_body = planet_dict[planet_name]["body"]
    pos_vel = (planet_body - (earth if planet_name == "Moon" else sun)).at(t)
    elements = osculating_elements_of(pos_vel)
    return {"semi_major_axis": elements.semi_major_axis.au, "eccentricity": elements.eccentricity}

def _calculate_angle(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Calculate angle in degrees between two vectors."""
    cos_angle = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    return np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0)))

def calculate_events(t: 'skyfield.timelib.Time', angle_threshold: float = 1.0) -> List[Tuple[str, str]]:
    """Detect astronomical events at a given time."""
    events = []
    earth_pos = (planet_dict["Earth"]["body"] - sun).at(t).position.au
    sun_pos = sun.at(t).position.au
    
    for name in planet_dict:
        if name in ["Earth", "Moon"]:
            continue
        planet_pos = (planet_dict[name]["body"] - sun).at(t).position.au
        earth_to_planet = planet_pos - earth_pos
        earth_to_sun = sun_pos - earth_pos
        angle = _calculate_angle(earth_to_planet, earth_to_sun)
        
        if name in ["Mercury", "Venus"]:
            if angle < angle_threshold and np.dot(earth_to_planet, earth_to_sun) > 0 and np.linalg.norm(earth_to_planet) < np.linalg.norm(earth_to_sun):
                events.append((name, "Inferior Conjunction"))
            elif abs(angle - 180) < angle_threshold and np.linalg.norm(earth_to_sun) < np.linalg.norm(earth_to_planet):
                events.append((name, "Superior Conjunction"))
        elif abs(angle - 180) < angle_threshold:
            events.append((name, "Opposition"))
    
    return events

def find_next_events(selected_planets: List[str], t_start: 'skyfield.timelib.Time', t_end: 'skyfield.timelib.Time', angle_threshold: float = 1.0) -> List[Tuple[str, str, str]]:
    """Find upcoming astronomical events."""
    events = []
    for name in selected_planets:
        if name in ["Earth", "Moon"] or name not in planet_dict:
            continue
        
        planet_body = planet_dict[name]["body"]
        def elongation_at(t):
            e = earth.at(t)
            s = sun.at(t)
            p = planet_body.at(t)
            earth_to_sun = (s - e).position.au
            earth_to_planet = (p - e).position.au
            cos_angle = np.dot(earth_to_planet, earth_to_sun) / (np.linalg.norm(earth_to_planet) * np.linalg.norm(earth_to_sun))
            return np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0)))
        
        elongation_at.step_days = 0.5
        times, elongations = find_discrete(t_start, t_end, elongation_at)
        
        for t, elong in zip(times, elongations):
            if name in ["Mercury", "Venus"]:
                if abs(elong) < angle_threshold and (planet_body - sun).at(t).distance().au < (earth - sun).at(t).distance().au:
                    events.append((name, "Inferior Conjunction", t.utc_strftime('%Y-%m-%d %H:%M UTC')))
                elif abs(elong - 180) < angle_threshold and (planet_body - sun).at(t).distance().au > (earth - sun).at(t).distance().au:
                    events.append((name, "Superior Conjunction", t.utc_strftime('%Y-%m-%d %H:%M UTC')))
            elif abs(elong - 180) < angle_threshold:
                events.append((name, "Opposition", t.utc_strftime('%Y-%m-%d %H:%M UTC')))
    
    return sorted(events, key=lambda x: x[2])

if __name__ == "__main__":
    t = parse_date_time("2025-03-24", "12:00")
    positions = get_heliocentric_positions(["Earth", "Mars", "InvalidPlanet"], t)
    print("Heliocentric Positions:", positions)
    orbit = calculate_orbit("InvalidPlanet", t.tt, parse_date_time("2026-03-24", "12:00").tt)
    print("Orbit Shape (Invalid Planet):", orbit.shape)
    events = calculate_events(t)
    print("Current Events:", events)
    t_start = ts.now()
    t_end = ts.utc(t_start.utc_datetime().year + 1, t_start.utc_datetime().month, t_start.utc_datetime().day)
    upcoming_events = find_next_events(["Mercury", "Venus", "Mars", "Jupiter"], t_start, t_end)
    print("Upcoming Events:", upcoming_events)