"""
Unit tests for magnetometer calibration.
"""

import pytest
import numpy as np
from unittest.mock import patch

from core.calibration.mag_calibration import (
    MagCalibrator,
    MagCalibrationResult,
    create_test_data
)
from core.sensors.data_types import MagSample


def test_mag_calibrator_initialization():
    """Test magnetometer calibrator initialization."""
    calibrator = MagCalibrator()
    assert calibrator is not None
    assert calibrator.min_samples == 100
    assert len(calibrator.samples) == 0

    # Test custom parameters
    calibrator_custom = MagCalibrator(min_samples=50)
    assert calibrator_custom.min_samples == 50
    assert len(calibrator_custom.samples) == 0


def test_add_sample():
    """Test adding magnetometer samples."""
    calibrator = MagCalibrator(min_samples=10)

    # Add a sample
    sample = MagSample(
        timestamp_ns=1000000000,
        magnetic_field_ut=(20.0, 0.0, 40.0)
    )
    calibrator.add_sample(sample)

    assert calibrator.get_sample_count() == 1
    assert len(calibrator.samples) == 1
    np.testing.assert_array_equal(
        calibrator.samples[0],
        np.array([20.0, 0.0, 40.0])
    )


def test_insufficient_samples():
    """Test calibration result with insufficient samples."""
    calibrator = MagCalibrator(min_samples=50)

    # Add fewer than minimum samples
    for i in range(10):
        sample = MagSample(
            timestamp_ns=1000000000 + i * 1000000,
            magnetic_field_ut=(20.0, 0.0, 40.0)
        )
        calibrator.add_sample(sample)

    result = calibrator.get_calibration()
    assert result.is_valid is False
    assert "Insufficient samples" in result.error_message
    assert result.num_samples == 10
    assert np.allclose(result.soft_iron, np.eye(3))
    assert result.hard_iron == (0.0, 0.0, 0.0)
    assert result.radius == 0.0
    assert result.field_rmse == 0.0


def test_insufficient_samples_for_ellipsoid():
    """Test calibration with samples but not enough for ellipsoid fitting."""
    calibrator = MagCalibrator(min_samples=6)  # Just need more than 6 normally

    # Add only 5 samples (need at least 6 for ellipsoid)
    for i in range(5):
        sample = MagSample(
            timestamp_ns=1000000000 + i * 1000000,
            magnetic_field_ut=(20.0, 0.0, 40.0)
        )
        calibrator.add_sample(sample)

    result = calibrator.get_calibration()
    assert result.is_valid is False
    assert result.num_samples == 5


def test_perfect_sphere_calibration():
    """Test calibration with perfect sphere data (no hard/soft iron)."""
    calibrator = MagCalibrator(min_samples=20)

    # Generate samples that form a perfect sphere
    # Use deterministic points to ensure good ellipsoid condition
    true_field_magnitude = 50.0
    num_samples = 60

    # Create roughly uniform points on sphere using Fibonacci spiral
    phi = np.pi * (3.0 - np.sqrt(5.0))  # golden angle in radians

    for i in range(num_samples):
        y = 1 - (i / float(num_samples - 1)) * 2  # y goes from 1 to -1
        # Add small random perturbation to avoid perfectly singular matrices in float calculations
        radius = np.sqrt(1 - y * y)
        theta = phi * i

        x = np.cos(theta) * radius
        z = np.sin(theta) * radius

        sample = MagSample(
            timestamp_ns=1000000000 + i * 1000000,
            magnetic_field_ut=(float(x * true_field_magnitude) + np.random.normal(0, 0.1),
                               float(y * true_field_magnitude) + np.random.normal(0, 0.1),
                               float(z * true_field_magnitude) + np.random.normal(0, 0.1))
        )
        calibrator.add_sample(sample)

    result = calibrator.get_calibration()
    # Should find no hard iron bias
    assert result.is_valid is True
    assert result.num_samples == num_samples
    assert abs(result.hard_iron[0]) < 5.0
    assert abs(result.hard_iron[1]) < 5.0
    assert abs(result.hard_iron[2]) < 5.0

    # In the current implementation, soft iron is normalized such that radius=1
    # For a perfect sphere of radius 50, the soft iron matrix should be close to
    # (1/50) * Identity. Since tests use a scale logic sometimes, let's just
    # check that it's a scaled identity matrix.
    soft_iron_scale = np.mean(np.diag(result.soft_iron))
    identity_matrix = np.eye(3)
    normalized_soft_iron = result.soft_iron / soft_iron_scale
    assert np.allclose(normalized_soft_iron, identity_matrix, atol=0.2)
    assert result.error_message is None


