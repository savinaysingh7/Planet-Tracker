from astropy.time import Time
from sunpy.coordinates import get_body_heliographic_stonyhurst
import numpy as np
import astropy.units as u

def get_heliographic_position(planet, time=None):
    """Calculate heliographic coordinates and distance for a planet at a given time."""
    if time is None:
        time = Time.now()
    try:
        coord = get_body_heliographic_stonyhurst(planet, time=time)
        return coord.lon.deg, coord.lat.deg, coord.radius.au
    except Exception as e:
        print(f"Failed to calculate position for {planet}: {e}")
        return 0, 0, 0

def get_positions_over_time(planet, start_date, days=30, steps=30):
    """Generate positions for a planet over a time period, including dates."""
    start = Time(start_date)
    time_offsets = np.linspace(0, days, steps)  # Days as floats
    times = start + (time_offsets * 86400) * u.s  # Explicitly use seconds unit
    positions = []
    for t in times:
        lon, lat, dist = get_heliographic_position(planet, t)
        positions.append((lon, lat, dist, t.iso.split()[0]))  # Add YYYY-MM-DD
    return positions