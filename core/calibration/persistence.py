"""
Calibration profile persistence module.
Handles saving and loading calibration parameters to/from disk.
Supports JSON and YAML formats with versioning.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np

from .bias_calibration import StaticCalibrationResult
from .mag_calibration import MagCalibrationResult


@dataclass
class CalibrationProfile:
    """Complete calibration profile for all sensors."""
    version: str = "1.0"
    accelerometer: Optional[StaticCalibrationResult] = None
    gyroscope: Optional[StaticCalibrationResult] = None
    magnetometer: Optional[MagCalibrationResult] = None
    timestamp_ns: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        # Convert numpy arrays to lists for JSON serialization
        if self.accelerometer is not None:
            data['accelerometer']['accel_bias'] = asdict(self.accelerometer.accel_bias)
            data['accelerometer']['gyro_bias'] = asdict(self.accelerometer.gyro_bias)
        if self.gyroscope is not None:
            data['gyroscope']['accel_bias'] = asdict(self.gyroscope.accel_bias)
            data['gyroscope']['gyro_bias'] = asdict(self.gyroscope.gyro_bias)
        if self.magnetometer is not None:
            data['magnetometer']['hard_iron'] = list(self.magnetometer.hard_iron)
            data['magnetometer']['soft_iron'] = self.magnetometer.soft_iron.tolist()
            data['magnetometer']['radius'] = float(self.magnetometer.radius)
            data['magnetometer']['field_rmse'] = float(self.magnetometer.field_rmse)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CalibrationProfile':
        """Create from dictionary."""
        # Handle numpy array conversion
        if data.get('magnetometer') and data['magnetometer'].get('soft_iron'):
            data['magnetometer']['soft_iron'] = np.array(data['magnetometer']['soft_iron'])

        # Handle nested dataclasses
        if data.get('accelerometer'):
            accel_data = data['accelerometer']
            if accel_data.get('accel_bias'):
                from .bias_calibration import AccelBias
                accel_data['accel_bias'] = AccelBias(**accel_data['accel_bias'])
            if accel_data.get('gyro_bias'):
                from .bias_calibration import GyroBias
                accel_data['gyro_bias'] = GyroBias(**accel_data['gyro_bias'])
            from .bias_calibration import StaticCalibrationResult
            data['accelerometer'] = StaticCalibrationResult(**accel_data)

        if data.get('gyroscope'):
            gyro_data = data['gyroscope']
            if gyro_data.get('accel_bias'):
                from .bias_calibration import AccelBias
                gyro_data['accel_bias'] = AccelBias(**gyro_data['accel_bias'])
            if gyro_data.get('gyro_bias'):
                from .bias_calibration import GyroBias
                gyro_data['gyro_bias'] = GyroBias(**gyro_data['gyro_bias'])
            from .bias_calibration import StaticCalibrationResult
            data['gyroscope'] = StaticCalibrationResult(**gyro_data)

        if data.get('magnetometer'):
            mag_data = data['magnetometer']
            if 'hard_iron' in mag_data and isinstance(mag_data['hard_iron'], list):
                mag_data['hard_iron'] = tuple(mag_data['hard_iron'])
            from .mag_calibration import MagCalibrationResult
            data['magnetometer'] = MagCalibrationResult(**mag_data)

        return cls(**data)


class CalibrationPersistence:
    """Handles persistence of calibration profiles."""

    def __init__(self, storage_dir: Optional[Union[str, Path]] = None):
        """
        Initialize persistence handler.

        Args:
            storage_dir: Directory to store calibration profiles.
                        Defaults to ~/.dead_reckoning/calibration/
        """
        if storage_dir is None:
            storage_dir = Path.home() / ".dead_reckoning" / "calibration"
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save_profile(self, profile: CalibrationProfile,
                    filename: Optional[str] = None) -> Path:
        """
        Save calibration profile to disk.

        Args:
            profile: CalibrationProfile to save
            filename: Optional filename. If not provided, uses timestamp.

        Returns:
            Path to saved file
        """
        if filename is None:
            timestamp = profile.timestamp_ns or np.datetime64('now').astype('datetime64[ns]').astype(int)
            filename = f"calibration_{timestamp}.json"

        # If filename is an absolute path, use it directly, else prepend storage_dir
        if Path(filename).is_absolute():
            filepath = Path(filename)
        else:
            filepath = self.storage_dir / filename

        # Update timestamp if not set
        if profile.timestamp_ns == 0:
            profile.timestamp_ns = np.datetime64('now').astype('datetime64[ns]').astype(int)

        # Save as JSON
        with open(filepath, 'w') as f:
            json.dump(profile.to_dict(), f, indent=2)

        return filepath

    def load_profile(self, filepath: Union[str, Path]) -> CalibrationProfile:
        """
        Load calibration profile from disk.

        Args:
            filepath: Path to calibration file

        Returns:
            Loaded CalibrationProfile
        """
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"Calibration file not found: {filepath}")

        with open(filepath, 'r') as f:
            data = json.load(f)

        return CalibrationProfile.from_dict(data)

    def list_profiles(self) -> list[Path]:
        """
        List all calibration profiles in storage directory.

        Returns:
            List of profile file paths sorted by modification time (newest first)
        """
        profiles = list(self.storage_dir.glob("calibration_*.json"))
        return sorted(profiles, key=lambda p: p.stat().st_mtime, reverse=True)

    def delete_profile(self, filepath: Union[str, Path]) -> bool:
        """
        Delete a calibration profile.

        Args:
            filepath: Path to profile to delete

        Returns:
            True if deleted, False if not found
        """
        filepath = Path(filepath)
        if filepath.exists():
            filepath.unlink()
            return True
        return False


def create_profile_from_results(
    accel_result: Optional[StaticCalibrationResult] = None,
    gyro_result: Optional[StaticCalibrationResult] = None,
    mag_result: Optional[MagCalibrationResult] = None
) -> CalibrationProfile:
    """
    Create a CalibrationProfile from individual calibration results.

    Args:
        accel_result: Accelerometer calibration result
        gyro_result: Gyroscope calibration result
        mag_result: Magnetometer calibration result

    Returns:
        CalibrationProfile containing all provided results
    """
    return CalibrationProfile(
        accelerometer=accel_result,
        gyroscope=gyro_result,
        magnetometer=mag_result,
        timestamp_ns=int(np.datetime64('now').astype('datetime64[ns]').astype(int))
    )


if __name__ == "__main__":
    # Simple test
    persistence = CalibrationPersistence("./test_calibration")

    # Create dummy results for testing
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
        soft_iron=np.eye(3),
        radius=1.0,
        field_rmse=0.01,
        is_valid=True,
        num_samples=200
    )

    profile = create_profile_from_results(
        accel_result=accel_result,
        mag_result=mag_result
    )

    # Save and load
    saved_path = persistence.save_profile(profile, "test_profile.json")
    print(f"Saved profile to: {saved_path}")

    loaded_profile = persistence.load_profile(saved_path)
    print(f"Loaded profile version: {loaded_profile.version}")
    print(f"Accel bias: {loaded_profile.accelerometer.accel_bias.as_tuple() if loaded_profile.accelerometer else None}")
    print(f"Mag hard iron: {loaded_profile.magnetometer.hard_iron if loaded_profile.magnetometer else None}")