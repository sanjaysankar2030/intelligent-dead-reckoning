"""
Unit tests for ML velocity estimator integration with ESKF.
"""
import pytest
import numpy as np
from core.navigation.state import NavState
from core.navigation.mechanization import StrapdownINS
from core.filters.eskf import ErrorStateKalmanFilter
from core.models.velocity_estimator import VelocityEstimatorAPI


def test_ml_velocity_update_acceptance():
    """Test that ML velocity update is accepted when within gate."""
    # Initialize INS with a known state
    initial_state = NavState(
        timestamp_ns=0,
        position_m=(0.0, 0.0, 0.0),
        velocity_mps=(10.0, 0.0, 0.0),  # Moving 10 m/s North
        attitude_q_v2n=(1.0, 0.0, 0.0, 0.0),  # Identity (vehicle aligned with NED)
        accel_bias_mps2=(0.0, 0.0, 0.0),
        gyro_bias_radps=(0.0, 0.0, 0.0)
    )

    ins = StrapdownINS(initial_state)
    eskf = ErrorStateKalmanFilter(ins)

    # ML model predicts forward velocity close to truth (10 m/s with small variance)
    result = eskf.update_forward_velocity(
        forward_speed_mps=10.1,  # Close to true 10.0 m/s
        variance=0.5,
        gate=3.0
    )

    assert result.accepted, "Update should be accepted when within gate"
    assert result.mahalanobis_dist < 3.0


def test_ml_velocity_update_rejection():
    """Test that ML velocity update is rejected when outside gate."""
    initial_state = NavState(
        timestamp_ns=0,
        position_m=(0.0, 0.0, 0.0),
        velocity_mps=(10.0, 0.0, 0.0),
        attitude_q_v2n=(1.0, 0.0, 0.0, 0.0),
        accel_bias_mps2=(0.0, 0.0, 0.0),
        gyro_bias_radps=(0.0, 0.0, 0.0)
    )

    ins = StrapdownINS(initial_state)
    eskf = ErrorStateKalmanFilter(ins)

    # ML model predicts wildly incorrect velocity
    result = eskf.update_forward_velocity(
        forward_speed_mps=30.0,  # Way off from 10.0 m/s
        variance=0.1,
        gate=3.0
    )

    assert not result.accepted, "Update should be rejected when outside gate"
    assert result.mahalanobis_dist > 3.0


def test_ml_velocity_corrects_drift():
    """Test that ML velocity update corrects velocity drift."""
    initial_state = NavState(
        timestamp_ns=0,
        position_m=(0.0, 0.0, 0.0),
        velocity_mps=(10.0, 2.0, 0.5),  # Drifted velocity with lateral/vertical components
        attitude_q_v2n=(1.0, 0.0, 0.0, 0.0),
        accel_bias_mps2=(0.0, 0.0, 0.0),
        gyro_bias_radps=(0.0, 0.0, 0.0)
    )

    ins = StrapdownINS(initial_state)
    eskf = ErrorStateKalmanFilter(ins)

    v_before = np.array(ins.state.velocity_mps)

    # ML model provides correct forward velocity (15 m/s)
    result = eskf.update_forward_velocity(
        forward_speed_mps=15.0,
        variance=1.0,
        gate=5.0
    )

    assert result.accepted

    v_after = np.array(ins.state.velocity_mps)

    # Velocity should have changed (correction applied)
    assert not np.allclose(v_before, v_after), "Velocity should be corrected"

    # Forward velocity component should move toward 15 m/s
    # (exact match not expected due to Kalman gain)
    forward_speed_after = v_after[0]  # North component (aligned with vehicle forward)
    assert abs(forward_speed_after - 15.0) < abs(v_before[0] - 15.0), \
        "Forward velocity should move closer to ML prediction"


def test_ml_velocity_high_uncertainty():
    """Test ML velocity update with high uncertainty has minimal effect."""
    initial_state = NavState(
        timestamp_ns=0,
        position_m=(0.0, 0.0, 0.0),
        velocity_mps=(10.0, 0.0, 0.0),
        attitude_q_v2n=(1.0, 0.0, 0.0, 0.0),
        accel_bias_mps2=(0.0, 0.0, 0.0),
        gyro_bias_radps=(0.0, 0.0, 0.0)
    )

    ins = StrapdownINS(initial_state)
    eskf = ErrorStateKalmanFilter(ins)

    v_before = np.array(ins.state.velocity_mps)

    # ML model with very high uncertainty
    result = eskf.update_forward_velocity(
        forward_speed_mps=20.0,  # Different from current 10.0
        variance=100.0,  # Very high uncertainty
        gate=10.0
    )

    v_after = np.array(ins.state.velocity_mps)

    # Change should be small due to high measurement uncertainty
    change = np.linalg.norm(v_after - v_before)
    assert change < 2.0, "High uncertainty should limit correction magnitude"


