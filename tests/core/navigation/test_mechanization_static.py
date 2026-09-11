"""
Unit tests for stationary conditions in strapdown mechanization.
"""

import math
import numpy as np
import pytest

from core.navigation.mechanization import StrapdownINS
from core.navigation.state import NavState
from core.sensors.data_types import ImuSample
from core.alignment.quaternion_utils import quat_from_euler, quat_rotate_vector

def test_static_level_phone():
    """Level phone resting on table should have zero acceleration and stay stationary."""
    ins = StrapdownINS()
    
    # In Android sensor frame, phone flat screen-up:
    # Accelerometer measures +9.80665 m/s^2 along Z (out of screen).
    # In vehicle frame (FRD), Z is DOWN.
    # So if phone is flat screen-up, Phone Z points UP (-Z in vehicle frame).
    # Let's say phone is aligned with vehicle: Vehicle X=Forward, Y=Right, Z=Down.
    # Then reaction to gravity in Vehicle frame is -9.80665 in Z (upwards).
    
    # Let sensor frame be aligned with vehicle frame for this test:
    # Specific force measured is UP (towards -Z_v): (0, 0, -9.80665)
    
    for i in range(100):
        t_ns = (i + 1) * 10_000_000  # 100 Hz (10 ms steps)
        sample = ImuSample(
            timestamp_ns=t_ns,
            accel_m_s2=(0.0, 0.0, -9.80665),
            gyro_rad_s=(0.0, 0.0, 0.0)
        )
        state = ins.propagate(sample, q_sensor_to_vehicle=(1.0, 0.0, 0.0, 0.0))
        
    assert math.isclose(state.position_m[0], 0.0, abs_tol=1e-5)
    assert math.isclose(state.position_m[1], 0.0, abs_tol=1e-5)
    assert math.isclose(state.position_m[2], 0.0, abs_tol=1e-5)
    assert math.isclose(state.velocity_mps[0], 0.0, abs_tol=1e-5)
    assert math.isclose(state.velocity_mps[1], 0.0, abs_tol=1e-5)
    assert math.isclose(state.velocity_mps[2], 0.0, abs_tol=1e-5)

def test_static_arbitrary_orientation():
    """Phone placed in arbitrary 3D orientation should stay stationary if properly aligned."""
    ins = StrapdownINS()
    
    # Let vehicle be level: reaction to gravity in vehicle frame is f_v = [0, 0, -9.80665]
    f_v = (0.0, 0.0, -9.80665)
    
    # Suppose phone is mounted with roll=30 deg, pitch=45 deg, yaw=60 deg relative to vehicle
    q_s2v = quat_from_euler(math.radians(30), math.radians(45), math.radians(60))
    
    # Then in sensor frame, specific force is f_s = R_v2s * f_v = q_s2v^* * f_v * q_s2v
    from core.alignment.quaternion_utils import quat_conjugate
    q_v2s = quat_conjugate(q_s2v)
    f_s = quat_rotate_vector(q_v2s, f_v)
    
    for i in range(100):
        t_ns = (i + 1) * 10_000_000
        sample = ImuSample(
            timestamp_ns=t_ns,
            accel_m_s2=f_s,
            gyro_rad_s=(0.0, 0.0, 0.0)
        )
        state = ins.propagate(sample, q_sensor_to_vehicle=q_s2v)
        
    assert math.isclose(state.position_m[0], 0.0, abs_tol=1e-5)
    assert math.isclose(state.position_m[1], 0.0, abs_tol=1e-5)
    assert math.isclose(state.position_m[2], 0.0, abs_tol=1e-5)
    assert math.isclose(state.velocity_mps[0], 0.0, abs_tol=1e-5)
    assert math.isclose(state.velocity_mps[1], 0.0, abs_tol=1e-5)
    assert math.isclose(state.velocity_mps[2], 0.0, abs_tol=1e-5)
