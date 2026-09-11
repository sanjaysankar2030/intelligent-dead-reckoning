"""
Deterministic replay verification tests for sensor calibration pipeline.
Tests that the calibration engine produces consistent results when given
the same synthetic sensor data stream.
"""

from __future__ import annotations

import numpy as np
import pytest

from core.calibration.bias_calibration import StaticImuCalibrator
from core.calibration.mag_calibration import MagCalibrator
from core.calibration.pipeline import SensorDataPipeline
from core.calibration.persistence import CalibrationPersistence
from core.sensors.data_types import ImuSample, MagSample
from core.sensors.health import SensorHealthManager


def create_imu_bias_sample(bias_accel: tuple, bias_gyro: tuple,
                          gravity_magnitude: float = 9.80665,
                          noise_level: float = 0.01) -> ImuSample:
    """Create an IMU sample with known bias and gravity in Z-down orientation."""
    return ImuSample(
        timestamp_ns=1000000000,
        accel_m_s2=(
            bias_accel[0] + np.random.normal(0, noise_level),
            bias_accel[1] + np.random.normal(0, noise_level),
            bias_accel[2] + gravity_magnitude + np.random.normal(0, noise_level)
        ),
        gyro_rad_s=(
            bias_gyro[0] + np.random.normal(0, noise_level * 0.1),
            bias_gyro[1] + np.random.normal(0, noise_level * 0.1),
            bias_gyro[2] + np.random.normal(0, noise_level * 0.1)
        )
    )


def create_mag_sample_with_calibration(true_field_magnitude: float,
                                      hard_iron: tuple,
                                      soft_iron: np.ndarray,
                                      index: int,
                                      num_samples: int,
                                      noise_level: float = 0.1) -> MagSample:
    """Create a magnetometer sample with known calibration parameters on a sphere."""
    phi_spiral = np.pi * (3.0 - np.sqrt(5.0))
    y = 1 - (index / float(max(1, num_samples - 1))) * 2
    radius = np.sqrt(1 - y * y)
    theta = phi_spiral * index

    x = np.cos(theta) * radius
    z = np.sin(theta) * radius

    field_dir = np.array([x, y, z])
    true_field_vec = true_field_magnitude * field_dir
    hard_iron_np = np.array(hard_iron)

    # Apply soft iron distortion then add hard iron bias
    distorted = soft_iron @ true_field_vec + hard_iron_np
    noisy = distorted + np.random.normal(0, noise_level, 3)

    return MagSample(
        timestamp_ns=1000000000 + index * 1000000,
        magnetic_field_ut=tuple(noisy)
    )


def test_deterministic_imu_calibration():
    """Test that IMU calibration produces deterministic results with fixed seed."""
    # Set random seed for reproducibility
    np.random.seed(42)

    # Known biases to inject
    true_accel_bias = (0.05, -0.02, 0.03)  # m/s^2
    true_gyro_bias = (0.001, -0.002, 0.0015)  # rad/s

    # Create calibrator
    calibrator = StaticImuCalibrator(min_samples=50, variance_threshold=0.1)

    # Generate deterministic samples
    samples = []
    for i in range(100):
        sample = create_imu_bias_sample(true_accel_bias, true_gyro_bias, noise_level=0.01)
        samples.append(sample)
        calibrator.add_sample(sample)

    # Get calibration result
    result1 = calibrator.get_calibration()

    # Reset and repeat with same seed
    np.random.seed(42)
    calibrator2 = StaticImuCalibrator(min_samples=50, variance_threshold=0.1)

    samples2 = []
    for i in range(100):
        sample = create_imu_bias_sample(true_accel_bias, true_gyro_bias, noise_level=0.01)
        samples2.append(sample)
        calibrator2.add_sample(sample)

    result2 = calibrator2.get_calibration()

    # Results should be identical (within floating point precision)
    assert result1.is_valid == result2.is_valid
    assert result1.num_samples == result2.num_samples

    if result1.is_valid and result2.is_valid:
        assert abs(result1.accel_bias.x - result2.accel_bias.x) < 1e-10
        assert abs(result1.accel_bias.y - result2.accel_bias.y) < 1e-10
        assert abs(result1.accel_bias.z - result2.accel_bias.z) < 1e-10
        assert abs(result1.gyro_bias.x - result2.gyro_bias.x) < 1e-10
        assert abs(result1.gyro_bias.y - result2.gyro_bias.y) < 1e-10
        assert abs(result1.gyro_bias.z - result2.gyro_bias.z) < 1e-10


