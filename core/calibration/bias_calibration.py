"""
Static bias calibration for accelerometers and gyroscopes.

During stationary periods, the accelerometer should measure only gravity,
and the gyroscope should measure near-zero angular velocity.
Any deviation from these expected values represents sensor bias.
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from typing import List, Optional, Tuple

from ..sensors.data_types import ImuSample


@dataclass
class AccelBias:
    """Accelerometer bias in m/s^2."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def as_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def __sub__(self, other: "AccelBias") -> "AccelBias":
        return AccelBias(self.x - other.x, self.y - other.y, self.z - other.z)

    def __add__(self, other: "AccelBias") -> "AccelBias":
        return AccelBias(self.x + other.x, self.y + other.y, self.z + other.z)


@dataclass
class GyroBias:
    """Gyroscope bias in rad/s."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def as_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def __sub__(self, other: "GyroBias") -> "GyroBias":
        return GyroBias(self.x - other.x, self.y - other.y, self.z - other.z)

    def __add__(self, other: "GyroBias") -> "GyroBias":
        return GyroBias(self.x + other.x, self.y + other.y, self.z + other.z)


@dataclass
class StaticCalibrationResult:
    """Result of static calibration procedure."""
    accel_bias: AccelBias
    gyro_bias: GyroBias
    num_samples: int
    accel_std: Tuple[float, float, float]  # Standard deviation of measurements
    gyro_std: Tuple[float, float, float]  # Standard deviation of measurements
    is_valid: bool
    error_message: Optional[str] = None


class StaticImuCalibrator:
    """Estimates IMU biases from stationary data."""

    def __init__(
        self,
        gravity_magnitude: float = 9.80665,
        max_accel_deviation: float = 2.0,  # m/s^2
        max_gyro_deviation: float = 0.5,   # rad/s
        min_samples: int = 100,
        variance_threshold: float = 0.01   # Max allowed variance for valid calibration
    ):
        """
        Args:
            gravity_magnitude: Expected gravity magnitude in m/s^2
            max_accel_deviation: Maximum allowed deviation from gravity for valid static sample
            max_gyro_deviation: Maximum allowed gyro magnitude for valid static sample
            min_samples: Minimum number of samples required for calibration
            variance_threshold: Maximum allowed variance in each axis for valid calibration
        """
        self.gravity_magnitude = gravity_magnitude
        self.max_accel_deviation = max_accel_deviation
        self.max_gyro_deviation = max_gyro_deviation
        self.min_samples = min_samples
        self.variance_threshold = variance_threshold

        # Running statistics for incremental calculation
        self._accel_sum = np.zeros(3)
        self._accel_sum_sq = np.zeros(3)
        self._gyro_sum = np.zeros(3)
        self._gyro_sum_sq = np.zeros(3)
        self._count = 0

    def add_sample(self, imu_sample: ImuSample) -> bool:
        """
        Add a sample to the calibration dataset if it appears to be from static conditions.

        Args:
            imu_sample: IMU sample to potentially include in calibration

        Returns:
            True if sample was added (passed staticness checks), False otherwise
        """
        # Check if accelerometer measures approximately gravity only
        accel = np.array(imu_sample.accel_m_s2)
        accel_magnitude = np.linalg.norm(accel)
        accel_deviation = abs(accel_magnitude - self.gravity_magnitude)

        # Check if gyroscope measures near-zero angular velocity
        gyro = np.array(imu_sample.gyro_rad_s)
        gyro_magnitude = np.linalg.norm(gyro)

        # Static conditions: accel ~ gravity, gyro ~ zero
        is_static = bool(
            (accel_deviation <= self.max_accel_deviation) and
            (gyro_magnitude <= self.max_gyro_deviation)
        )

        if is_static:
            # Update running statistics
            self._accel_sum += accel
            self._accel_sum_sq += accel * accel
            self._gyro_sum += gyro
            self._gyro_sum_sq += gyro * gyro
            self._count += 1

        return is_static

    def get_calibration(self) -> StaticCalibrationResult:
        """
        Calculate bias estimates from accumulated samples.

        Returns:
            StaticCalibrationResult containing bias estimates and quality metrics
        """
        if self._count < self.min_samples:
            return StaticCalibrationResult(
                accel_bias=AccelBias(),
                gyro_bias=GyroBias(),
                num_samples=self._count,
                accel_std=(0.0, 0.0, 0.0),
                gyro_std=(0.0, 0.0, 0.0),
                is_valid=False,
                error_message=f"Insufficient samples: {self._count} < {self.min_samples}"
            )

        # Calculate means
        accel_mean = self._accel_sum / self._count
        gyro_mean = self._gyro_sum / self._count

        # Calculate variances
        accel_var = (self._accel_sum_sq / self._count) - (accel_mean * accel_mean)
        gyro_var = (self._gyro_sum_sq / self._count) - (gyro_mean * gyro_mean)

        # Check for numerical issues that could cause negative variances
        accel_var = np.maximum(accel_var, 0.0)
        gyro_var = np.maximum(gyro_var, 0.0)

        accel_std = np.sqrt(accel_var)
        gyro_std = np.sqrt(gyro_var)

        # Check if variance is too high (indicating non-static conditions or noisy sensor)
        is_valid = bool(np.all(accel_std <= self.variance_threshold) and np.all(gyro_std <= self.variance_threshold))

        # Accelerometer bias: measured - expected gravity in down direction
        # We assume the device is stationary with Z-axis pointing down
        # In a more sophisticated implementation, we'd estimate the gravity vector direction
        expected_accel = np.array([0.0, 0.0, self.gravity_magnitude])  # Assuming Z-down
        accel_bias_raw = accel_mean - expected_accel

        # Gyroscope bias: measured - expected (zero)
        gyro_bias_raw = gyro_mean  # Expected is zero

        return StaticCalibrationResult(
            accel_bias=AccelBias(
                x=float(accel_bias_raw[0]),
                y=float(accel_bias_raw[1]),
                z=float(accel_bias_raw[2])
            ),
            gyro_bias=GyroBias(
                x=float(gyro_bias_raw[0]),
                y=float(gyro_bias_raw[1]),
                z=float(gyro_bias_raw[2])
            ),
            num_samples=self._count,
            accel_std=tuple(float(x) for x in accel_std),
            gyro_std=tuple(float(x) for x in gyro_std),
            is_valid=is_valid,
            error_message=None if is_valid else "Variance too high - sensor may not be static"
        )

    def reset(self) -> None:
        """Reset the calibrator to initial state."""
        self._accel_sum = np.zeros(3)
        self._accel_sum_sq = np.zeros(3)
        self._gyro_sum = np.zeros(3)
        self._gyro_sum_sq = np.zeros(3)
        self._count = 0

    def get_sample_count(self) -> int:
        """Get number of samples added to calibration."""
        return self._count


def calibrate_accelerometer_gravity_vector(
    accel_samples: List[Tuple[float, float, float]]
) -> Tuple[np.ndarray, float]:
    """
    Estimate accelerometer bias and gravity vector from multiple stationary orientations.

    This function uses multiple stationary orientations to solve for both
    the accelerometer bias and the gravity vector direction simultaneously.

    Args:
        accel_samples: List of accelerometer measurements from different stationary orientations

    Returns:
        Tuple of (bias_vector, gravity_magnitude_estimate)
    """
    if len(accel_samples) < 6:
        raise ValueError("Need at least 6 samples from different orientations for vector calibration")

    # Build linear system: accel_measured = bias + gravity_true
    # For N samples: [accel1]   [1 0 0 0 0 1]   [bx]
    #                [accel2] = [0 1 0 0 0 1] * [by]
    #                ...        [0 0 1 0 0 1]   [bz]
    #                               [0 0 0 1 0 0]   [gx]
    #                               [0 0 0 0 1 0]   [gy]
    #                               [0 0 0 0 0 1]   [gz]
    #
    # Actually: accel_measured = bias + R^T * g_true
    # For static case, R^T * g_true is just the gravity vector in sensor frame
    # So: accel_measured = bias + gravity_in_sensor_frame
    #
    # We can solve for bias and gravity direction by noting that
    # ||gravity_in_sensor_frame|| should be constant

    # For simplicity in this implementation, we'll use the average method
    # A more sophisticated approach would use SVD or nonlinear optimization
    samples = np.array(accel_samples)
    mean_accel = np.mean(samples, axis=0)

    # Assume gravity is primarily in Z direction (can be improved)
    # Bias = mean_accel - [0, 0, gravity]
    # We don't know gravity magnitude exactly, so we estimate it from the data
    # The gravity vector magnitude should be consistent across samples
    magnitudes = np.linalg.norm(samples, axis=1)
    gravity_estimate = np.mean(magnitudes)

    # Assume Z-down orientation for bias calculation
    expected_gravity = np.array([0.0, 0.0, gravity_estimate])
    bias = mean_accel - expected_gravity

    return bias, gravity_estimate


# Example usage and testing functions
def create_test_data() -> List[ImuSample]:
    """Create test IMU data with known biases."""
    import time

    true_accel_bias = (0.05, -0.02, 0.03)  # m/s^2
    true_gyro_bias = (0.001, -0.002, 0.0015)  # rad/s

    samples = []
    base_time = time.time_ns()

    for i in range(200):
        # Simulate stationary IMU readings
        accel = (
            true_accel_bias[0] + np.random.normal(0, 0.01),  # x
            true_accel_bias[1] + np.random.normal(0, 0.01),  # y
            true_accel_bias[2] + 9.80665 + np.random.normal(0, 0.01)  # Z with gravity
        )
        gyro = (
            true_gyro_bias[0] + np.random.normal(0, 0.001),
            true_gyro_bias[1] + np.random.normal(0, 0.001),
            true_gyro_bias[2] + np.random.normal(0, 0.001)
        )

        samples.append(ImuSample(
            timestamp_ns=base_time + i * 10000000,  # 10ms apart
            accel_m_s2=accel,
            gyro_rad_s=gyro
        ))

    return samples


if __name__ == "__main__":
    # Simple test
    calibrator = StaticImuCalibrator(min_samples=50)
    test_data = create_test_data()

    for sample in test_data:
        calibrator.add_sample(sample)

    result = calibrator.get_calibration()
    print(f"Calibration result: {result}")
    print(f"Accel bias: {result.accel_bias.as_tuple()}")
    print(f"Gyro bias: {result.gyro_bias.as_tuple()}")
    print(f"Valid: {result.is_valid}")