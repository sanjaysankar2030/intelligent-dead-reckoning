"""
Unit tests for the complete phone-to-vehicle alignment engine.
"""

import math

import numpy as np
import pytest

from core.alignment.alignment_engine import AlignmentEngine
from core.alignment.frames import AlignmentState
from core.alignment.quaternion_utils import quat_rotate_vector, quat_to_euler
from core.sensors.data_types import GnssFix, ImuSample


def create_imu_sample(accel: tuple[float, float, float]) -> ImuSample:
    return ImuSample(
        timestamp_ns=1000000000,
        accel_m_s2=accel,
        gyro_rad_s=(0.0, 0.0, 0.0),
    )


def create_gnss_fix(v_north: float, v_east: float) -> GnssFix:
    return GnssFix(
        timestamp_ns=1000000000,
        latitude_deg=0.0,
        longitude_deg=0.0,
        altitude_m=0.0,
        velocity_ned_mps=(v_north, v_east, 0.0),
        horizontal_accuracy_m=1.0,
        vertical_accuracy_m=2.0,
        speed_accuracy_mps=0.1,
        satellite_count=10,
    )


def test_engine_initialization():
    engine = AlignmentEngine()
    assert not engine.is_aligned
    assert not engine.is_heading_available

    status = engine.get_alignment_status()
    assert status.state == AlignmentState.UNINITIALIZED
    assert status.confidence == 0.0


def test_gravity_only_state():
    engine = AlignmentEngine(gravity_window_size=5, gravity_min_samples=5)

    # Add static IMU samples (perfectly level, +g in Z)
    for _ in range(5):
        used, status = engine.add_imu_sample(create_imu_sample((0.0, 0.0, 9.80665)))
        assert used

    assert engine.is_aligned
    assert not engine.is_heading_available

    status = engine.get_alignment_status()
    assert status.state == AlignmentState.GRAVITY_ONLY
    assert math.isclose(status.roll_rad, 0.0, abs_tol=1e-5)
    assert math.isclose(status.pitch_rad, 0.0, abs_tol=1e-5)
    assert math.isclose(status.yaw_rad, 0.0, abs_tol=1e-5)


def test_fully_aligned_state():
    engine = AlignmentEngine(gravity_window_size=5, gravity_min_samples=5, min_confidence_for_aligned=0.3)

    # 1. Establish gravity alignment (flat)
    for _ in range(5):
        engine.add_imu_sample(create_imu_sample((0.0, 0.0, 9.80665)))

    # 2. Establish heading alignment (moving East)
    for _ in range(5):
        used, status = engine.add_gnss_fix(create_gnss_fix(0.0, 10.0))

    assert engine.is_aligned
    assert engine.is_heading_available

    status = engine.get_alignment_status()
    assert status.state == AlignmentState.FULLY_ALIGNED
    assert math.isclose(status.yaw_rad, math.pi/2, abs_tol=1e-5)

    # Test the output quaternion
    q = engine.get_phone_to_vehicle_quaternion()
    r, p, y = quat_to_euler(q)
    assert math.isclose(r, 0.0, abs_tol=1e-5)
    assert math.isclose(p, 0.0, abs_tol=1e-5)
    assert math.isclose(y, math.pi/2, abs_tol=1e-5)

    # Transform a vector FROM phone TO vehicle
    # Phone Y points East (forward in this case, wait...)
    # Actually, yaw of pi/2 means R_phone^vehicle rotates by pi/2 around Z.
    v_phone = (1.0, 0.0, 0.0)
    v_veh = quat_rotate_vector(q, v_phone)
    # Rotating (1,0,0) by 90 deg around Z gives (0,1,0)
    assert math.isclose(v_veh[0], 0.0, abs_tol=1e-5)
    assert math.isclose(v_veh[1], 1.0, abs_tol=1e-5)


def test_reorientation_detection():
    engine = AlignmentEngine(
        gravity_window_size=5,
        gravity_min_samples=5,
        min_confidence_for_aligned=0.2,
        reentry_deg_threshold=15.0
    )

    # 1. Establish initial alignment (flat, moving North)
    for _ in range(5):
        engine.add_imu_sample(create_imu_sample((0.0, 0.0, 9.80665)))
    for _ in range(5):
        engine.add_gnss_fix(create_gnss_fix(10.0, 0.0))

    assert engine.get_alignment_status().state == AlignmentState.FULLY_ALIGNED

    # 2. Suddenly phone is flipped upside down and moving East
    # Gravity is now [0, 0, -9.8] in phone frame
    for _ in range(5):
        engine.add_imu_sample(create_imu_sample((0.0, 0.0, -9.80665)))
    for _ in range(5):
        used, status = engine.add_gnss_fix(create_gnss_fix(0.0, 10.0))

    # The engine should detect this drastic change as LOST
    assert status.state == AlignmentState.LOST
