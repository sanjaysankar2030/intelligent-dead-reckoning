"""
Unit tests for heading (yaw) estimator.
"""

import math

import numpy as np
import pytest

from core.alignment.heading_estimator import HeadingEstimator
from core.sensors.data_types import GnssFix, ImuSample, MagSample


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


def test_heading_estimator_init():
    estimator = HeadingEstimator()
    assert not estimator.is_valid
    assert estimator.confidence == 0.0
    assert estimator.yaw_offset == 0.0


def test_gnss_velocity_heading():
    estimator = HeadingEstimator(gnss_min_speed=2.0)

    # Low speed - rejected
    low_speed = create_gnss_fix(1.0, 1.0)
    assert not estimator.add_gnss_fix(low_speed)

    # Driving North (heading 0)
    north_fix = create_gnss_fix(10.0, 0.0)
    assert estimator.add_gnss_fix(north_fix)
    estimator.update()
    assert estimator.is_valid
    assert math.isclose(estimator.yaw_offset, 0.0, abs_tol=1e-5)

    estimator.reset()

    # Driving East (heading 90 deg / pi/2)
    east_fix = create_gnss_fix(0.0, 10.0)
    estimator.add_gnss_fix(east_fix)
    estimator.update()
    assert estimator.is_valid
    assert math.isclose(estimator.yaw_offset, math.pi/2, abs_tol=1e-5)

    estimator.reset()

    # Driving South-West (-135 deg / -3*pi/4)
    sw_fix = create_gnss_fix(-10.0, -10.0)
    estimator.add_gnss_fix(sw_fix)
    estimator.update()
    assert estimator.is_valid
    assert math.isclose(estimator.yaw_offset, -3*math.pi/4, abs_tol=1e-5)


def test_mag_aiding():
    estimator = HeadingEstimator()

    # Sample with magnetic field pointing mostly East
    # Assuming standard phone orientation
    mag_sample = MagSample(
        timestamp_ns=1000000000,
        magnetic_field_ut=(0.0, 40.0, -20.0)
    )

    assert estimator.add_mag_sample(mag_sample)
    estimator.update()

    assert estimator.is_valid
    assert math.isclose(estimator.yaw_offset, math.pi/2, abs_tol=1e-5)
    # Mag confidence should be low
    assert estimator.confidence < 0.2


def test_confidence_growth():
    estimator = HeadingEstimator()

    # Add single reading
    estimator.add_gnss_fix(create_gnss_fix(10.0, 0.0))
    estimator.update()
    conf1 = estimator.confidence

    # Add 9 more identical readings
    for _ in range(9):
        estimator.add_gnss_fix(create_gnss_fix(10.0, 0.0))
        estimator.update()

    conf10 = estimator.confidence

    assert conf10 > conf1
    assert conf10 > 0.8
    assert math.isclose(estimator.yaw_offset, 0.0, abs_tol=1e-5)


def test_heading_fusion():
    estimator = HeadingEstimator(mag_weight=0.1)

    # GNSS says North (0 deg)
    for _ in range(5):
        estimator.add_gnss_fix(create_gnss_fix(10.0, 0.0))

    # Mag says East (90 deg)
    for _ in range(5):
        estimator.add_mag_sample(MagSample(
            timestamp_ns=1000000000,
            magnetic_field_ut=(0.0, 40.0, -20.0)
        ))

    estimator.update()

    # GNSS should dominate due to higher weight
    assert estimator.is_valid
    assert 0.0 <= estimator.yaw_offset < math.radians(10)
