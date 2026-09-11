"""
Sensor data pipeline adapter.
Enforces the data flow: Raw Sensor -> Calibration Engine -> Corrected Sensor -> Navigation Filter.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional, Tuple

import numpy as np

from ..sensors.data_types import ImuSample, MagSample
from .bias_calibration import StaticCalibrationResult, StaticImuCalibrator
from .mag_calibration import MagCalibrationResult, MagCalibrator
from .persistence import CalibrationProfile, CalibrationPersistence


@dataclass
class PipelineStep:
    """Represents a step in the sensor data pipeline."""
    name: str
    enabled: bool = True
    process_func: Optional[Callable] = None


class SensorDataPipeline:
    """
    Manages the sensor data processing pipeline ensuring proper flow:
    Raw Sensor -> Calibration Engine -> Corrected Sensor -> Navigation Filter

    The pipeline applies calibration corrections in the correct order and
    maintains calibration state between processing steps.
    """

    def __init__(self,
                 imu_calibrator: Optional[StaticImuCalibrator] = None,
                 mag_calibrator: Optional[MagCalibrator] = None,
                 persistence: Optional[CalibrationPersistence] = None):
        """
        Initialize the sensor data pipeline.

        Args:
            imu_calibrator: IMU bias calibrator (if None, creates default)
            mag_calibrator: Magnetometer calibrator (if None, creates default)
            persistence: Persistence handler for calibration profiles
        """
        self.imu_calibrator = imu_calibrator or StaticImuCalibrator()
        self.mag_calibrator = mag_calibrator or MagCalibrator()
        self.persistence = persistence or CalibrationPersistence()

        # Current calibration results (None if not calibrated)
        self.imu_calibration_result: Optional[StaticCalibrationResult] = None
        self.mag_calibration_result: Optional[MagCalibrationResult] = None

        # Pipeline steps
        self.steps = [
            PipelineStep("imu_calibration", True, self._apply_imu_calibration),
            PipelineStep("mag_calibration", True, self._apply_mag_calibration),
        ]

        # Statistics
        self.samples_processed = 0
        self.calibration_samples_collected = 0

    def add_imu_sample(self, sample: ImuSample) -> Tuple[bool, Optional[ImuSample]]:
        """
        Add an IMU sample to the pipeline.

        Returns:
            Tuple of (sample_accepted_for_calibration, calibrated_sample)
            - sample_accepted_for_calibration: True if sample was static and added to calibration dataset
            - calibrated_sample: Calibrated sample if calibration is valid, None otherwise
        """
        # Add to IMU calibrator for bias estimation
        accepted = self.imu_calibrator.add_sample(sample)
        if accepted:
            self.calibration_samples_collected += 1

        # Apply current calibration if available
        calibrated_sample = None
        if self.imu_calibration_result and self.imu_calibration_result.is_valid:
            calibrated_sample = self._apply_imu_calibration(sample)

        self.samples_processed += 1
        return accepted, calibrated_sample

    def add_mag_sample(self, sample: MagSample) -> Tuple[bool, Optional[MagSample]]:
        """
        Add a magnetometer sample to the pipeline.

        Returns:
            Tuple of (sample_accepted_for_calibration, calibrated_sample)
            - sample_accepted_for_calibration: True if sample was added to calibration dataset
            - calibrated_sample: Calibrated sample if calibration is valid, None otherwise
        """
        # Add to magnetometer calibrator for bias estimation
        self.mag_calibrator.add_sample(sample)
        self.calibration_samples_collected += 1

        # Apply current calibration if available
        calibrated_sample = None
        if self.mag_calibration_result and self.mag_calibration_result.is_valid:
            calibrated_sample = self._apply_mag_calibration(sample)

        self.samples_processed += 1
        return True, calibrated_sample

    def update_calibration(self) -> bool:
        """
        Update calibration results from collected samples.

        Returns:
            True if calibration was updated successfully, False otherwise
        """
        updated = False

        # Update IMU calibration
        imu_result = self.imu_calibrator.get_calibration()
        if imu_result.is_valid and (self.imu_calibration_result is None or
                                    not self.imu_calibration_result.is_valid or
                                    imu_result.num_samples > self.imu_calibration_result.num_samples):
            self.imu_calibration_result = imu_result
            updated = True

        # Update magnetometer calibration
        mag_result = self.mag_calibrator.get_calibration()
        if mag_result.is_valid and (self.mag_calibration_result is None or
                                    not self.mag_calibration_result.is_valid or
                                    mag_result.num_samples > self.mag_calibration_result.num_samples):
            self.mag_calibration_result = mag_result
            updated = True

        return updated

    def save_calibration(self, filename: Optional[str] = None) -> Optional[str]:
        """
        Save current calibration to persistent storage.

        Args:
            filename: Optional filename for the calibration profile

        Returns:
            Path to saved file if successful, None otherwise
        """
        if not self.is_calibrated():
            return None

        profile = CalibrationProfile(
            accelerometer=self.imu_calibration_result,
            gyroscope=self.imu_calibration_result,  # Same result for both in current implementation
            magnetometer=self.mag_calibration_result,
            timestamp_ns=int(np.datetime64('now').astype('datetime64[ns]').astype(int))
        )

        try:
            saved_path = self.persistence.save_profile(profile, filename)
            return str(saved_path)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return None

    def load_calibration(self, filepath: str) -> bool:
        """
        Load calibration from persistent storage.

        Args:
            filepath: Path to calibration file

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            profile = self.persistence.load_profile(filepath)
            self.imu_calibration_result = profile.accelerometer
            self.mag_calibration_result = profile.magnetometer
            return True
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False

    def is_calibrated(self) -> bool:
        """
        Check if pipeline has valid calibration results.

        Returns:
            True if both IMU and magnetometer have valid calibration, False otherwise
        """
        imu_valid = (self.imu_calibration_result is not None and
                    self.imu_calibration_result.is_valid)
        mag_valid = (self.mag_calibration_result is not None and
                    self.mag_calibration_result.is_valid)
        return imu_valid and mag_valid

    def get_calibration_quality(self) -> dict:
        """
        Get calibration quality metrics.

        Returns:
            Dictionary containing calibration quality information
        """
        return {
            'imu_calibrated': self.imu_calibration_result is not None and self.imu_calibration_result.is_valid,
            'mag_calibrated': self.mag_calibration_result is not None and self.mag_calibration_result.is_valid,
            'imu_samples': self.imu_calibration_result.num_samples if self.imu_calibration_result else 0,
            'mag_samples': self.mag_calibration_result.num_samples if self.mag_calibration_result else 0,
            'imu_accel_bias': self.imu_calibration_result.accel_bias.as_tuple() if (self.imu_calibration_result and self.imu_calibration_result.is_valid) else None,
            'imu_gyro_bias': self.imu_calibration_result.gyro_bias.as_tuple() if (self.imu_calibration_result and self.imu_calibration_result.is_valid) else None,
            'mag_hard_iron': self.mag_calibration_result.hard_iron if (self.mag_calibration_result and self.mag_calibration_result.is_valid) else None,
            'mag_field_rmse': self.mag_calibration_result.field_rmse if (self.mag_calibration_result and self.mag_calibration_result.is_valid) else None,
            'pipeline_samples_processed': self.samples_processed,
            'calibration_samples_collected': self.calibration_samples_collected
        }

    def reset(self) -> None:
        """Reset the pipeline to initial state."""
        self.imu_calibrator.reset()
        self.mag_calibrator.reset()
        self.imu_calibration_result = None
        self.mag_calibration_result = None
        self.samples_processed = 0
        self.calibration_samples_collected = 0

    # Private methods for applying calibration
    def _apply_imu_calibration(self, sample: ImuSample) -> ImuSample:
        """Apply IMU bias correction to a sample."""
        if not self.imu_calibration_result or not self.imu_calibration_result.is_valid:
            return sample

        # Apply accelerometer bias correction
        corrected_accel = (
            sample.accel_m_s2[0] - self.imu_calibration_result.accel_bias.x,
            sample.accel_m_s2[1] - self.imu_calibration_result.accel_bias.y,
            sample.accel_m_s2[2] - self.imu_calibration_result.accel_bias.z
        )

        # Apply gyroscope bias correction
        corrected_gyro = (
            sample.gyro_rad_s[0] - self.imu_calibration_result.gyro_bias.x,
            sample.gyro_rad_s[1] - self.imu_calibration_result.gyro_bias.y,
            sample.gyro_rad_s[2] - self.imu_calibration_result.gyro_bias.z
        )

        return ImuSample(
            timestamp_ns=sample.timestamp_ns,
            accel_m_s2=corrected_accel,
            gyro_rad_s=corrected_gyro
        )

    def _apply_mag_calibration(self, sample: MagSample) -> MagSample:
        """Apply magnetometer calibration to a sample."""
        if not self.mag_calibration_result or not self.mag_calibration_result.is_valid:
            return sample

        # Apply magnetometer calibration using the calibrator's apply_calibration method
        return self.mag_calibrator.apply_calibration(sample, self.mag_calibration_result)