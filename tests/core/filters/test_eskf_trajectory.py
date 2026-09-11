import math
import numpy as np
import pytest

from core.navigation.mechanization import StrapdownINS
from core.filters.eskf import ErrorStateKalmanFilter
from core.sensors.data_types import ImuSample

def simulate_trajectory():
    """Run synthetic trajectory and compare Pure INS vs ESKF-corrected INS."""
    
    # True Bias in Sensor
    true_bias = 0.5 # m/s^2 intentional bias error in X
    
    # 10 second run at 100 Hz
    dt = 0.01
    
    pure_ins = StrapdownINS()
    # High initial uncertainty in bias to allow rapid convergence
    eskf_ins = StrapdownINS()
    eskf_ins.covariance[9:12, 9:12] = np.eye(3) * 1.0 # high initial accel bias covariance
    
    eskf = ErrorStateKalmanFilter(eskf_ins)
    
    for i in range(1000):
        t_sec = (i + 1) * dt
        t_ns = int(t_sec * 1e9)
        
        # True dynamics: accel of 1.0 for first 5 sec, -1.0 for next 5 sec
        if t_sec <= 5.0:
            true_accel_x = 1.0
        else:
            true_accel_x = -1.0
            
        # Raw Sensor reads true kinematics plus bias 
        # (simulating uncalibrated offset or dynamic drift)
        meas_accel_x = true_accel_x + true_bias
        
        sample = ImuSample(
            timestamp_ns=t_ns,
            accel_m_s2=(meas_accel_x, 0.0, -9.80665),
            gyro_rad_s=(0.0, 0.0, 0.0)
        )
        
        # Propagate nominal uncorrected INS
        pure_ins.propagate(sample, propagate_covariance=False)
        
        # Propagate ESKF-wrapped INS
        eskf_ins.propagate(sample, propagate_covariance=True)
        
        # Every 1 second, give a GNSS fix
        if (i + 1) % 100 == 0:
            # Calculate what the TRUE position and velocity are at this exact second
            # Integration of a piecewise function:
            if t_sec <= 5.0:
                true_pos_x = 0.5 * 1.0 * (t_sec ** 2)
                true_vel_x = 1.0 * t_sec
            else:
                t_sub = t_sec - 5.0
                true_vel_x = 5.0 - 1.0 * t_sub
                true_pos_x = 12.5 + 5.0 * t_sub - 0.5 * 1.0 * (t_sub ** 2)
            
            # Measurement is truth with slight noise 
            # Simulate GNSS covariance of 1.0 for pos, 0.1 for vel
            eskf.update_position((true_pos_x, 0.0, 0.0), np.eye(3) * 1.0)
            eskf.update_velocity((true_vel_x, 0.0, 0.0), np.eye(3) * 0.1)
    
    return pure_ins, eskf_ins

def test_eskf_trajectory_correction():
    pure_ins, eskf_ins = simulate_trajectory()
    
    # Truth at 10.0s is Pos=25, Vel=0
    # Pure INS without correction thinks Pos=25(from actual) + 0.5(50) = 50 + ?
    # Let's see: 
    # Measured accel = 1.5 then -0.5
    # Vel at 5s = 1.5 * 5 = 7.5
    # Vel at 10s = 7.5 - 0.5 * 5 = 5.0. Truth varies, pure INS diverges.
    pure_vel_error = abs(pure_ins.state.velocity_mps[0] - 0.0)
    pure_pos_error = abs(pure_ins.state.position_m[0] - 25.0)
    
    eskf_vel_error = abs(eskf_ins.state.velocity_mps[0] - 0.0)
    eskf_pos_error = abs(eskf_ins.state.position_m[0] - 25.0)
    
    # ESKF should dramatically outperform pure INS
    assert eskf_vel_error < pure_vel_error
    assert eskf_pos_error < pure_pos_error
    
    # Error should be bounded significantly
    assert eskf_vel_error < 0.5 # Should be very small
    assert eskf_pos_error < 2.0 # Filter pulls it close to truth
    
    # Look at estimated bias!
    # The true bias was +0.5. The ESKF state stores `accel_bias_mps2` which we subtract!
    # So the filter should estimate accel_bias as +0.5!
    est_bias = eskf_ins.state.accel_bias_mps2[0]
    
    # We started at 0.0, after 10 updates it should begin converging towards 0.5
    assert est_bias > 0.2
    
    # Covariance for bias should have plummeted from 1.0
    assert eskf_ins.covariance[9, 9] < 0.5
