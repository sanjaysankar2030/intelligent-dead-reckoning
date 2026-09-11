"""
Unit tests for gravity-based tilt alignment.
"""

import math

import numpy as np
import pytest

from core.alignment.gravity_alignment import GravityAligner
from core.alignment.quaternion_utils import quat_rotate_vector
from core.sensors.data_types import ImuSample


def create_static_imu_sample(accel: tuple[float, float, float]) -> ImuSample:
    return ImuSample(
        timestamp_ns=1000000000,
        accel_m_s2=accel,
        gyro_rad_s=(0.0, 0.0, 0.0),
    )


def test_gravity_aligner_initialization():
    aligner = GravityAligner(window_size=10, min_samples=5)
    assert not aligner.is_valid
    assert aligner.confidence == 0.0
    assert aligner.roll == 0.0
    assert aligner.pitch == 0.0


def test_level_orientation():
    aligner = GravityAligner(window_size=5, min_samples=5)
    # Phone laying flat, screen up: Z points out of screen, measures +g
    for _ in range(5):
        sample = create_static_imu_sample((0.0, 0.0, 9.80665))
        aligner.add_sample(sample)

    assert aligner.is_valid
    assert math.isclose(aligner.roll, 0.0, abs_tol=1e-5)
    assert math.isclose(aligner.pitch, 0.0, abs_tol=1e-5)
    assert aligner.confidence > 0.8


def test_pitched_orientation():
    aligner = GravityAligner(window_size=5, min_samples=5)
    # Phone pitched up 30 degrees (tilt around Y axis)
    # Pitch is positive -> front of phone points up
    # In vehicle frame, X (forward) is up. Gravity is [0, 0, g]
    # Phone frame measures: X = -g*sin(30), Z = g*cos(30)
    pitch_true = math.radians(30)
    g = 9.80665
    ax = -g * math.sin(pitch_true)
    az = g * math.cos(pitch_true)

    for _ in range(5):
        sample = create_static_imu_sample((ax, 0.0, az))
        aligner.add_sample(sample)

    assert aligner.is_valid
    assert math.isclose(aligner.roll, 0.0, abs_tol=1e-5)
    assert math.isclose(aligner.pitch, pitch_true, abs_tol=1e-5)


def test_rolled_orientation():
    aligner = GravityAligner(window_size=5, min_samples=5)
    # Phone rolled right 45 degrees (tilt around X axis)
    roll_true = math.radians(45)
    g = 9.80665
    ay = g * math.sin(roll_true)
    az = g * math.cos(roll_true)

    for _ in range(5):
        sample = create_static_imu_sample((0.0, ay, az))
        aligner.add_sample(sample)

    assert aligner.is_valid
    assert math.isclose(aligner.roll, roll_true, abs_tol=1e-5)
    assert math.isclose(aligner.pitch, 0.0, abs_tol=1e-5)


def test_complex_orientation():
    aligner = GravityAligner(window_size=5, min_samples=5)

    # We want a phone with roll=30, pitch=45, yaw=60
    # The vehicle is level, so its gravity is [0, 0, g].
    # Measured acceleration is the anti-gravity vector [0, 0, -g] transformed to phone frame,
    # then negated (since it measures reaction). Actually, accelerometer measures
    # R_vehicle^phone @ [0, 0, g] directly.

    roll = math.radians(30)
    pitch = math.radians(45)
    # Yaw doesn't affect gravity measurement in phone frame!

    # Create rotation matrix from vehicle to phone
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)

    # R_vehicle^phone is Rx(roll) * Ry(pitch) * Rz(yaw)
    # We only care about how it maps [0, 0, 1] (vehicle Z/down).
    # Rz(yaw) leaves [0, 0, 1] unchanged.
    # So we apply Ry(pitch) then Rx(roll) to [0, 0, 1]
    g_vec = np.array([0, 0, 9.80665])

    Ry = np.array([
        [cp, 0, -sp],
        [0, 1, 0],
        [sp, 0, cp]
    ])
    Rx = np.array([
        [1, 0, 0],
        [0, cr, sr],
        [0, -sr, cr]
    ])

    R_v_to_p = Rx @ Ry
    accel = R_v_to_p @ g_vec

    for _ in range(5):
        sample = create_static_imu_sample(tuple(accel))
        aligner.add_sample(sample)

    assert aligner.is_valid
    assert math.isclose(aligner.roll, roll, abs_tol=1e-5)
    assert math.isclose(aligner.pitch, pitch, abs_tol=1e-5)


def test_rejection_of_dynamic_samples():
    aligner = GravityAligner(window_size=5, min_samples=5, max_accel_deviation=1.0)
    # Add varying/dynamic samples that deviate from gravity
    for _ in range(3):
        sample = create_static_imu_sample((0.0, 0.0, 9.80665))
        assert aligner.add_sample(sample) is True

    # Add bad sample
    dynamic_sample = create_static_imu_sample((0.0, 0.0, 15.0))
    assert aligner.add_sample(dynamic_sample) is False

    # Still invalid because only 3 good samples
    assert not aligner.is_valid

    # Add rest of good samples
    for _ in range(2):
        sample = create_static_imu_sample((0.0, 0.0, 9.80665))
        assert aligner.add_sample(sample) is True

    # Now valid
    assert aligner.is_valid


def test_tilt_quaternion():
    aligner = GravityAligner(min_samples=1)
    aligner.add_sample(create_static_imu_sample((0.0, 0.0, 9.80665)))

    # No yaw -> identity (since roll=0, pitch=0)
    q = aligner.get_tilt_quaternion(yaw=0.0)
    assert q == (1.0, 0.0, 0.0, 0.0)

    # With yaw
    yaw = math.radians(90)
    q_yaw = aligner.get_tilt_quaternion(yaw=yaw)
    v = quat_rotate_vector(q_yaw, (1.0, 0.0, 0.0))
    # Rotating X forward by 90 yaw (around Z down) results in Y right
    assert math.isclose(v[0], 0.0, abs_tol=1e-5)
    assert math.isclose(v[1], 1.0, abs_tol=1e-5)
    assert math.isclose(v[2], 0.0, abs_tol=1e-5)
