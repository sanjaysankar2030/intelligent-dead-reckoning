"""
Unit tests for accelerometer and gyroscope bias calibration.
"""

import pytest
import numpy as np
from unittest.mock import patch

from core.calibration.bias_calibration import (
    StaticImuCalibrator,
    AccelBias,
    GyroBias,
    StaticCalibrationResult,
    create_test_data
)
from core.sensors.data_types import ImuSample


def test_static_imu_calibrator_initialization():
    """Test calibrator initialization with default and custom parameters."""
    calibrator = StaticImuCalibrator()
    assert calibrator is not None
    assert calibrator.min_samples == 100
    assert calibrator.gravity_magnitude == 9.80665

    # Test custom parameters
    calibrator_custom = StaticImuCalibrator(
        gravity_magnitude=9.5,
        max_accel_deviation=1.0,
        max_gyro_deviation=0.2,
        min_samples=50,
        variance_threshold=0.005
    )
    assert calibrator_custom.gravity_magnitude == 9.5
    assert calibrator_custom.max_accel_deviation == 1.0
    assert calibrator_custom.max_gyro_deviation == 0.2
    assert calibrator_custom.min_samples == 50
    assert calibrator_custom.variance_threshold == 0.005


def test_add_sample_static_conditions():
    """Test adding samples that meet static conditions."""
    calibrator = StaticImuCalibrator(min_samples=10)

    # Create a sample that should be considered static
    # Accel: [0, 0, 9.81] (gravity only)
    # Gyro: [0, 0, 0] (no rotation)
    static_sample = ImuSample(
        timestamp_ns=1000000000,
        accel_m_s2=(0.0, 0.0, 9.81),
        gyro_rad_s=(0.0, 0.0, 0.0)
    )

    # Add sample - should return True (accepted)
    assert calibrator.add_sample(static_sample) is True
    assert calibrator.get_sample_count() == 1

    # Add another static sample
    static_sample2 = ImuSample(
        timestamp_ns=1000000010,
        accel_m_s2=(0.0, 0.0, 9.81),
        gyro_rad_s=(0.0, 0.0, 0.0)
    )
    assert calibrator.add_sample(static_sample2) is True
    assert calibrator.get_sample_count() == 2


def test_add_sample_non_static_conditions():
    """Test adding samples that do NOT meet static conditions."""
    calibrator = StaticImuCalibrator(min_samples=10)

    # Sample with high linear acceleration (not static)
    accelerating_sample = ImuSample(
        timestamp_ns=1000000000,
        accel_m_s2=(15.0, 0.0, 9.81),  # 15 m/s^2 forward acceleration (exceeds default 2.0)
        gyro_rad_s=(0.0, 0.0, 0.0)
    )

    # Add sample - should return False (rejected)
    assert calibrator.add_sample(accelerating_sample) is False
    assert calibrator.get_sample_count() == 0

    # Sample with high angular velocity (not static)
    rotating_sample = ImuSample(
        timestamp_ns=1000000000,
        accel_m_s2=(0.0, 0.0, 9.81),
        gyro_rad_s=(1.0, 0.0, 0.0)  # 1.0 rad/s rotation (exceeds default 0.5)
    )

    assert calibrator.add_sample(rotating_sample) is False
    assert calibrator.get_sample_count() == 0


def test_insufficient_samples():
    """Test calibration result with insufficient samples."""
    calibrator = StaticImuCalibrator(min_samples=50)

    # Add fewer than minimum samples
    for i in range(10):
        sample = ImuSample(
            timestamp_ns=1000000000 + i * 10000000,
            accel_m_s2=(0.0, 0.0, 9.81),
            gyro_rad_s=(0.0, 0.0, 0.0)
        )
        calibrator.add_sample(sample)

    result = calibrator.get_calibration()
    assert result.is_valid is False
    assert "Insufficient samples" in result.error_message
    assert result.num_samples == 10
    assert result.accel_bias == AccelBias(0.0, 0.0, 0.0)
    assert result.gyro_bias == GyroBias(0.0, 0.0, 0.0)


def test_sufficient_samples_no_bias():
    """Test calibration with sufficient samples and no bias."""
    calibrator = StaticImuCalibrator(min_samples=10)

    # Add samples with no bias (perfect sensors)
    for i in range(20):
        sample = ImuSample(
            timestamp_ns=1000000000 + i * 10000000,
            accel_m_s2=(0.0, 0.0, 9.81),  # Perfect gravity measurement
            gyro_rad_s=(0.0, 0.0, 0.0)    # Perfect zero gyro
        )
        calibrator.add_sample(sample)

    result = calibrator.get_calibration()
    assert result.is_valid is True
    assert result.num_samples == 20
    # Bias should be close to zero
    assert abs(result.accel_bias.x) < 0.01
    assert abs(result.accel_bias.y) < 0.01
    assert abs(result.accel_bias.z) < 0.01
    assert abs(result.gyro_bias.x) < 0.001
    assert abs(result.gyro_bias.y) < 0.001
    assert abs(result.gyro_bias.z) < 0.001
    assert result.error_message is None


