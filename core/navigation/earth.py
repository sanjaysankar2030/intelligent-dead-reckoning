import math
from typing import Tuple
import numpy as np

WGS84_A = 6378137.0
WGS84_F = 1.0 / 298.257223563
WGS84_E2 = 2 * WGS84_F - WGS84_F**2

def lla_to_ned(lat: float, lon: float, alt: float, lat0: float, lon0: float, alt0: float) -> Tuple[float, float, float]:
    """
    Convert geodetic (Latitude, Longitude, Altitude) to local NED coordinates.
    lat, lon in degrees. alt in meters.
    """
    lat_r, lon_r = math.radians(lat), math.radians(lon)
    lat0_r, lon0_r = math.radians(lat0), math.radians(lon0)

    # Prime vertical radius of curvature
    sin_lat0 = math.sin(lat0_r)
    rn = WGS84_A / math.sqrt(1.0 - WGS84_E2 * sin_lat0**2)
    # Meridional radius of curvature
    rm = rn * (1.0 - WGS84_E2) / (1.0 - WGS84_E2 * sin_lat0**2)

    d_lat = lat_r - lat0_r
    d_lon = lon_r - lon0_r

    north = (rm + alt0) * d_lat
    east = (rn + alt0) * math.cos(lat0_r) * d_lon
    down = -(alt - alt0)
    
    return north, east, down

def ned_to_lla(north: float, east: float, down: float, lat0: float, lon0: float, alt0: float) -> Tuple[float, float, float]:
    """Convert local NED coordinates back to Geodetic LLA."""
    lat0_r, lon0_r = math.radians(lat0), math.radians(lon0)
    
    sin_lat0 = math.sin(lat0_r)
    rn = WGS84_A / math.sqrt(1.0 - WGS84_E2 * sin_lat0**2)
    rm = rn * (1.0 - WGS84_E2) / (1.0 - WGS84_E2 * sin_lat0**2)
    
    d_lat = north / (rm + alt0)
    d_lon = east / ((rn + alt0) * math.cos(lat0_r))
    
    lat = math.degrees(lat0_r + d_lat)
    lon = math.degrees(lon0_r + d_lon)
    alt = alt0 - down
    
    return lat, lon, alt
