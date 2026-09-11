"""
Magnetometer calibration for hard and soft iron effects.

Hard iron effects: Permanent magnetic bias (constant offset)
Soft iron effects: Magnetic field distortion (changes sensitivity and axes orthogonality)

Calibration fits measurements to an ellipsoid and transforms to a sphere.
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional

from ..sensors.data_types import MagSample


@dataclass
class MagCalibrationResult:
    """Result of magnetometer calibration."""
    hard_iron: Tuple[float, float, float]  # Bias offset (ux, uy, uz) in uT
    soft_iron: np.ndarray  # 3x3 transformation matrix
    radius: float  # Fitted sphere radius in uT
    field_rmse: float  # Root mean square error of fit
    is_valid: bool
    error_message: Optional[str] = None
    num_samples: int = 0


class MagCalibrator:
    """
    Magnetometer calibration using ellipsoid fitting.

    Collects magnetometer measurements and fits them to an ellipsoid model:
    (x - x0)^2/a^2 + (y - y0)^2/b^2 + (z - z0)^2/c^2 = 1

    Then transforms to sphere: X' = A * (X - x0)
    """

    def __init__(self, min_samples: int = 100):
        """
        Args:
            min_samples: Minimum samples required for calibration
        """
        self.min_samples = min_samples
        self.samples: List[np.ndarray] = []  # List of [x, y, z] measurements

    def add_sample(self, mag_sample: MagSample) -> None:
        """Add a magnetometer sample to the calibration dataset."""
        self.samples.append(np.array([
            mag_sample.magnetic_field_ut[0],
            mag_sample.magnetic_field_ut[1],
            mag_sample.magnetic_field_ut[2]
        ]))

    def get_calibration(self) -> MagCalibrationResult:
        """
        Perform ellipsoid fitting to calculate calibration parameters.

        Returns:
            MagCalibrationResult with hard iron, soft iron, and quality metrics
        """
        if len(self.samples) < self.min_samples:
            return MagCalibrationResult(
                hard_iron=(0.0, 0.0, 0.0),
                soft_iron=np.eye(3),
                radius=0.0,
                field_rmse=0.0,
                is_valid=False,
                error_message=f"Insufficient samples: {len(self.samples)} < {self.min_samples}",
                num_samples=len(self.samples)
            )

        if len(self.samples) < 6:
            return MagCalibrationResult(
                hard_iron=(0.0, 0.0, 0.0),
                soft_iron=np.eye(3),
                radius=0.0,
                field_rmse=0.0,
                is_valid=False,
                error_message=f"Need at least 6 samples for ellipsoid fitting, got {len(self.samples)}",
                num_samples=len(self.samples)
            )

        try:
            # Convert to numpy array for easier manipulation
            data = np.array(self.samples)  # Shape: (n_samples, 3)

            # Center the data to improve numerical conditioning
            # This helps eliminate linear terms in the ellipsoid equation
            mu = np.mean(data, axis=0)
            data_centered = data - mu

            # Build design matrix for ellipsoid fit using centered data
            # We fit: A*x^2 + B*y^2 + C*z^2 + 2D*xy + 2E*xz + 2F*yz + J = 0
            # (no linear terms since data is centered)
            D = np.column_stack([
                data_centered[:, 0]**2,        # x^2
                data_centered[:, 1]**2,        # y^2
                data_centered[:, 2]**2,        # z^2
                2 * data_centered[:, 0] * data_centered[:, 1],  # 2xy
                2 * data_centered[:, 0] * data_centered[:, 2],  # 2xz
                2 * data_centered[:, 1] * data_centered[:, 2],  # 2yz
                np.ones(len(data_centered))    # 1
            ])

            # Solve D * v = 0 where v = [A,B,C,D,E,F,G]^T
            # Using SVD for homogeneous system
            _, _, Vt = np.linalg.svd(D, full_matrices=False)
            v = Vt[-1, :]  # Last row corresponds to smallest singular value

            # Extract ellipsoid parameters for centered data
            # [A,B,C,D,E,F,G] where equation is: A*x^2 + B*y^2 + C*z^2 + 2D*xy + 2E*xz + 2F*yz + G = 0
            A, B, C, D, E, F, G = v

            # Construct the ellipsoid matrix for the quadratic form
            # [A   D   E]
            # [D   B   F] * [x y z]^2 + G = 0
            # [E   F   C]
            ellipsoid_matrix_centered = np.array([
                [A, D, E],
                [D, B, F],
                [E, F, C]
            ])

            # Check if we have a valid ellipsoid (matrix should be definite, i.e., all eigenvalues same sign and non-zero)
            try:
                eigvals = np.linalg.eigvals(ellipsoid_matrix_centered)
                # Check if all eigenvalues are positive (positive definite)
                if np.all(eigvals > 0):
                    pass  # Good, already positive definite
                # Check if all eigenvalues are negative (negative definite)
                elif np.all(eigvals < 0):
                    # Multiply by -1 to make positive definite
                    # Since if [A,B,C,D,E,F,G] is a solution, so is [-A,-B,-C,-D,-E,-F,-G]
                    A, B, C, D, E, F, G = -A, -B, -C, -D, -E, -F, -G
                    # Reconstruct the matrix with negated parameters
                    ellipsoid_matrix_centered = np.array([
                        [A, D, E],
                        [D, B, F],
                        [E, F, C]
                    ])
                    # Update eigenvalues (they should now be positive)
                    eigvals = -eigvals
                else:
                    # Eigenvalues have mixed signs or include zero - not definite
                    return MagCalibrationResult(
                        hard_iron=(0.0, 0.0, 0.0),
                        soft_iron=np.eye(3),
                        radius=0.0,
                        field_rmse=0.0,
                        is_valid=False,
                        error_message="Ellipsoid matrix not definite",
                        num_samples=len(self.samples)
                    )
            except np.linalg.LinAlgError:
                return MagCalibrationResult(
                    hard_iron=(0.0, 0.0, 0.0),
                    soft_iron=np.eye(3),
                    radius=0.0,
                    field_rmse=0.0,
                    is_valid=False,
                    error_message="Failed to compute eigenvalues",
                    num_samples=len(self.samples)
                )

            # Calculate center (hard iron bias)
            # For the centered data fit: x_c^T * A * x_c + G = 0 where x_c = x - mu
            # This is equivalent to: (x - mu)^T * A * (x - mu) + G = 0
            # Which is already in the form: (x - xc)^T * A * (x - xc) + G' = 0
            # with xc = mu and G' = G
            # Therefore, the center is simply mu!
            center = mu

            # Calculate transformation matrix for sphere fitting
            # We want: (x - center)^T * ellipsoid_matrix * (x - center) = 1
            # After translation: x'^T * ellipsoid_matrix * x' = 1 where x' = x - center
            # To make this a unit sphere: x'' = sqrt(ellipsoid_matrix) * x'
            # So the soft iron matrix is sqrt(ellipsoid_matrix)
            try:
                # Eigenvalue decomposition for matrix square root
                eigvals, eigvecs = np.linalg.eigh(ellipsoid_matrix_centered)
                # Ensure positive eigenvalues
                eigvals = np.maximum(eigvals, 1e-10)
                # Soft iron matrix: sqrt(ellipsoid_matrix)
                soft_iron = eigvecs @ np.diag(np.sqrt(eigvals)) @ eigvecs.T
            except np.linalg.LinAlgError:
                return MagCalibrationResult(
                    hard_iron=(0.0, 0.0, 0.0),
                    soft_iron=np.eye(3),
                    radius=0.0,
                    field_rmse=0.0,
                    is_valid=False,
                    error_message="Failed to compute soft iron matrix",
                    num_samples=len(self.samples)
                )

            # Calculate the radius and RMSE by transforming to normalized space
            try:
                # Transform all samples to normalized space
                # x' = x - center (centered data)
                centered = data - center.reshape(1, 3)
                # Apply the inverse of the soft iron transformation to get to unit sphere
                # Actually, soft_iron is sqrt(ellipsoid_matrix), so to normalize we need inv(sqrt(ellipsoid_matrix))
                # But we want: (x - center)^T * ellipsoid_matrix * (x - center) = radius^2
                # Let L = sqrt(ellipsoid_matrix), then we want: ||L*(x - center)||^2 = radius^2
                # So the normalized coordinates are: L*(x - center) / radius
                # And L*(x - center) should have norm radius
                transformed = (soft_iron @ centered.T).T  # Shape: (n_samples, 3)
                # For a perfect fit, all transformed points should lie on a sphere of radius 'radius'
                radii = np.linalg.norm(transformed, axis=1)
                radius = np.mean(radii)

                # Calculate RMSE
                rmse = np.sqrt(np.mean((radii - radius)**2))

                # Normalize the soft iron matrix so that radius = 1
                # This makes the interpretation easier: soft_iron transforms to unit sphere
                if radius > 0:
                    soft_iron = soft_iron / radius
                    radius = 1.0

            except Exception:
                # Fallback: use geometric mean of eigenvalues
                radius = np.prod(np.linalg.eigvals(ellipsoid_matrix_centered))**(-1/6)
                rmse = 0.0  # Unknown without detailed calculation

            # Validate result
            is_valid = True
            error_message = None

            # Check for reasonable values
            if np.any(np.abs(center) > 1000):  # More than 1000 uT bias is unreasonable
                is_valid = False
                error_message = "Hard iron bias too large"
            else:
                # Soft iron matrix is sqrt(ellipsoid), scaled so it maps to a unit sphere.
                # Its eigenvalues represent the scaling factors applied to each axis.
                # Extreme deformations (e.g. >10x scaling in one axis vs others) indicate failure.
                try:
                    soft_eigvals = np.linalg.eigvals(soft_iron)
                    # Use relative condition number rather than absolute value
                    cond_number = np.max(np.abs(soft_eigvals)) / (np.min(np.abs(soft_eigvals)) + 1e-10)
                    if cond_number > 20:  # Allow up to 20x stretching in one axis
                        is_valid = False
                        error_message = "Soft iron matrix indicates extreme distortion"
                except Exception:
                    pass

            return MagCalibrationResult(
                hard_iron=tuple(float(x) for x in center),
                soft_iron=soft_iron,
                radius=float(radius),
                field_rmse=float(rmse),
                is_valid=is_valid,
                error_message=error_message,
                num_samples=len(self.samples)
            )

        except Exception as e:
            return MagCalibrationResult(
                hard_iron=(0.0, 0.0, 0.0),
                soft_iron=np.eye(3),
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
        corrected = np.array([
            mag_sample.magnetic_field_ut[0] - calibration.hard_iron[0],
            mag_sample.magnetic_field_ut[1] - calibration.hard_iron[1],
            mag_sample.magnetic_field_ut[2] - calibration.hard_iron[2]
        ])

        # Apply soft iron transformation
        calibrated_vec = calibration.soft_iron @ corrected

        return MagSample(
            timestamp_ns=mag_sample.timestamp_ns,
            magnetic_field_ut=tuple(float(x) for x in calibrated_vec)
        )

    def reset(self) -> None:
        """Reset the calibrator to initial state."""
        self.samples.clear()

    def get_sample_count(self) -> int:
        """Get number of samples added to calibration."""
        return len(self.samples)


def create_test_data() -> List[MagSample]:
    """Create test magnetometer data with known hard and soft iron effects."""
    import time

    # True magnetic field (approx 45 uT in India, pointing down and north)
    true_field = np.array([20.0, 0.0, 40.0])  # uT

    # Hard iron bias (constant offset)
    hard_iron = np.array([5.0, -3.0, 2.0])  # uT

    # Soft iron matrix (distortion)
    # Create a simple scaling and rotation
    soft_iron = np.array([
        [1.2, 0.1, 0.0],
        [0.05, 0.9, 0.0],
        [0.0, 0.0, 1.1]
    ])

    samples = []
    base_time = time.time_ns()

    # Generate samples in different orientations
    for i in range(200):
        # Rotate the true field to simulate different orientations
        angle = 2 * np.pi * i / 200  # Full circle over all samples
        rot_z = np.array([
            [np.cos(angle), -np.sin(angle), 0],
            [np.sin(angle), np.cos(angle), 0],
            [0, 0, 1]
        ])

        # Apply rotation to true field
        rotated_field = rot_z @ true_field

        # Apply hard and soft iron effects
        distorted = soft_iron @ (rotated_field + hard_iron)

        # Add noise
        noisy = distorted + np.random.normal(0, 0.5, 3)

        samples.append(MagSample(
            timestamp_ns=base_time + i * 1000000,  # 1ms apart
            magnetic_field_ut=tuple(float(x) for x in noisy)
        ))

    return samples


if __name__ == "__main__":
    # Simple test
    calibrator = MagCalibrator(min_samples=50)
    test_data = create_test_data()

    for sample in test_data:
        calibrator.add_sample(sample)

    result = calibrator.get_calibration()
    print(f"Calibration result: {result}")
    print(f"Hard iron: {result.hard_iron}")
    print(f"Soft iron:\n{result.soft_iron}")
    print(f"Radius: {result.radius}")
    print(f"RMSE: {result.field_rmse}")
    print(f"Valid: {result.is_valid}")

    # Test applying calibration
    if result.is_valid:
        test_sample = test_data[0]
        calibrated = calibrator.apply_calibration(test_sample, result)
        print(f"\nSample: {test_sample.magnetic_field_ut}")
        print(f"Calibrated: {calibrated.magnetic_field_ut}")