def test_sufficient_samples_with_bias():
    """Test calibration with sufficient samples and known bias."""
    calibrator = StaticImuCalibrator(min_samples=10)

    # Known biases to inject
    true_accel_bias = (0.05, -0.02, 0.03)  # m/s^2
    true_gyro_bias = (0.001, -0.002, 0.0015)  # rad/s

    # Add samples with known bias
    for i in range(30):
        accel = (
            true_accel_bias[0] + np.random.normal(0, 0.005),
            true_accel_bias[1] + np.random.normal(0, 0.005),
            true_accel_bias[2] + 9.81 + np.random.normal(0, 0.005)  # Z includes gravity
        )
        gyro = (
            true_gyro_bias[0] + np.random.normal(0, 0.0005),
            true_gyro_bias[1] + np.random.normal(0, 0.0005),
            true_gyro_bias[2] + np.random.normal(0, 0.0005)
        )

        sample = ImuSample(
            timestamp_ns=1000000000 + i * 10000000,
            accel_m_s2=accel,
            gyro_rad_s=gyro
        )
        calibrator.add_sample(sample)

    result = calibrator.get_calibration()
    assert result.is_valid is True
    assert result.num_samples == 30

    # Estimated bias should be close to true bias
    assert abs(result.accel_bias.x - true_accel_bias[0]) < 0.02
    assert abs(result.accel_bias.y - true_accel_bias[1]) < 0.02
    assert abs(result.accel_bias.z - true_accel_bias[2]) < 0.02
    assert abs(result.gyro_bias.x - true_gyro_bias[0]) < 0.002
    assert abs(result.gyro_bias.y - true_gyro_bias[1]) < 0.002
    assert abs(result.gyro_bias.z - true_gyro_bias[2]) < 0.002
    assert result.error_message is None


def test_high_variance_rejection():
    """Test that high variance samples are rejected."""
    calibrator = StaticImuCalibrator(min_samples=10, variance_threshold=0.01)

    # Add samples with high variance (should still be accepted as static if mean is good)
    # But the final calibration should fail due to high variance
    for i in range(20):
        # Large noise added
        accel = (
            np.random.normal(0, 0.2),  # High noise
            np.random.normal(0, 0.2),
            9.81 + np.random.normal(0, 0.2)
        )
        gyro = (
            np.random.normal(0, 0.1),  # High noise
            np.random.normal(0, 0.1),
            np.random.normal(0, 0.1)
        )

        sample = ImuSample(
            timestamp_ns=1000000000 + i * 10000000,
            accel_m_s2=accel,
            gyro_rad_s=gyro
        )
        calibrator.add_sample(sample)

    result = calibrator.get_calibration()
    # Should fail due to high variance
    assert result.is_valid is False
    assert "Variance too high" in result.error_message
    assert result.num_samples == 20


def test_reset():
    """Test resetting the calibrator."""
    calibrator = StaticImuCalibrator(min_samples=10)

    # Add some samples
    for i in range(5):
        sample = ImuSample(
            timestamp_ns=1000000000 + i * 10000000,
            accel_m_s2=(0.0, 0.0, 9.81),
            gyro_rad_s=(0.0, 0.0, 0.0)
        )
        calibrator.add_sample(sample)

    assert calibrator.get_sample_count() == 5

    # Reset
    calibrator.reset()
    assert calibrator.get_sample_count() == 0

    # After reset, should be able to add samples again
    sample = ImuSample(
        timestamp_ns=1000000000,
        accel_m_s2=(0.0, 0.0, 9.81),
        gyro_rad_s=(0.0, 0.0, 0.0)
    )
    assert calibrator.add_sample(sample) is True
    assert calibrator.get_sample_count() == 1


def test_create_test_data():
    """Test the test data creation function."""
    test_data = create_test_data()
    assert len(test_data) == 200
    assert all(isinstance(sample, ImuSample) for sample in test_data)
    # Check that timestamps are increasing
    timestamps = [sample.timestamp_ns for sample in test_data]
    assert all(timestamps[i] < timestamps[i+1] for i in range(len(timestamps)-1))


if __name__ == "__main__":
    pytest.main([__file__])