def test_ml_velocity_with_rotation():
    """Test ML velocity update when vehicle is rotated relative to NED."""
    # Vehicle rotated 90° (facing East instead of North)
    # Quaternion for 90° rotation around Z-axis (Down)
    # q = [cos(45°), 0, 0, sin(45°)] for 90° Z rotation
    q_90deg_z = (np.cos(np.pi/4), 0.0, 0.0, np.sin(np.pi/4))

    initial_state = NavState(
        timestamp_ns=0,
        position_m=(0.0, 0.0, 0.0),
        velocity_mps=(0.0, 10.0, 0.0),  # Moving East in NED frame
        attitude_q_v2n=q_90deg_z,  # Vehicle pointing East
        accel_bias_mps2=(0.0, 0.0, 0.0),
        gyro_bias_radps=(0.0, 0.0, 0.0)
    )

    ins = StrapdownINS(initial_state)
    eskf = ErrorStateKalmanFilter(ins)

    # ML model predicts forward velocity (in vehicle frame)
    result = eskf.update_forward_velocity(
        forward_speed_mps=10.0,
        variance=0.5,
        gate=5.0
    )

    assert result.accepted, "Update should handle rotated vehicle frame"


def test_ml_velocity_api_insufficient_data():
    """Test VelocityEstimatorAPI with insufficient buffer."""
    api = VelocityEstimatorAPI(model_path=None, window_size=100)

    # Add only 50 samples (less than window_size=100)
    for _ in range(50):
        api.add_vehicle_frame_sample(
            accel_v=(1.0, 0.0, -9.81),
            gyro_v=(0.0, 0.0, 0.0)
        )

    vel, var = api.estimate_velocity()

    # Should return fallback with high uncertainty
    assert vel == 0.0
    assert var == 100.0  # High uncertainty fallback


def test_ml_velocity_api_buffer_management():
    """Test that VelocityEstimatorAPI maintains correct rolling window."""
    api = VelocityEstimatorAPI(model_path=None, window_size=100)

    # Add 150 samples (exceeds window_size)
    for i in range(150):
        api.add_vehicle_frame_sample(
            accel_v=(float(i), 0.0, -9.81),
            gyro_v=(0.0, 0.0, 0.0)
        )

    # Buffer should contain only last 100 samples
    assert len(api.buffer) == 100

    # First sample in buffer should be from iteration 50 (150 - 100)
    assert api.buffer[0][0][0] == 50.0


def test_ml_velocity_api_clear():
    """Test clearing the velocity estimator buffer."""
    api = VelocityEstimatorAPI(model_path=None, window_size=100)

    for _ in range(100):
        api.add_vehicle_frame_sample(
            accel_v=(1.0, 0.0, -9.81),
            gyro_v=(0.0, 0.0, 0.0)
        )

    assert len(api.buffer) == 100

    api.clear()

    assert len(api.buffer) == 0


def test_ml_velocity_integration_eskf_covariance_update():
    """Test that ML velocity update properly updates covariance."""
    initial_state = NavState(
        timestamp_ns=0,
        position_m=(0.0, 0.0, 0.0),
        velocity_mps=(10.0, 0.0, 0.0),
        attitude_q_v2n=(1.0, 0.0, 0.0, 0.0),
        accel_bias_mps2=(0.0, 0.0, 0.0),
        gyro_bias_radps=(0.0, 0.0, 0.0)
    )

    ins = StrapdownINS(initial_state)
    eskf = ErrorStateKalmanFilter(ins)

    P_before = ins.covariance.copy()

    result = eskf.update_forward_velocity(
        forward_speed_mps=10.0,
        variance=0.5,
        gate=3.0
    )

    assert result.accepted

    P_after = ins.covariance

    # Covariance should change after update
    assert not np.allclose(P_before, P_after), "Covariance should be updated"

    # Covariance should remain positive semi-definite
    eigenvalues = np.linalg.eigvals(P_after)
    assert np.all(eigenvalues >= -1e-10), "Covariance should remain PSD"