def test_deterministic_mag_calibration():
    """Test that magnetometer calibration produces deterministic results with fixed seed."""
    # Set random seed for reproducibility
    np.random.seed(42)

    # True field and calibration parameters
    true_field_magnitude = np.linalg.norm([20.0, 0.0, 40.0])  # uT
    hard_iron_true = np.array([5.0, -3.0, 2.0])  # uT
    soft_iron_true = np.array([
        [1.2, 0.1, 0.0],
        [0.05, 0.9, 0.0],
        [0.0, 0.0, 1.1]
    ])

    # Create calibrator
    calibrator = MagCalibrator(min_samples=50)

    # Generate deterministic samples with varying orientations
    num_samples = 100
    for i in range(num_samples):
        sample = create_mag_sample_with_calibration(
            true_field_magnitude, hard_iron_true, soft_iron_true, i, num_samples, noise_level=0.1
        )
        calibrator.add_sample(sample)

    # Get calibration result
    result1 = calibrator.get_calibration()

    # Reset and repeat with same seed
    np.random.seed(42)
    calibrator2 = MagCalibrator(min_samples=50)

    for i in range(num_samples):
        sample = create_mag_sample_with_calibration(
            true_field_magnitude, hard_iron_true, soft_iron_true, i, num_samples, noise_level=0.1
        )
        calibrator2.add_sample(sample)

    result2 = calibrator2.get_calibration()

    # Results should be identical (within floating point precision)
    assert result1.is_valid == result2.is_valid
    assert result1.num_samples == result2.num_samples

    if result1.is_valid and result2.is_valid:
        assert abs(result1.hard_iron[0] - result2.hard_iron[0]) < 1e-10
        assert abs(result1.hard_iron[1] - result2.hard_iron[1]) < 1e-10
        assert abs(result1.hard_iron[2] - result2.hard_iron[2]) < 1e-10

        # Check soft iron matrix (should be close)
        np.testing.assert_array_almost_equal(
            result1.soft_iron, result2.soft_iron, decimal=10
        )


def test_pipeline_deterministic_replay():
    """Test that the full pipeline produces deterministic results."""
    # Set random seed for reproducibility
    np.random.seed(42)

    # Known biases
    true_accel_bias = (0.03, -0.01, 0.02)
    true_gyro_bias = (0.0005, -0.001, 0.0008)
    true_field = np.array([20.0, 0.0, 40.0])
    hard_iron_true = np.array([2.0, -1.0, 0.5])
    soft_iron_true = np.array([
        [1.1, 0.05, 0.0],
        [0.02, 0.95, 0.0],
        [0.0, 0.0, 1.05]
    ])

    # Create pipeline
    pipeline1 = SensorDataPipeline(mag_calibrator=MagCalibrator(min_samples=20))
    print(f"Pipeline1 IMU calibrator min_samples: {pipeline1.imu_calibrator.min_samples}")
    print(f"Pipeline1 Mag calibrator min_samples: {pipeline1.mag_calibrator.min_samples}")

    # Generate and process deterministic samples
    for i in range(200):
        # IMU sample
        imu_sample = create_imu_bias_sample(
            true_accel_bias, true_gyro_bias, noise_level=0.005
        )
        accepted_imu, calibrated_imu = pipeline1.add_imu_sample(imu_sample)

        # Mag sample (less frequent)
        if i % 4 == 0:
            mag_sample = create_mag_sample_with_calibration(
                np.linalg.norm(true_field),  # true_field_magnitude
                hard_iron_true,
                soft_iron_true,
                i // 4,  # index for mag samples
                50,  # total number of mag samples we expect
                noise_level=0.05
            )
            accepted_mag, calibrated_mag = pipeline1.add_mag_sample(mag_sample)

    print(f"Pipeline1 samples processed: {pipeline1.samples_processed}")
    print(f"Pipeline1 calibration samples collected: {pipeline1.calibration_samples_collected}")

    # Update calibration
    updated1 = pipeline1.update_calibration()
    print(f"Pipeline1 update_calibration returned: {updated1}")

    quality1 = pipeline1.get_calibration_quality()
    print(f"Pipeline1 quality: {quality1}")

    # Save calibration
    import tempfile
    import os
    with tempfile.TemporaryDirectory() as tmpdir:
        save_path = os.path.join(tmpdir, "calibration.json")
        print(f"Attempting to save to: {save_path}")
        saved_file = pipeline1.save_calibration(save_path)
        print(f"Save calibration returned: {saved_file}")

        if saved_file is None:
            print("ERROR: save_calibration returned None!")
            print(f"Pipeline1 is_calibrated(): {pipeline1.is_calibrated()}")
            print(f"Pipeline1 imu_calibration_result: {pipeline1.imu_calibration_result}")
            if pipeline1.imu_calibration_result:
                print(f"Pipeline1 imu_calibration_result.is_valid: {pipeline1.imu_calibration_result.is_valid}")
            print(f"Pipeline1 mag_calibration_result: {pipeline1.mag_calibration_result}")
            if pipeline1.mag_calibration_result:
                print(f"Pipeline1 mag_calibration_result.is_valid: {pipeline1.mag_calibration_result.is_valid}")

        # Create second pipeline and load calibration
        pipeline2 = SensorDataPipeline()
        print(f"Pipeline2 IMU calibrator min_samples: {pipeline2.imu_calibrator.min_samples}")
        print(f"Pipeline2 Mag calibrator min_samples: {pipeline2.mag_calibrator.min_samples}")
        loaded = pipeline2.load_calibration(save_path)
        print(f"Load calibration returned: {loaded}")
        quality2 = pipeline2.get_calibration_quality()
        print(f"Pipeline2 quality: {quality2}")

        # Qualities should be identical
        assert quality1['imu_calibrated'] == quality2['imu_calibrated']
        assert quality1['mag_calibrated'] == quality2['mag_calibrated']
        assert quality1['imu_samples'] == quality2['imu_samples']
        assert quality1['mag_samples'] == quality2['mag_samples']

        if quality1['imu_accel_bias'] and quality2['imu_accel_bias']:
            np.testing.assert_array_almost_equal(
                quality1['imu_accel_bias'], quality2['imu_accel_bias'], decimal=10
            )
            np.testing.assert_array_almost_equal(
                quality1['imu_gyro_bias'], quality2['imu_gyro_bias'], decimal=10
            )

        if quality1['mag_hard_iron'] and quality2['mag_hard_iron']:
            np.testing.assert_array_almost_equal(
                quality1['mag_hard_iron'], quality2['mag_hard_iron'], decimal=10
            )


