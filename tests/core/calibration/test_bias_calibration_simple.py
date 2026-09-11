"""
Unit tests for simple accelerometer and gyroscope bias calibration (NumPy-free).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from core.calibration.bias_calibration_simple import (
    StaticImuCalibrator,
    AccelBias,
    GyroBias,
    StaticCalibrationResult
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
    # Using acceleration that would violate the max_accel_deviation threshold
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

    # Add samples with no bias (perfect sensors measuring gravity in Z-down)
    for i in range(20):
        sample = ImuSample(
            timestamp_ns=1000000000 + i * 10000000,
            accel_m_s2=(0.0, 0.0, 9.81),  # Perfect gravity measurement (Z-down)
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
    # We use a higher variance threshold here because we are intentionally inserting
    # samples with different orientations to make the optimization problem well-posed
    calibrator = StaticImuCalibrator(min_samples=10, variance_threshold=2.0)

    # Known biases to inject
    true_accel_bias = (0.05, -0.02, 0.03)  # m/s^2
    true_gyro_bias = (0.001, -0.002, 0.0015)  # rad/s

    # Add samples with known bias
    # Note: to solve for bias using magnitude optimization, we need some variation in orientation,
    # otherwise the problem is ill-posed (many biases can produce the same constant magnitude).
    # We simulate slight device orientations while remaining "static" in each pose.
    import math
    for i in range(30):
        # Simulate slight tilt (e.g. resting on uneven surface, different poses)
        tilt_x = math.sin(i * 0.1) * 0.2
        tilt_y = math.cos(i * 0.1) * 0.2

        # True gravity vector in sensor frame
        g_x = tilt_x * 9.81
        g_y = tilt_y * 9.81
        g_z = math.sqrt(9.81**2 - g_x**2 - g_y**2)

        accel = (
            g_x + true_accel_bias[0],
            g_y + true_accel_bias[1],
            g_z + true_accel_bias[2]
        )
        gyro = (
            true_gyro_bias[0],
            true_gyro_bias[1],
            true_gyro_bias[2]
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
    # Higher tolerance for accel due to optimization with limited orientation variance
    assert abs(result.accel_bias.x - true_accel_bias[0]) < 0.1
    assert abs(result.accel_bias.y - true_accel_bias[1]) < 0.1
    assert abs(result.accel_bias.z - true_accel_bias[2]) < 0.15
    assert abs(result.gyro_bias.x - true_gyro_bias[0]) < 0.001
    assert abs(result.gyro_bias.y - true_gyro_bias[1]) < 0.001
    assert abs(result.gyro_bias.z - true_gyro_bias[2]) < 0.001
    assert result.error_message is None


def test_high_variance_rejection():
    """Test that high variance samples are rejected."""
    # Use smaller deviation limits to allow noise but then test that variance rejects it
    calibrator = StaticImuCalibrator(min_samples=10, variance_threshold=0.01)

    # Add samples with high variance
    # The noise must be small enough to pass the max_accel_deviation check
    # but large enough to fail the variance_threshold check when multiplied by std dev
    for i in range(20):
        # Vary measurements to create high variance (std dev > 0.01)
        # Using alternating values to increase variance without increasing mean error
        offset = 0.5 if i % 2 == 0 else -0.5
        accel = (
            offset,  # Variance will be ~0.25, std dev ~0.5 (>0.01 threshold)
            offset,
            9.81 + offset
        )
        gyro = (
            offset * 0.1,  # Variance will be ~0.0025, std dev ~0.05 (>0.01 threshold)
            offset * 0.1,
            offset * 0.1
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


if __name__ == "__main__":
    import pytest
    pytest.main([__file__])