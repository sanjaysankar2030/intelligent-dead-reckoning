"""
Simple magnetometer calibration for hard iron effects only.
NumPy-free version for compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Optional
import math

from ..sensors.data_types import MagSample


@dataclass
class MagCalibrationResult:
    """Result of magnetometer calibration."""
    hard_iron: Tuple[float, float, float]  # Bias offset (ux, uy, uz) in uT
    soft_iron: Tuple[Tuple[float, float, float],
                     Tuple[float, float, float],
                     Tuple[float, float, float]]  # 3x3 transformation matrix as tuples
    radius: float  # Fitted sphere radius in uT
    field_rmse: float  # Root mean square error of fit
    is_valid: bool
    error_message: Optional[str] = None
    num_samples: int = 0


class MagCalibrator:
    """
    Simple magnetometer calibration for hard iron effects only.
    Estimates bias as the average of min and max values in each axis.
    """

    def __init__(self, min_samples: int = 100):
        """
        Args:
            min_samples: Minimum samples required for calibration
        """
        self.min_samples = min_samples
        self.samples: List[Tuple[float, float, float]] = []  # List of (x, y, z) measurements
        self._min_vals = [float('inf'), float('inf'), float('inf')]
        self._max_vals = [float('-inf'), float('-inf'), float('-inf')]

    def add_sample(self, mag_sample: MagSample) -> None:
        """Add a magnetometer sample to the calibration dataset."""
        sample_tuple = (
            mag_sample.magnetic_field_ut[0],
            mag_sample.magnetic_field_ut[1],
            mag_sample.magnetic_field_ut[2]
        )
        self.samples.append(sample_tuple)

        # Update min/max for hard iron estimation
        for i in range(3):
            if sample_tuple[i] < self._min_vals[i]:
                self._min_vals[i] = sample_tuple[i]
            if sample_tuple[i] > self._max_vals[i]:
                self._max_vals[i] = sample_tuple[i]

    def get_calibration(self) -> MagCalibrationResult:
        """
        Calculate hard iron bias as average of min and max values.
        Soft iron is set to identity (no correction).

        Returns:
            MagCalibrationResult with hard iron estimate and identity soft iron
        """
        if len(self.samples) < self.min_samples:
            return MagCalibrationResult(
                hard_iron=(0.0, 0.0, 0.0),
                soft_iron=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
                radius=0.0,
                field_rmse=0.0,
                is_valid=False,
                error_message=f"Insufficient samples: {len(self.samples)} < {self.min_samples}",
                num_samples=len(self.samples)
            )

        if len(self.samples) < 2:
            return MagCalibrationResult(
                hard_iron=(0.0, 0.0, 0.0),
                soft_iron=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
                radius=0.0,
                field_rmse=0.0,
                is_valid=False,
                error_message=f"Need at least 2 samples for hard iron estimation, got {len(self.samples)}",
                num_samples=len(self.samples)
            )

        try:
            # Hard iron bias: average of min and max for each axis
            hard_iron = [
                (self._min_vals[0] + self._max_vals[0]) / 2.0,
                (self._min_vals[1] + self._max_vals[1]) / 2.0,
                (self._min_vals[2] + self._max_vals[2]) / 2.0
            ]

            # Soft iron: identity matrix (no correction for simple version)
            soft_iron = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))

            # Estimate radius as average distance from hard iron center
            total_distance = 0.0
            for sample in self.samples:
                dx = sample[0] - hard_iron[0]
                dy = sample[1] - hard_iron[1]
                dz = sample[2] - hard_iron[2]
                distance = math.sqrt(dx*dx + dy*dy + dz*dz)
                total_distance += distance

            radius = total_distance / len(self.samples) if self.samples else 0.0

            # Calculate RMSE: how much distances vary from the mean radius
            total_squared_error = 0.0
            for sample in self.samples:
                dx = sample[0] - hard_iron[0]
                dy = sample[1] - hard_iron[1]
                dz = sample[2] - hard_iron[2]
                distance = math.sqrt(dx*dx + dy*dy + dz*dz)
                error = distance - radius
                total_squared_error += error * error

            rmse = math.sqrt(total_squared_error / len(self.samples)) if self.samples else 0.0

            # Validate result
            is_valid = True
            error_message = None

            # Check for reasonable values
            if any(abs(x) > 1000 for x in hard_iron):  # More than 1000 uT bias is unreasonable
                is_valid = False
                error_message = "Hard iron bias too large"

            return MagCalibrationResult(
                hard_iron=tuple(hard_iron),
                soft_iron=soft_iron,
                radius=radius,
                field_rmse=rmse,
                is_valid=is_valid,
                error_message=error_message,
                num_samples=len(self.samples)
            )

        except Exception as e:
            return MagCalibrationResult(
                hard_iron=(0.0, 0.0, 0.0),
                soft_iron=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
                radius=0.0,
                field_rmse=0.0,
                is_valid=False,
                error_message=f"Calibration failed: {str(e)}",
                num_samples=len(self.samples)
            )

    def apply_calibration(self, mag_sample: MagSample,
                         calibration: MagCalibrationResult) -> MagSample:
        """
        Apply calibration to a magnetometer sample.

        Args:
            mag_sample: Raw magnetometer sample
            calibration: Calibration result from get_calibration()

        Returns:
            Calibrated magnetometer sample
        """
        if not calibration.is_valid:
            return mag_sample  # Return uncalibrated if calibration invalid

        # Apply hard iron subtraction
        corrected_x = mag_sample.magnetic_field_ut[0] - calibration.hard_iron[0]
        corrected_y = mag_sample.magnetic_field_ut[1] - calibration.hard_iron[1]
        corrected_z = mag_sample.magnetic_field_ut[2] - calibration.hard_iron[2]

        # Apply soft iron transformation (identity for simple version)
        calibrated_x = corrected_x * calibration.soft_iron[0][0] + corrected_y * calibration.soft_iron[0][1] + corrected_z * calibration.soft_iron[0][2]
        calibrated_y = corrected_x * calibration.soft_iron[1][0] + corrected_y * calibration.soft_iron[1][1] + corrected_z * calibration.soft_iron[1][2]
        calibrated_z = corrected_x * calibration.soft_iron[2][0] + corrected_y * calibration.soft_iron[2][1] + corrected_z * calibration.soft_iron[2][2]

        return MagSample(
            timestamp_ns=mag_sample.timestamp_ns,
            magnetic_field_ut=(calibrated_x, calibrated_y, calibrated_z)
        )

    def reset(self) -> None:
        """Reset the calibrator to initial state."""
        self.samples.clear()
        self._min_vals = [float('inf'), float('inf'), float('inf')]
        self._max_vals = [float('-inf'), float('-inf'), float('-inf')]

    def get_sample_count(self) -> int:
        """Get number of samples added to calibration."""
        return len(self.samples)


def create_test_data() -> List[MagSample]:
    """Create test magnetometer data with known hard iron effects."""
    import time

    # True magnetic field (approx 45 uT in various directions)
    base_time = time.time_ns()

    samples = []

    # Generate samples in different orientations with known hard iron
    true_field_magnitude = 45.0  # uT
    hard_iron_true = (5.0, -3.0, 2.0)  # uT

    for i in range(200):
        # Generate uniformly distributed directions on sphere
        # Using spherical coordinates
        phi = math.acos(2 * (i % 100) / 99.0 - 1.0)  # [0, pi]
        theta = 2.0 * math.pi * (i % 50) / 49.0     # [0, 2pi]

        # Unit vector in this direction
        field_dir_x = math.sin(phi) * math.cos(theta)
        field_dir_y = math.sin(phi) * math.sin(theta)
        field_dir_z = math.cos(phi)

        # True field in this direction
        true_field_x = true_field_magnitude * field_dir_x
        true_field_y = true_field_magnitude * field_dir_y
        true_field_z = true_field_magnitude * field_dir_z

        # Apply hard iron bias
        biased_x = true_field_x + hard_iron_true[0]
        biased_y = true_field_y + hard_iron_true[1]
        biased_z = true_field_z + hard_iron_true[2]

        # Add small noise
        noise = 0.1
        noisy_x = biased_x + ( (i % 17) - 8 ) * noise / 8.0
        noisy_y = biased_y + ( (i % 23) - 11 ) * noise / 11.0
        noisy_z = biased_z + ( (i % 29) - 14 ) * noise / 14.5

        samples.append(MagSample(
            timestamp_ns=base_time + i * 1000000,  # 1ms apart
            magnetic_field_ut=(noisy_x, noisy_y, noisy_z)
        ))

    return samples


if __name__ == "__main__":
    # Simple test
    calibrator = MagCalibrator(min_samples=20)
    test_data = create_test_data()

    for sample in test_data:
        calibrator.add_sample(sample)

    result = calibrator.get_calibration()
    print(f"Calibration result: {result}")
    print(f"Hard iron: {result.hard_iron}")
    print(f"Soft iron: {result.soft_iron}")
    print(f"Radius: {result.radius}")
    print(f"RMSE: {result.field_rmse}")
    print(f"Valid: {result.is_valid}")

    # Test applying calibration
    if result.is_valid:
        test_sample = test_data[0]
        calibrated = calibrator.apply_calibration(test_sample, result)
        print(f"\nSample: {test_sample.magnetic_field_ut}")
        print(f"Calibrated: {calibrated.magnetic_field_ut}")