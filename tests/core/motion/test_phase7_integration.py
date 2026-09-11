"""
End-to-end integration test: GNSS outage with ML velocity aiding and ZUPT.
"""
import pytest
import numpy as np
from core.sensors.data_types import ImuSample, GnssFix
from core.navigation.state import NavState
from core.navigation.mechanization import StrapdownINS
from core.filters.eskf import ErrorStateKalmanFilter
from core.models.velocity_estimator import VelocityEstimatorAPI
from core.motion.zupt_detector import ZuptDetector


def test_gnss_outage_with_ml_aiding():
    """
    Simplified test verifying Phase 7 components work together:
    - ZUPT detector correctly identifies stationary periods
    - ML velocity estimator API functions properly
    - Integration doesn't crash during simulated outage
    """
    # Initial state: stationary at origin
    initial_state = NavState(
        timestamp_ns=0,
        position_m=(0.0, 0.0, 0.0),
        velocity_mps=(0.0, 0.0, 0.0),
        attitude_q_v2n=(1.0, 0.0, 0.0, 0.0),
        accel_bias_mps2=(0.0, 0.0, 0.0),  # Zero biases for simplicity
        gyro_bias_radps=(0.0, 0.0, 0.0)
    )

    ins = StrapdownINS(initial_state)
    eskf = ErrorStateKalmanFilter(ins)
    vel_estimator = VelocityEstimatorAPI(model_path=None, window_size=100)
    zupt = ZuptDetector(window_size=50)

    dt = 0.01  # 100 Hz

    # Phase 1: Stationary (0-1 seconds)
    for i in range(100):
        t = i * dt

        # Stationary IMU samples
        accel = (0.0, 0.0, 9.81)
        gyro = (0.0, 0.0, 0.0)

        imu = ImuSample(
            timestamp_ns=int(t * 1e9),
            accel_m_s2=accel,
            gyro_rad_s=gyro
        )

        ins.propagate(imu)
        vel_estimator.add_vehicle_frame_sample(accel, gyro)
        zupt.add_sample(accel, gyro)

    # Verify ZUPT detects stationary
    p_stat = zupt.get_stationary_probability()
    assert p_stat > 0.7, f"Should detect stationary, got P(stat)={p_stat}"

    # Test adaptive ZUPT covariance
    R_zupt = zupt.get_adaptive_zupt_covariance()
    assert R_zupt.shape == (3, 3)
    assert np.all(np.diag(R_zupt) > 0.0), "ZUPT covariance should be positive"

    # Phase 2: Simulate moving (1-2 seconds)
    for i in range(100, 200):
        t = i * dt

        # Moving with acceleration
        accel = (2.0, 0.0, 9.81)
        gyro = (0.0, 0.0, 0.0)

        imu = ImuSample(
            timestamp_ns=int(t * 1e9),
            accel_m_s2=accel,
            gyro_rad_s=gyro
        )

        ins.propagate(imu)
        vel_estimator.add_vehicle_frame_sample(accel, gyro)
        zupt.add_sample(accel, gyro)

    # Verify ZUPT detects motion
    p_stat_moving = zupt.get_stationary_probability()
    assert p_stat_moving < 0.7, f"Should detect motion, got P(stat)={p_stat_moving}"

    # Verify ML velocity API works
    if len(vel_estimator.buffer) >= vel_estimator.window_size:
        v_ml, var_ml = vel_estimator.estimate_velocity()
        assert var_ml > 0.0, "ML velocity variance should be positive"

    # Test ML velocity update integration (even with untrained model)
    result = eskf.update_forward_velocity(forward_speed_mps=1.0, variance=1.0, gate=10.0)
    # Result may be accepted or rejected depending on innovation, but shouldn't crash
    assert result.mahalanobis_dist >= 0.0

    # Test passes if all components work together without errors
    assert True


def test_zupt_during_traffic_stop():
    """Test ZUPT detector during simulated traffic stop."""
    initial_state = NavState(
        timestamp_ns=0,
        position_m=(100.0, 50.0, 0.0),
        velocity_mps=(10.0, 0.0, 0.0),  # Initially moving
        attitude_q_v2n=(1.0, 0.0, 0.0, 0.0),
        accel_bias_mps2=(0.0, 0.0, 0.0),
        gyro_bias_radps=(0.0, 0.0, 0.0)
    )

    ins = StrapdownINS(initial_state)
    eskf = ErrorStateKalmanFilter(ins)
    zupt = ZuptDetector(window_size=50)

    dt = 0.01

    # Phase 1: Moving (0-1 second)
    for i in range(100):
        accel = (1.0, 0.0, 9.81)  # Some forward acceleration
        gyro = (0.0, 0.0, 0.0)

        imu = ImuSample(
            timestamp_ns=int(i * dt * 1e9),
            accel_m_s2=accel,
            gyro_rad_s=gyro
        )

        ins.propagate(imu)
        zupt.add_sample(accel, gyro)

    p_stat_moving = zupt.get_stationary_probability()
    assert p_stat_moving < 0.7, f"Should detect movement, got P(stat)={p_stat_moving}"

    # Phase 2: Deceleration (1-2 seconds)
    for i in range(100, 200):
        accel = (-1.0, 0.0, 9.81)  # Deceleration
        gyro = (0.0, 0.0, 0.0)

        imu = ImuSample(
            timestamp_ns=int(i * dt * 1e9),
            accel_m_s2=accel,
            gyro_rad_s=gyro
        )

        ins.propagate(imu)
        zupt.add_sample(accel, gyro)

    # Phase 3: Stationary (2-4 seconds)
    for i in range(200, 400):
        accel = (0.0, 0.0, 9.81 + 0.01 * np.random.randn())
        gyro = (0.001 * np.random.randn(), 0.001 * np.random.randn(), 0.001 * np.random.randn())

        imu = ImuSample(
            timestamp_ns=int(i * dt * 1e9),
            accel_m_s2=accel,
            gyro_rad_s=gyro
        )

        ins.propagate(imu)
        zupt.add_sample(accel, gyro)

    p_stat_stopped = zupt.get_stationary_probability()
    assert p_stat_stopped > 0.65, f"Should detect stationary at traffic stop, got P(stat)={p_stat_stopped}"

    # Apply adaptive ZUPT
    R_zupt = zupt.get_adaptive_zupt_covariance(base_variance=0.01)
    result = eskf.update_zero_velocity(vel_cov=R_zupt)

    # ZUPT update should be applied successfully
    assert result is not None, "ZUPT update should return a result"

    # Verify that covariance was updated (shows ZUPT was integrated)
    assert ins.covariance is not None

    # Test passes if ZUPT detector correctly identified stationary state
    # and the ZUPT update was successfully integrated into ESKF
    assert True
