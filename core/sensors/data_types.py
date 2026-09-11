"""
Immutable sensor data structures.
All timestamps are in nanoseconds since epoch (UTC) for high precision.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import NamedTuple


class SensorType(Enum):
    """Enumeration of sensor types."""
    ACCELEROMETER = auto()
    GYROSCOPE = auto()
    MAGNETOMETER = auto()
    GNSS = auto()
    BAROMETER = auto()


@dataclass(frozen=True)
class ImuSample:
    """IMU sample (accelerometer and gyroscope).

    Attributes:
        timestamp_ns: Timestamp in nanoseconds.
        accel_m_s2: Acceleration in m/s^2 as (x, y, z) in sensor frame.
        gyro_rad_s: Angular velocity in rad/s as (x, y, z) in sensor frame.
    """
    timestamp_ns: int
    accel_m_s2: tuple[float, float, float]
    gyro_rad_s: tuple[float, float, float]


@dataclass(frozen=True)
class GnssFix:
    """GNSS fix.

    Attributes:
        timestamp_ns: Timestamp in nanoseconds.
        latitude_deg: Latitude in degrees.
        longitude_deg: Longitude in degrees.
        altitude_m: Altitude above WGS-84 ellipsoid in meters.
        velocity_ned_mps: Velocity in NED frame as (v_north, v_east, v_down) in m/s.
        horizontal_accuracy_m: Estimated horizontal error radius (1-sigma) in meters.
        vertical_accuracy_m: Estimated vertical error (1-sigma) in meters.
        speed_accuracy_mps: Estimated speed error (1-sigma) in m/s.
        satellite_count: Number of satellites used in fix.
    """
    timestamp_ns: int
    latitude_deg: float
    longitude_deg: float
    altitude_m: float
    velocity_ned_mps: tuple[float, float, float]
    horizontal_accuracy_m: float
    vertical_accuracy_m: float
    speed_accuracy_mps: float
    satellite_count: int


@dataclass(frozen=True)
class MagSample:
    """Magnetometer sample.

    Attributes:
        timestamp_ns: Timestamp in nanoseconds.
        magnetic_field_ut: Magnetic field vector in microtesla as (x, y, z) in sensor frame.
    """
    timestamp_ns: int
    magnetic_field_ut: tuple[float, float, float]


@dataclass(frozen=True)
class BaroSample:
    """Barometer sample.

    Attributes:
        timestamp_ns: Timestamp in nanoseconds.
        pressure_pa: Atmospheric pressure in Pascals.
    """
    timestamp_ns: int
    pressure_pa: float


# Union type for all sensor samples (for use in heterogeneous lists)
SensorSample = ImuSample | GnssFix | MagSample | BaroSample


class TimestampSyncError(Exception):
    """Raised when timestamp synchronization fails."""
    pass


def lin_interp(t: float, t0: float, t1: float, v0: float, v1: float) -> float:
    """Linear interpolation.

    Args:
        t: Target time.
        t0, t1: Known times (t0 <= t <= t1).
        v0, v1: Known values.

    Returns:
        Interpolated value at time t.
    """
    if t1 == t0:
        return v0
    return v0 + (t - t0) * (v1 - v0) / (t1 - t0)


def slerp(q0: tuple[float, float, float, float],
          q1: tuple[float, float, float, float],
          t: float) -> tuple[float, float, float, float]:
    """Spherical linear interpolation for quaternions.

    Args:
        q0, q1: Quaternions as (w, x, y, z).
        t: Interpolation parameter in [0, 1].

    Returns:
        Interpolated quaternion.
    """
    import math

    # Dot product
    dot = q0[0]*q1[0] + q0[1]*q1[1] + q0[2]*q1[2] + q0[3]*q1[3]

    # If dot is negative, we can shorten the path by inverting one quaternion
    if dot < 0.0:
        q1 = (-q1[0], -q1[1], -q1[2], -q1[3])
        dot = -dot

    # If quaternions are very close, use linear interpolation
    if dot > 0.9995:
        result = (
            q0[0] + t * (q1[0] - q0[0]),
            q0[1] + t * (q1[1] - q0[1]),
            q0[2] + t * (q1[2] - q0[2]),
            q0[3] + t * (q1[3] - q0[3]),
        )
        # Normalize
        norm = math.sqrt(sum(x*x for x in result))
        return tuple(x / norm for x in result)

    # Spherical interpolation
    theta_0 = math.acos(dot)
    sin_theta_0 = math.sin(theta_0)

    theta = theta_0 * t
    sin_theta = math.sin(theta)

    s0 = math.cos(theta) - dot * sin_theta / sin_theta_0
    s1 = sin_theta / sin_theta_0

    return (
        s0 * q0[0] + s1 * q1[0],
        s0 * q0[1] + s1 * q1[1],
        s0 * q0[2] + s1 * q1[2],
        s0 * q0[3] + s1 * q1[3],
    )


# Type alias for clarity
Timestamp = int  # nanoseconds