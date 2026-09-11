"""
Unit tests for explicit kinematic cases.
"""

import math
import pytest

from core.navigation.mechanization import StrapdownINS
from core.sensors.data_types import ImuSample
from core.alignment.quaternion_utils import quat_from_euler, quat_to_euler

def test_constant_acceleration():
    """Verify standard 1D kinematic equations for constant acceleration."""
    ins = StrapdownINS()
    
    # 2.0 m/s^2 forward in Vehicle X axis.
    # Reaction force: Accelerometer measures f = a - g.
    # a_n = [2.0, 0, 0]. In Vehicle (level): a_v = [2.0, 0, 0].
    # Gravity in Vehicle (level): g_v = [0, 0, 9.80665].
    # So f_v = a_v - g_v = [2.0, 0.0, -9.80665]
    
    f_v = (2.0, 0.0, -9.80665)
    
    dt = 0.01  # 10ms
    n_steps = 500  # 5 seconds
    
    for i in range(n_steps):
        t_ns = (i + 1) * 10_000_000
        sample = ImuSample(
            timestamp_ns=t_ns,
            accel_m_s2=f_v,
            gyro_rad_s=(0.0, 0.0, 0.0)
        )
        # Using Identity for q_s2v means sensor == vehicle
        state = ins.propagate(sample)
        
    # Expected: v = at = 2.0 * 5.0 = 10.0 m/s
    # Expected: p = 0.5 * a * t^2 = 0.5 * 2.0 * 25.0 = 25.0 m
    # Note: Using discrete trapezoidal integration with constant accel gives EXACT match
    # because acceleration is constant.
    assert math.isclose(state.velocity_mps[0], 10.0, abs_tol=1e-3)
    assert math.isclose(state.position_m[0], 25.0, abs_tol=1e-3)
    assert math.isclose(state.position_m[1], 0.0, abs_tol=1e-5)
    assert math.isclose(state.position_m[2], 0.0, abs_tol=1e-5)

def test_constant_turn():
    """Verify attitude propagates correctly during a constant yaw rate turn."""
    ins = StrapdownINS()
    
    dt = 0.01
    # Turning right at 90 deg/sec
    turn_rate = math.pi / 2  
    n_steps = 100  # 1 second -> 90 degrees total
    
    for i in range(n_steps):
        t_ns = (i + 1) * int(dt * 1e9)
        sample = ImuSample(
            timestamp_ns=t_ns,
            accel_m_s2=(0.0, 0.0, -9.80665),
            gyro_rad_s=(0.0, 0.0, turn_rate)
        )
        state = ins.propagate(sample)
        
    roll, pitch, yaw = quat_to_euler(state.attitude_q_v2n)
    
    assert math.isclose(roll, 0.0, abs_tol=1e-5)
    assert math.isclose(pitch, 0.0, abs_tol=1e-5)
    assert math.isclose(yaw, math.pi / 2, abs_tol=1e-5)
