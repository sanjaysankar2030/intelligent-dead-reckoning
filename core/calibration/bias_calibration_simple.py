"""
Static bias calibration for accelerometers and gyroscopes.
Estimates bias by assuming the mean acceleration vector points in the
direction of gravity.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import math

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
    orientation_error_deg: float = 0.0  # Error in gravity direction estimation


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
        self._accel_sum = [0.0, 0.0, 0.0]
        self._accel_sum_sq = [0.0, 0.0, 0.0]
        self._gyro_sum = [0.0, 0.0, 0.0]
        self._gyro_sum_sq = [0.0, 0.0, 0.0]
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
        accel = imu_sample.accel_m_s2
        accel_magnitude = (accel[0]**2 + accel[1]**2 + accel[2]**2)**0.5
        accel_deviation = abs(accel_magnitude - self.gravity_magnitude)

        # Check if gyroscope measures near-zero angular velocity
        gyro = imu_sample.gyro_rad_s
        gyro_magnitude = (gyro[0]**2 + gyro[1]**2 + gyro[2]**2)**0.5

        # Static conditions: accel ~ gravity, gyro ~ zero
        is_static = (
            accel_deviation <= self.max_accel_deviation and
            gyro_magnitude <= self.max_gyro_deviation
        )

        if is_static:
            # Update running statistics
            self._accel_sum[0] += accel[0]
            self._accel_sum[1] += accel[1]
            self._accel_sum[2] += accel[2]
            self._accel_sum_sq[0] += accel[0] * accel[0]
            self._accel_sum_sq[1] += accel[1] * accel[1]
            self._accel_sum_sq[2] += accel[2] * accel[2]
            self._gyro_sum[0] += gyro[0]
            self._gyro_sum[1] += gyro[1]
            self._gyro_sum[2] += gyro[2]
            self._gyro_sum_sq[0] += gyro[0] * gyro[0]
            self._gyro_sum_sq[1] += gyro[1] * gyro[1]
            self._gyro_sum_sq[2] += gyro[2] * gyro[2]
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
        accel_mean = [
            self._accel_sum[0] / self._count,
            self._accel_sum[1] / self._count,
            self._accel_sum[2] / self._count
        ]
        gyro_mean = [
            self._gyro_sum[0] / self._count,
            self._gyro_sum[1] / self._count,
            self._gyro_sum[2] / self._count
        ]

        # Calculate variances
        accel_var = [
            max(0.0, self._accel_sum_sq[0] / self._count - accel_mean[0] * accel_mean[0]),
            max(0.0, self._accel_sum_sq[1] / self._count - accel_mean[1] * accel_mean[1]),
            max(0.0, self._accel_sum_sq[2] / self._count - accel_mean[2] * accel_mean[2])
        ]
        gyro_var = [
            max(0.0, self._gyro_sum_sq[0] / self._count - gyro_mean[0] * gyro_mean[0]),
            max(0.0, self._gyro_sum_sq[1] / self._count - gyro_mean[1] * gyro_mean[1]),
            max(0.0, self._gyro_sum_sq[2] / self._count - gyro_mean[2] * gyro_mean[2])
        ]

        accel_std = [v**0.5 for v in accel_var]
        gyro_std = [v**0.5 for v in gyro_var]

        # Check if variance is too high (indicating non-static conditions or noisy sensor)
        is_valid = (
            accel_std[0] <= self.variance_threshold and
            accel_std[1] <= self.variance_threshold and
            accel_std[2] <= self.variance_threshold and
            gyro_std[0] <= self.variance_threshold and
            gyro_std[1] <= self.variance_threshold and
            gyro_std[2] <= self.variance_threshold
        )

        # Gyroscope bias: measured - expected (zero)
        gyro_bias_raw = gyro_mean  # Expected is zero

        # Accelerometer bias: we assume the device is stationary, so the accelerometer measures
        # gravity plus bias. We estimate the gravity direction from the mean accelerometer
        # vector and then scale it to the known gravity magnitude.
        accel_mag = (accel_mean[0]**2 + accel_mean[1]**2 + accel_mean[2]**2)**0.5
        if accel_mag > 0:
            accel_direction = [
                accel_mean[0] / accel_mag,
                accel_mean[1] / accel_mag,
                accel_mean[2] / accel_mag
            ]
            gravity_expected = [
                accel_direction[0] * self.gravity_magnitude,
                accel_direction[1] * self.gravity_magnitude,
                accel_direction[2] * self.gravity_magnitude
            ]
            accel_bias_raw = [
                accel_mean[0] - gravity_expected[0],
                accel_mean[1] - gravity_expected[1],
                accel_mean[2] - gravity_expected[2]
            ]
        else:
            # If the magnitude is zero, we cannot estimate direction, so we assume zero bias.
            accel_bias_raw = [0.0, 0.0, 0.0]

        # Calculate orientation error (how well the estimated gravity direction matches samples)
        # We compute the standard deviation of the magnitudes of the acceleration samples.
        # If the device is truly stationary, the magnitude should be constant (gravity magnitude).
        # Variation in magnitude indicates either noise or that our gravity direction estimate is off.
        if self._count > 0:
            # We would need to store all samples to compute this exactly.
            # For now, we set orientation_error_deg to 0 as a placeholder.
            orientation_error_deg = 0.0
        else:
            orientation_error_deg = 0.0

        return StaticCalibrationResult(
            accel_bias=AccelBias(
                x=accel_bias_raw[0],
                y=accel_bias_raw[1],
                z=accel_bias_raw[2]
            ),
            gyro_bias=GyroBias(
                x=gyro_bias_raw[0],
                y=gyro_bias_raw[1],
                z=gyro_bias_raw[2]
            ),
            num_samples=self._count,
            accel_std=(accel_std[0], accel_std[1], accel_std[2]),
            gyro_std=(gyro_std[0], gyro_std[1], gyro_std[2]),
            is_valid=is_valid,
            error_message=None if is_valid else "Variance too high - sensor may not be static",
            orientation_error_deg=orientation_error_deg
        )

    def reset(self) -> None:
        """Reset the calibrator to initial state."""
        self._accel_sum = [0.0, 0.0, 0.0]
        self._accel_sum_sq = [0.0, 0.0, 0.0]
        self._gyro_sum = [0.0, 0.0, 0.0]
        self._gyro_sum_sq = [0.0, 0.0, 0.0]
        self._count = 0

    def get_sample_count(self) -> int:
        """Get number of samples added to calibration."""
        return self._count