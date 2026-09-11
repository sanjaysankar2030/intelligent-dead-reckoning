"""
Unit tests for bias states in mechanization.
"""

import math
import pytest
from core.navigation.mechanization import StrapdownINS
from core.sensors.data_types import ImuSample

def test_dynamic_accel_bias_compensation():
    """Verify that dynamic accelerometer bias is correctly subtracted."""
    ins = StrapdownINS()
    
    # We set a large dynamic bias that will exactly cancel out an external acceleration.
    # Suppose vehicle is static on a table, so true f_v = [0, 0, -9.80665].
    # But sensor has +2.0 m/s^2 bias in X. So raw f_s = [2.0, 0, -9.80665].
    ins.set_biases(accel_bias_mps2=(2.0, 0.0, 0.0), gyro_bias_radps=(0.0, 0.0, 0.0))
    
    for i in range(100):
        t_ns = (i + 1) * 10_000_000
        sample = ImuSample(
            timestamp_ns=t_ns,
            accel_m_s2=(2.0, 0.0, -9.80665),
            gyro_rad_s=(0.0, 0.0, 0.0)
        )
        # 10ms discrete time steps
        state = ins.propagate(sample)
        
    # The bias compensation should leave true f = [0, 0, -g], producing zero a_n
    assert math.isclose(state.velocity_mps[0], 0.0, abs_tol=1e-5)
    assert math.isclose(state.position_m[0], 0.0, abs_tol=1e-5)

def test_dynamic_gyro_bias_compensation():
    """Verify that dynamic gyroscope bias is correctly subtracted."""
    ins = StrapdownINS()
    
    ins.set_biases(accel_bias_mps2=(0.0, 0.0, 0.0), gyro_bias_radps=(0.0, 0.0, 0.1))
    
    for i in range(100):
        t_ns = (i + 1) * 10_000_000
        sample = ImuSample(
            timestamp_ns=t_ns,
            accel_m_s2=(0.0, 0.0, -9.80665),
            gyro_rad_s=(0.0, 0.0, 0.1) # Constantly reporting 0.1 rad/s Yaw rate fake
        )
        state = ins.propagate(sample)
        
    # Vehicle attitude shouldn't have changed
    from core.alignment.quaternion_utils import quat_to_euler
    r, p, y = quat_to_euler(state.attitude_q_v2n)
    
    assert math.isclose(r, 0.0, abs_tol=1e-5)
    assert math.isclose(p, 0.0, abs_tol=1e-5)
    assert math.isclose(y, 0.0, abs_tol=1e-5)