def test_health_monitor_deterministic():
    """Test that health monitoring produces deterministic results."""
    # Set random seed
    np.random.seed(42)

    # Create health monitors
    imu_monitor1 = SensorHealthManager()
    mag_monitor1 = SensorHealthManager()

    # Generate deterministic samples
    health_statuses_imu = []
    health_statuses_mag = []

    for i in range(100):
        # Normal IMU sample
        imu_sample = ImuSample(
            timestamp_ns=1000000000 + i * 10000000,
            accel_m_s2=(
                0.0 + np.random.normal(0, 0.01),
                0.0 + np.random.normal(0, 0.01),
                9.81 + np.random.normal(0, 0.01)
            ),
            gyro_rad_s=(
                0.001 + np.random.normal(0, 0.001),
                -0.002 + np.random.normal(0, 0.001),
                0.0015 + np.random.normal(0, 0.001)
            )
        )

        # Normal Mag sample
        mag_sample = MagSample(
            timestamp_ns=1000000000 + i * 10000000,
            magnetic_field_ut=(
                20.0 + np.random.normal(0, 0.1),
                0.0 + np.random.normal(0, 0.1),
                40.0 + np.random.normal(0, 0.1)
            )
        )

        imu_status = imu_monitor1.update_imu(imu_sample)
        mag_status = mag_monitor1.update_mag(mag_sample)

        health_statuses_imu.append(imu_status)
        health_statuses_mag.append(mag_status)

    # Reset and repeat with same seed
    np.random.seed(42)
    imu_monitor2 = SensorHealthManager()
    mag_monitor2 = SensorHealthManager()

    health_statuses_imu2 = []
    health_statuses_mag2 = []

    for i in range(100):
        imu_sample = ImuSample(
            timestamp_ns=1000000000 + i * 10000000,
            accel_m_s2=(
                0.0 + np.random.normal(0, 0.01),
                0.0 + np.random.normal(0, 0.01),
                9.81 + np.random.normal(0, 0.01)
            ),
            gyro_rad_s=(
                0.001 + np.random.normal(0, 0.001),
                -0.002 + np.random.normal(0, 0.001),
                0.0015 + np.random.normal(0, 0.001)
            )
        )

        mag_sample = MagSample(
            timestamp_ns=1000000000 + i * 10000000,
            magnetic_field_ut=(
                20.0 + np.random.normal(0, 0.1),
                0.0 + np.random.normal(0, 0.1),
                40.0 + np.random.normal(0, 0.1)
            )
        )

        imu_status = imu_monitor2.update_imu(imu_sample)
        mag_status = mag_monitor2.update_mag(mag_sample)

        health_statuses_imu2.append(imu_status)
        health_statuses_mag2.append(mag_status)

    # Compare health statuses
    for i in range(len(health_statuses_imu)):
        s1 = health_statuses_imu[i]
        s2 = health_statuses_imu2[i]

        assert s1.is_healthy == s2.is_healthy
        assert s1.issues == s2.issues
        # Metrics should be very close (allowing for small floating point differences)
        for key in s1.metrics:
            assert abs(s1.metrics[key] - s2.metrics[key]) < 1e-10

    for i in range(len(health_statuses_mag)):
        s1 = health_statuses_mag[i]
        s2 = health_statuses_mag2[i]

        assert s1.is_healthy == s2.is_healthy
        assert s1.issues == s2.issues
        for key in s1.metrics:
            assert abs(s1.metrics[key] - s2.metrics[key]) < 1e-10