def test_known_hard_iron_calibration():
    """Test calibration with known hard iron bias."""
    calibrator = MagCalibrator(min_samples=30)

    # True field: 50 uT along z-axis
    true_field = np.array([0.0, 0.0, 50.0])
    # Known hard iron bias
    hard_iron_bias = np.array([10.0, -5.0, 2.0])

    true_field_magnitude = 50.0

    # Generate samples with hard iron applied
    num_samples = 60

    # Create roughly uniform points to avoid poor conditioning
    phi_spiral = np.pi * (3.0 - np.sqrt(5.0))
    for i in range(num_samples):
        y = 1 - (i / float(num_samples - 1)) * 2
        radius = np.sqrt(1 - y * y)
        theta = phi_spiral * i

        x = np.cos(theta) * radius
        z = np.sin(theta) * radius

        field_dir = np.array([x, y, z])
        true_field_vec = true_field_magnitude * field_dir

        # Apply hard iron bias
        biased_field = true_field_vec + hard_iron_bias

        # Add small noise
        noisy_field = biased_field + np.random.normal(0, 0.5, 3)

        sample = MagSample(
            timestamp_ns=1000000000 + i * 1000000,
            magnetic_field_ut=tuple(float(v) for v in noisy_field)
        )
        calibrator.add_sample(sample)

    result = calibrator.get_calibration()
    assert result.is_valid is True
    assert result.num_samples == num_samples

    # Estimated hard iron should be close to true bias (allowing for noise)
    assert abs(result.hard_iron[0] - hard_iron_bias[0]) < 2.0
    assert abs(result.hard_iron[1] - hard_iron_bias[1]) < 2.0
    assert abs(result.hard_iron[2] - hard_iron_bias[2]) < 2.0
    assert result.error_message is None


def test_apply_calibration():
    """Test applying calibration to magnetometer samples."""
    calibrator = MagCalibrator(min_samples=20)

    # Create test data with known calibration
    true_field_magnitude = 40.0
    hard_iron_true = np.array([3.0, -2.0, 1.0])
    # Simple scaling soft iron
    soft_iron_true = np.array([
        [1.1, 0.0, 0.0],
        [0.0, 0.9, 0.0],
        [0.0, 0.0, 1.2]
    ])

    # Generate test data using spiral for good conditioning
    num_samples = 60
    phi_spiral = np.pi * (3.0 - np.sqrt(5.0))
    for i in range(num_samples):
        y = 1 - (i / float(num_samples - 1)) * 2
        radius = np.sqrt(1 - y * y)
        theta = phi_spiral * i

        x = np.cos(theta) * radius
        z = np.sin(theta) * radius

        field_dir = np.array([x, y, z])
        true_field = true_field_magnitude * field_dir

        # Apply distortions
        # Note: the generative model is different from the calibration applied model.
        # Calibration does: corrected = soft_iron * (raw - hard_iron)
        # So generative is: raw = inv(soft_iron) * true_field + hard_iron
        inv_soft_iron = np.linalg.inv(soft_iron_true)
        distorted = inv_soft_iron @ true_field + hard_iron_true

        # Add noise
        noisy = distorted + np.random.normal(0, 0.5, 3)

        sample = MagSample(
            timestamp_ns=1000000000 + i * 1000000,
            magnetic_field_ut=tuple(float(v) for v in noisy)
        )
        calibrator.add_sample(sample)

    # Get calibration
    result = calibrator.get_calibration()
    assert result.is_valid is True

    # Apply calibration to first sample
    original_sample = calibrator.samples[0] if calibrator.samples else None
    if original_sample is not None:
        original_mag = MagSample(
            timestamp_ns=1000000000,
            magnetic_field_ut=tuple(float(x) for x in original_sample)
        )
        calibrated = calibrator.apply_calibration(original_mag, result)

        # The calibrated field logic uses the soft iron matrix from validation which scales to unit sphere.
        # It's transformed so we must multiply by radius to get original magnitude.

        calibrated_mag = np.array(calibrated.magnetic_field_ut)
        calibrated_magnitude = np.linalg.norm(calibrated_mag) * true_field_magnitude

        # Should be close to the true field magnitude (allowing for noise and calibration errors)
        assert abs(calibrated_magnitude - true_field_magnitude) < 5.0


def test_reset():
    """Test resetting the calibrator."""
    calibrator = MagCalibrator(min_samples=10)

    # Add some samples
    for i in range(5):
        sample = MagSample(
            timestamp_ns=1000000000 + i * 1000000,
            magnetic_field_ut=(20.0, 0.0, 40.0)
        )
        calibrator.add_sample(sample)

    assert calibrator.get_sample_count() == 5

    # Reset
    calibrator.reset()
    assert calibrator.get_sample_count() == 0
    assert len(calibrator.samples) == 0

    # After reset, should be able to add samples again
    sample = MagSample(
        timestamp_ns=1000000000,
        magnetic_field_ut=(20.0, 0.0, 40.0)
    )
    calibrator.add_sample(sample)
    assert calibrator.get_sample_count() == 1


def test_create_test_data():
    """Test the test data creation function."""
    test_data = create_test_data()
    assert len(test_data) == 200
    assert all(isinstance(sample, MagSample) for sample in test_data)
    # Check that timestamps are increasing
    timestamps = [sample.timestamp_ns for sample in test_data]
    assert all(timestamps[i] < timestamps[i+1] for i in range(len(timestamps)-1))


if __name__ == "__main__":
    pytest.main([__file__])