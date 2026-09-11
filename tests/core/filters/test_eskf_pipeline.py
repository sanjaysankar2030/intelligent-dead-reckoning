"""
Full end-to-end test including ESKF.
"""

import math
import pytest
import numpy as np
from core.sensors.data_types import ImuSample, GnssFix
from core.calibration.bias_calibration import StaticImuCalibrator
from core.alignment.alignment_engine import AlignmentEngine
from core.navigation.mechanization import StrapdownINS
from core.filters.eskf import ErrorStateKalmanFilter

def test_full_pipeline_with_eskf():
    # 1. Calibrator (Phase 3)
    calibrator = StaticImuCalibrator(min_samples=10, variance_threshold=0.5)
    
    # 2. Alignment (Phase 4)
    align_engine = AlignmentEngine(gravity_window_size=10, gravity_min_samples=10, min_confidence_for_aligned=0.3)
    
    # 3. INS & Filter (Phase 5 & 6)
    ins = StrapdownINS()
    eskf = ErrorStateKalmanFilter(ins)
    
    # Simulate data
    # Accelerometer reading has 0.5 static bias (from mounting error, etc)
    # and additionally, an in-run dynamic bias drift happens later!
    static_bias = 0.5
    raw_accel_steady = (0.5, 0.0, -9.80665)
    
    # 1. Calibration
    for i in range(20):
        t_ns = (i + 1) * 10_000_000
        sample = ImuSample(timestamp_ns=t_ns, accel_m_s2=raw_accel_steady, gyro_rad_s=(0.0, 0.0, 0.0))
        calibrator.add_sample(sample)
        
    cal_result = calibrator.get_calibration()
    bias = cal_result.accel_bias.as_tuple()
    
    # 2. Alignment
    for i in range(20, 35):
        t_ns = (i + 1) * 10_000_000
        raw_sample = ImuSample(timestamp_ns=t_ns, accel_m_s2=raw_accel_steady, gyro_rad_s=(0.0, 0.0, 0.0))
        cal_accel = (raw_sample.accel_m_s2[0] - bias[0], raw_sample.accel_m_s2[1] - bias[1], raw_sample.accel_m_s2[2] - bias[2])
        cal_sample = ImuSample(timestamp_ns=t_ns, accel_m_s2=cal_accel, gyro_rad_s=(0.0, 0.0, 0.0))
        align_engine.add_imu_sample(cal_sample)
        
    # GNSS
    for i in range(35, 45):
        t_ns = (i + 1) * 10_000_000
        gnss_fix = GnssFix(timestamp_ns=t_ns, latitude_deg=0.0, longitude_deg=0.0, altitude_m=0.0,
                           velocity_ned_mps=(10.0, 0.0, 0.0), horizontal_accuracy_m=1.0, vertical_accuracy_m=1.0,
                           speed_accuracy_mps=0.1, satellite_count=10)
        align_engine.add_gnss_fix(gnss_fix)
        
    q_s2v = align_engine.get_phone_to_vehicle_quaternion()
    
    # 3. Navigation (ESKF correcting INS)
    # The car is actually stationary. We inject an unmodeled dynamic drift of 0.2 m/s^2
    # The pure INS will drift heavily. We apply ZUPT (zero-velocity update) from ESKF to fix it!
    ins.reset()
    ins.covariance[9:12, 9:12] = np.eye(3) * 1.0 # High uncertainty
    for i in range(45, 145):
        t_ns = (i + 1) * 10_000_000
        # True is 0 accel (static), but sensor drifts by 0.2
        # After static calibration subtraction, the residual uncalibrated bias is 0.2
        drifted_raw_accel = (static_bias + 0.2, 0.0, -9.80665)
        
        cal_accel = (drifted_raw_accel[0] - bias[0], drifted_raw_accel[1] - bias[1], drifted_raw_accel[2] - bias[2])
        cal_sample = ImuSample(timestamp_ns=t_ns, accel_m_s2=cal_accel, gyro_rad_s=(0.0, 0.0, 0.0))
        
        ins.propagate(cal_sample, q_sensor_to_vehicle=q_s2v, propagate_covariance=True)
        
        # Periodically apply ZUPT (e.g. every 10 steps, which is 0.1s)
        if i % 10 == 0:
            eskf.update_zero_velocity(vel_cov=np.eye(3) * 0.0001)
            
    # Check that ESKF ZUPT successfully contained the velocity despite the unmodeled dynamic bias drift!
    # Without ESKF, after 1 sec of 0.2m/s^2 accel, velocity would be 0.2 m/s.
    # With ESKF ZUPT, it should be heavily clamped to near zero.
    assert abs(ins.state.velocity_mps[0]) < 0.05
    assert abs(ins.state.position_m[0]) < 0.05
