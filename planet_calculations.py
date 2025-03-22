from astropy.time import Time
from sunpy.coordinates import get_body_heliographic_stonyhurst

def get_heliographic_position(planet, time=None):
    if time is None:
        time = Time.now()
    try:
        coord = get_body_heliographic_stonyhurst(planet, time=time)
        return coord.lon.deg, coord.lat.deg, coord.radius.au
    except Exception as e:
        print(f"Failed to calculate position for {planet}: {e}")
        return 0, 0, 0