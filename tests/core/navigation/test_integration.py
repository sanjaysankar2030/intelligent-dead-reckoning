"""
Integration tests for the complete navigation pipeline (Phases 3-5).
"""

import math
import pytest
from core.sensors.data_types import ImuSample, GnssFix
from core.calibration.bias_calibration import StaticImuCalibrator
from core.alignment.alignment_engine import AlignmentEngine
from core.alignment.frames import AlignmentState
from core.navigation.mechanization import StrapdownINS

def test_full_pipeline_stationary():
    """Verify raw sensor -> calibration -> alignment -> INS stationary condition."""
    calibrator = StaticImuCalibrator(min_samples=10, variance_threshold=0.5)
    align_engine = AlignmentEngine(gravity_window_size=10, gravity_min_samples=10, min_confidence_for_aligned=0.3)
    ins = StrapdownINS()
    
    # 1. Calibration Phase (Simulate a noisy static period with a static bias)
    # True gravity is -9.80665 (flat). Sensor has static X bias of +0.5.
    raw_accel = (0.5, 0.0, -9.80665)
    
    for i in range(20):
        t_ns = (i + 1) * 10_000_000
        sample = ImuSample(timestamp_ns=t_ns, accel_m_s2=raw_accel, gyro_rad_s=(0.0, 0.0, 0.0))
        calibrator.add_sample(sample)
    
    # Calibrator should have found the bias!
    cal_result = calibrator.get_calibration()
    assert cal_result.is_valid
    bias = cal_result.accel_bias.as_tuple()
    assert math.isclose(bias[0], 0.5, abs_tol=1e-3)
    
    # 2. Alignment Phase (Using calibrated samples)
    # We will simulate 10 IMU samples for gravity alignment, then GNSS for heading.
    for i in range(20, 35):
        t_ns = (i + 1) * 10_000_000
        raw_sample = ImuSample(timestamp_ns=t_ns, accel_m_s2=raw_accel, gyro_rad_s=(0.0, 0.0, 0.0))
        # Correct it
        cal_accel = (raw_sample.accel_m_s2[0] - bias[0], raw_sample.accel_m_s2[1] - bias[1], raw_sample.accel_m_s2[2] - bias[2])
        cal_sample = ImuSample(timestamp_ns=t_ns, accel_m_s2=cal_accel, gyro_rad_s=(0.0, 0.0, 0.0))
        align_engine.add_imu_sample(cal_sample)
        
    for i in range(35, 45):
        t_ns = (i + 1) * 10_000_000
        # GNSS fix moving North (0 heading)
        gnss_fix = GnssFix(timestamp_ns=t_ns, latitude_deg=0.0, longitude_deg=0.0, altitude_m=0.0,
                           velocity_ned_mps=(10.0, 0.0, 0.0), horizontal_accuracy_m=1.0, vertical_accuracy_m=1.0,
                           speed_accuracy_mps=0.1, satellite_count=10)
        align_engine.add_gnss_fix(gnss_fix)
        
    status = align_engine.get_alignment_status()
    assert status.state == AlignmentState.FULLY_ALIGNED
    q_s2v = align_engine.get_phone_to_vehicle_quaternion()
    
    # 3. INS Mechanization Phase (Stationary)
    # Now that we are aligned, let's trace 1 second of static data.
    ins.reset()
    for i in range(45, 145):
        t_ns = (i + 1) * 10_000_000
        raw_sample = ImuSample(timestamp_ns=t_ns, accel_m_s2=raw_accel, gyro_rad_s=(0.0, 0.0, 0.0))
        # Calibration Correction
        cal_accel = (raw_sample.accel_m_s2[0] - bias[0], raw_sample.accel_m_s2[1] - bias[1], raw_sample.accel_m_s2[2] - bias[2])
        cal_sample = ImuSample(timestamp_ns=t_ns, accel_m_s2=cal_accel, gyro_rad_s=(0.0, 0.0, 0.0))
        
        # Mechanization
        state = ins.propagate(cal_sample, q_sensor_to_vehicle=q_s2v, propagate_covariance=False)
        
    # As it's stationary, position and velocity should be highly close to 0.
    assert math.isclose(state.position_m[0], 0.0, abs_tol=1e-5)
    assert math.isclose(state.velocity_mps[0], 0.0, abs_tol=1e-5)