def test_calibration_persistence_roundtrip():
    """Test that calibration persistence maintains deterministic values."""
    # Set random seed
    np.random.seed(42)

    # Create a calibration profile with known values
    from core.calibration.bias_calibration import AccelBias, GyroBias, StaticCalibrationResult
    from core.calibration.mag_calibration import MagCalibrationResult

    accel_result = StaticCalibrationResult(
        accel_bias=AccelBias(0.01, -0.02, 0.005),
        gyro_bias=GyroBias(0.001, -0.0005, 0.002),
        num_samples=100,
        accel_std=(0.001, 0.001, 0.001),
        gyro_std=(0.0001, 0.0001, 0.0001),
        is_valid=True
    )

    mag_result = MagCalibrationResult(
        hard_iron=(1.0, -0.5, 0.2),
        soft_iron=np.array([[1.1, 0.0, 0.0], [0.0, 0.9, 0.0], [0.0, 0.0, 1.0]]),
        radius=1.0,
        field_rmse=0.01,
        is_valid=True,
        num_samples=200
    )

    from core.calibration.persistence import create_profile_from_results
    profile = create_profile_from_results(
        accel_result=accel_result,
        mag_result=mag_result
    )

    # Save and load
    import tempfile
    import os
    with tempfile.TemporaryDirectory() as tmpdir:
        persistence = CalibrationPersistence(tmpdir)
        saved_path = persistence.save_profile(profile, "test_profile.json")

        # Load it back
        loaded_profile = persistence.load_profile(saved_path)

        # Values should be identical
        assert loaded_profile.version == profile.version
        assert loaded_profile.timestamp_ns == profile.timestamp_ns

        if loaded_profile.accelerometer and profile.accelerometer:
            assert loaded_profile.accelerometer.accel_bias.as_tuple() == \
                   profile.accelerometer.accel_bias.as_tuple()
            assert loaded_profile.accelerometer.gyro_bias.as_tuple() == \
                   profile.accelerometer.gyro_bias.as_tuple()
            assert loaded_profile.accelerometer.num_samples == \
                   profile.accelerometer.num_samples

        if loaded_profile.magnetometer and profile.magnetometer:
            assert loaded_profile.magnetometer.hard_iron == profile.magnetometer.hard_iron
            np.testing.assert_array_almost_equal(
                loaded_profile.magnetometer.soft_iron,
                profile.magnetometer.soft_iron,
                decimal=10
            )
            assert loaded_profile.magnetometer.radius == profile.magnetometer.radius
            assert loaded_profile.magnetometer.field_rmse == profile.magnetometer.field_rmse
            assert loaded_profile.magnetometer.num_samples == profile.magnetometer.num_samples


if __name__ == "__main__":
    # Run the tests
    test_deterministic_imu_calibration()
    print("✓ Deterministic IMU calibration test passed")

    test_deterministic_mag_calibration()
    print("✓ Deterministic magnetometer calibration test passed")

    test_pipeline_deterministic_replay()
    print("✓ Pipeline deterministic replay test passed")

    test_health_monitor_deterministic()
    print("✓ Health monitor deterministic test passed")

    test_calibration_persistence_roundtrip()
    print("✓ Calibration persistence roundtrip test passed")

    print("\nAll deterministic replay verification tests passed! 🎉")