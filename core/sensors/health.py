"""
Sensor health monitoring module.
Detects sensor issues like saturation, clipping, timestamp jitter, and variance anomalies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Deque, Optional, Tuple
from collections import deque
import numpy as np

from ..sensors.data_types import ImuSample, MagSample


@dataclass
class SensorHealthStatus:
    """Health status for a sensor."""
    timestamp_ns: int
    is_healthy: bool
    issues: list[str]
    metrics: dict[str, float]

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'timestamp_ns': self.timestamp_ns,
            'is_healthy': self.is_healthy,
            'issues': self.issues.copy(),
            'metrics': self.metrics.copy()
        }


class ImuHealthMonitor:
    """
    Monitors IMU (accelerometer and gyroscope) health.
    Detects saturation, clipping, excessive variance, and timestamp anomalies.
    """

    def __init__(self,
                 max_accel_magnitude: float = 50.0,  # m/s^2
                 max_gyro_magnitude: float = 50.0,   # rad/s
                 max_timestamp_jitter: float = 20_000_000,  # 20ms in ns
                 variance_window_size: int = 100,
                 max_variance_threshold: float = 10.0):  # m/s^2 or rad/s
        """
        Initialize IMU health monitor.

        Args:
            max_accel_magnitude: Maximum allowed accelerometer magnitude before saturation
            max_gyro_magnitude: Maximum allowed gyroscope magnitude before saturation
            max_timestamp_jitter: Maximum allowed timestamp jitter in nanoseconds
            variance_window_size: Window size for variance calculation
            max_variance_threshold: Maximum allowed variance in each axis
        """
        self.max_accel_magnitude = max_accel_magnitude
        self.max_gyro_magnitude = max_gyro_magnitude
        self.max_timestamp_jitter = max_timestamp_jitter
        self.variance_window_size = variance_window_size
        self.max_variance_threshold = max_variance_threshold

        # Data windows for variance calculation
        self.accel_window: Deque[Tuple[float, float, float]] = deque(maxlen=variance_window_size)
        self.gyro_window: Deque[Tuple[float, float, float]] = deque(maxlen=variance_window_size)
        self.timestamp_window: Deque[int] = deque(maxlen=variance_window_size)

        # Last timestamp for jitter detection
        self.last_timestamp: Optional[int] = None

    def update(self, sample: ImuSample) -> SensorHealthStatus:
        """
        Update health monitor with new IMU sample.

        Args:
            sample: IMU sample to analyze

        Returns:
            SensorHealthStatus with current health assessment
        """
        issues = []
        metrics = {}

        # Check for saturation/clipping
        accel_mag = np.sqrt(sample.accel_m_s2[0]**2 + sample.accel_m_s2[1]**2 + sample.accel_m_s2[2]**2)
        gyro_mag = np.sqrt(sample.gyro_rad_s[0]**2 + sample.gyro_rad_s[1]**2 + sample.gyro_rad_s[2]**2)

        if accel_mag > self.max_accel_magnitude:
            issues.append(f"accelerometer_saturation: {accel_mag:.2f} > {self.max_accel_magnitude} m/s^2")
        if gyro_mag > self.max_gyro_magnitude:
            issues.append(f"gyroscope_saturation: {gyro_mag:.2f} > {self.max_gyro_magnitude} rad/s")

        metrics['accel_magnitude'] = float(accel_mag)
        metrics['gyro_magnitude'] = float(gyro_mag)

        # Check timestamp jitter
        if self.last_timestamp is not None:
            jitter = abs(sample.timestamp_ns - self.last_timestamp - int(1e7))  # Expect 10ms intervals
            if jitter > self.max_timestamp_jitter:
                issues.append(f"timestamp_jitter: {jitter} ns > {self.max_timestamp_jitter} ns")
            metrics['timestamp_jitter_ns'] = float(jitter)
        else:
            metrics['timestamp_jitter_ns'] = 0.0

        self.last_timestamp = sample.timestamp_ns

        # Add to windows for variance calculation
        self.accel_window.append(sample.accel_m_s2)
        self.gyro_window.append(sample.gyro_rad_s)
        self.timestamp_window.append(sample.timestamp_ns)

        # Calculate variance if we have enough samples
        if len(self.accel_window) >= 10:  # Minimum for meaningful variance
            # Calculate variance for each axis
            accel_array = np.array(list(self.accel_window))
            gyro_array = np.array(list(self.gyro_window))

            accel_var = np.var(accel_array, axis=0)
            gyro_var = np.var(gyro_array, axis=0)

            metrics['accel_variance_x'] = float(accel_var[0])
            metrics['accel_variance_y'] = float(accel_var[1])
            metrics['accel_variance_z'] = float(accel_var[2])
            metrics['gyro_variance_x'] = float(gyro_var[0])
            metrics['gyro_variance_y'] = float(gyro_var[1])
            metrics['gyro_variance_z'] = float(gyro_var[2])

            # Check if variance exceeds threshold
            if np.any(accel_var > self.max_variance_threshold):
                issues.append(f"high_accelerometer_variance: max={np.max(accel_var):.4f}")
            if np.any(gyro_var > self.max_variance_threshold):
                issues.append(f"high_gyroscope_variance: max={np.max(gyro_var):.4f}")

        # Determine overall health
        is_healthy = len(issues) == 0

        return SensorHealthStatus(
            timestamp_ns=sample.timestamp_ns,
            is_healthy=is_healthy,
            issues=issues,
            metrics=metrics
        )


class MagHealthMonitor:
    """
    Monitors magnetometer health.
    Detects saturation, clipping, and excessive variance.
    """

    def __init__(self,
                 max_mag_magnitude: float = 100.0,  # uT
                 variance_window_size: int = 100,
                 max_variance_threshold: float = 50.0):  # uT^2
        """
        Initialize magnetometer health monitor.

        Args:
            max_mag_magnitude: Maximum allowed magnetometer magnitude before saturation
            variance_window_size: Window size for variance calculation
            max_variance_threshold: Maximum allowed variance in each axis
        """
        self.max_mag_magnitude = max_mag_magnitude
        self.variance_window_size = variance_window_size
        self.max_variance_threshold = max_variance_threshold

        # Data windows for variance calculation
        self.mag_window: Deque[Tuple[float, float, float]] = deque(maxlen=variance_window_size)
        self.timestamp_window: Deque[int] = deque(maxlen=variance_window_size)

        # Last timestamp for jitter detection
        self.last_timestamp: Optional[int] = None

    def update(self, sample: MagSample) -> SensorHealthStatus:
        """
        Update health monitor with new magnetometer sample.

        Args:
            sample: MagSample to analyze

        Returns:
            SensorHealthStatus with current health assessment
        """
        issues = []
        metrics = {}

        # Check for saturation/clipping
        mag_mag = np.sqrt(sample.magnetic_field_ut[0]**2 +
                         sample.magnetic_field_ut[1]**2 +
                         sample.magnetic_field_ut[2]**2)

        if mag_mag > self.max_mag_magnitude:
            issues.append(f"magnetometer_saturation: {mag_mag:.2f} > {self.max_mag_magnitude} uT")

        metrics['mag_magnitude'] = float(mag_mag)

        # Check timestamp jitter
        if self.last_timestamp is not None:
            jitter = abs(sample.timestamp_ns - self.last_timestamp - int(1e7))  # Expect 10ms intervals
            if jitter > 20_000_000:  # 20ms max jitter
                issues.append(f"timestamp_jitter: {jitter} ns > 20000000 ns")
            metrics['timestamp_jitter_ns'] = float(jitter)
        else:
            metrics['timestamp_jitter_ns'] = 0.0

        self.last_timestamp = sample.timestamp_ns

        # Add to windows for variance calculation
        self.mag_window.append(sample.magnetic_field_ut)
        self.timestamp_window.append(sample.timestamp_ns)

        # Calculate variance if we have enough samples
        if len(self.mag_window) >= 10:  # Minimum for meaningful variance
            mag_array = np.array(list(self.mag_window))
            mag_var = np.var(mag_array, axis=0)

            metrics['mag_variance_x'] = float(mag_var[0])
            metrics['mag_variance_y'] = float(mag_var[1])
            metrics['mag_variance_z'] = float(mag_var[2])

            # Check if variance exceeds threshold
            if np.any(mag_var > self.max_variance_threshold):
                issues.append(f"high_magnetometer_variance: max={np.max(mag_var):.4f}")

        # Determine overall health
        is_healthy = len(issues) == 0

        return SensorHealthStatus(
            timestamp_ns=sample.timestamp_ns,
            is_healthy=is_healthy,
            issues=issues,
            metrics=metrics
        )


class SensorHealthManager:
    """
    Manages health monitoring for all sensor types.
    """

    def __init__(self):
        """Initialize sensor health manager."""
        self.imu_monitor = ImuHealthMonitor()
        self.mag_monitor = MagHealthMonitor()
        self.health_history: Deque[SensorHealthStatus] = deque(maxlen=1000)

    def update_imu(self, sample: ImuSample) -> SensorHealthStatus:
        """
        Update IMU health monitor.

        Args:
            sample: IMU sample

        Returns:
            SensorHealthStatus for IMU
        """
        status = self.imu_monitor.update(sample)
        self.health_history.append(status)
        return status

    def update_mag(self, sample: MagSample) -> SensorHealthStatus:
        """
        Update magnetometer health monitor.

        Args:
            sample: MagSample

        Returns:
            SensorHealthStatus for magnetometer
        """
        status = self.mag_monitor.update(sample)
        self.health_history.append(status)
        return status

    def get_health_summary(self) -> dict:
        """
        Get summary of recent health status.

        Returns:
            Dictionary with health summary information
        """
        if not self.health_history:
            return {
                'overall_healthy': True,
                'recent_issues': [],
                'samples_monitored': 0
            }

        # Get recent statuses (last 100 samples)
        recent = list(self.health_history)[-100:] if len(self.health_history) >= 100 else list(self.health_history)

        # Count healthy vs unhealthy
        healthy_count = sum(1 for s in recent if s.is_healthy)
        total_count = len(recent)

        # Collect recent issues
        recent_issues = []
        for status in recent[-10:]:  # Last 10 samples
            if status.issues:
                recent_issues.extend([f"[{status.timestamp_ns}] {issue}" for issue in status.issues])

        return {
            'overall_healthy': healthy_count / total_count > 0.8 if total_count > 0 else True,
            'healthy_percentage': (healthy_count / total_count * 100) if total_count > 0 else 100.0,
            'recent_issues': recent_issues[-20:],  # Last 20 issues
            'samples_monitored': len(self.health_history)
        }

    def reset(self) -> None:
        """Reset all health monitors."""
        self.imu_monitor = ImuHealthMonitor()
        self.mag_monitor = MagHealthMonitor()
        self.health_history.clear()


if __name__ == "__main__":
    # Simple test
    import time
    from core.sensors.data_types import ImuSample, MagSample

    imu_monitor = ImuHealthMonitor()
    mag_monitor = MagHealthMonitor()

    # Test with normal samples
    normal_imu = ImuSample(
        timestamp_ns=time.time_ns(),
        accel_m_s2=(0.0, 0.0, 9.81),
        gyro_rad_s=(0.001, -0.002, 0.0015)
    )

    normal_mag = MagSample(
        timestamp_ns=time.time_ns(),
        magnetic_field_ut=(20.0, 0.0, 40.0)
    )

    imu_status = imu_monitor.update(normal_imu)
    mag_status = mag_monitor.update(normal_mag)

    print(f"IMU Healthy: {imu_status.is_healthy}, Issues: {imu_status.issues}")
    print(f"MAG Healthy: {mag_status.is_healthy}, Issues: {mag_status.issues}")

    # Test with saturated sample
    saturated_imu = ImuSample(
        timestamp_ns=time.time_ns(),
        accel_m_s2=(0.0, 0.0, 60.0),  # Above 50 m/s^2 threshold
        gyro_rad_s=(0.0, 0.0, 0.0)
    )

    saturated_status = imu_monitor.update(saturated_imu)
    print(f"Saturated IMU Healthy: {saturated_status.is_healthy}, Issues: {saturated_status.issues}")