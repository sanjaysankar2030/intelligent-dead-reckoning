"""
Timestamp synchronization and ring buffer for multi-sensor streams.

Provides:
- Thread-safe ring buffer for each sensor type
- Time-synchronized snapshot generation via interpolation
- Support for arbitrary sensor rates
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Generic, List, Optional, Tuple, TypeVar

from .data_types import (
    BaroSample,
    GnssFix,
    ImuSample,
    MagSample,
    SensorSample,
    SensorType,
    Timestamp,
    lin_interp,
    slerp,
)

T = TypeVar("T", bound=SensorSample)


@dataclass(frozen=True)
class SensorSnapshot:
    """Time-synchronized snapshot of all available sensor data.

    Attributes:
        timestamp_ns: The reference timestamp for the snapshot (nanoseconds).
        imu: IMU sample at timestamp_ns (may be interpolated).
        gnss: GNSS fix at timestamp_ns (may be interpolated, or None if no fix within window).
        mag: Magnetometer sample at timestamp_ns (may be interpolated).
        baro: Barometer sample at timestamp_ns (may be interpolated).
    """
    timestamp_ns: Timestamp
    imu: ImuSample
    gnss: Optional[GnssFix]
    mag: MagSample
    baro: BaroSample


class RingBuffer(Generic[T]):
    """Thread-safe fixed-size ring buffer for time-ordered sensor samples.

    Assumes samples are inserted in increasing timestamp order.
    """

    def __init__(self, capacity: int = 1000):
        """Initialize ring buffer.

        Args:
            capacity: Maximum number of samples to store.
        """
        self._capacity = capacity
        self._buffer: Deque[T] = deque(maxlen=capacity)
        self._lock = threading.RLock()

    def append(self, sample: T) -> None:
        """Append a new sample to the buffer.

        Args:
            sample: Sensor sample to add. Must have a timestamp_ns attribute.
        """
        with self._lock:
            self._buffer.append(sample)

    def get_latest(self) -> Optional[T]:
        """Get the most recent sample.

        Returns:
            The latest sample, or None if buffer is empty.
        """
        with self._lock:
            if not self._buffer:
                return None
            return self._buffer[-1]

    def get_window(
        self, start_time: Timestamp, end_time: Timestamp
    ) -> List[T]:
        """Get all samples within a time window [start_time, end_time].

        Args:
            start_time: Inclusive start timestamp (nanoseconds).
            end_time: Inclusive end timestamp (nanoseconds).

        Returns:
            List of samples in chronological order.
        """
        with self._lock:
            # Since deque is ordered by insertion time (timestamp), we can iterate
            return [s for s in self._buffer if start_time <= s.timestamp_ns <= end_time]

    def find_closest(
        self, target_time: Timestamp
    ) -> Tuple[Optional[T], Optional[T]]:
        """Find the two samples that bracket the target time.

        Returns:
            (left, right) where left.timestamp_ns <= target_time <= right.timestamp_ns.
            If target_time is before all samples, left is None.
            If target_time is after all samples, right is None.
            If buffer is empty, both are None.
        """
        with self._lock:
            if not self._buffer:
                return None, None

            # Convert to list for indexing (deque doesn't support efficient indexing)
            # But we can iterate from both ends since data is ordered.
            # For simplicity, we convert to list (buffer size is limited).
            buf = list(self._buffer)
            left: Optional[T] = None
            right: Optional[T] = None

            for sample in buf:
                if sample.timestamp_ns <= target_time:
                    left = sample
                if sample.timestamp_ns >= target_time and right is None:
                    right = sample
                    break  # Found the first sample at or after target_time

            return left, right

    def __len__(self) -> int:
        with self._lock:
            return len(self._buffer)

    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()


class Synchronizer:
    """Time-synchronizes multiple sensor streams using linear/spherical interpolation.

    Each sensor type has its own ring buffer. The synchronizer provides a method
    to get a snapshot at a specific timestamp by interpolating each stream to that time.
    """

    def __init__(
        self,
        imu_buffer_size: int = 1000,
        gnss_buffer_size: int = 100,
        mag_buffer_size: int = 500,
        baro_buffer_size: int = 200,
        max_interpolation_age_s: float = 0.1,
    ):
        """Initialize synchronizer.

        Args:
            *_buffer_size: Capacity for each sensor's ring buffer.
            max_interpolation_age_s: Maximum age (in seconds) of data to use for interpolation.
                                     Older data is considered stale and will result in None.
        """
        self._buffers: Dict[SensorType, RingBuffer] = {
            SensorType.ACCELEROMETER: RingBuffer(imu_buffer_size),  # Actually IMU
            SensorType.GYROSCOPE: RingBuffer(imu_buffer_size),      # Same buffer as accel
            SensorType.GNSS: RingBuffer(gnss_buffer_size),
            SensorType.MAGNETOMETER: RingBuffer(mag_buffer_size),
            SensorType.BAROMETER: RingBuffer(baro_buffer_size),
        }
        # Note: We use one buffer for both accel and gyro since they come together in ImuSample.
        # We'll split them when providing the snapshot.

        self._max_interpolation_age_ns = int(max_interpolation_age_s * 1e9)
        self._lock = threading.RLock()

    def imu_buffer(self) -> RingBuffer[ImuSample]:
        """Get the IMU buffer (shared by accel and gyro)."""
        return self._buffers[SensorType.ACCELEROMETER]  # Reusing the accel buffer for IMU

    def gnss_buffer(self) -> RingBuffer[GnssFix]:
        return self._buffers[SensorType.GNSS]

    def mag_buffer(self) -> RingBuffer[MagSample]:
        return self._buffers[SensorType.MAGNETOMETER]

    def baro_buffer(self) -> RingBuffer[BaroSample]:
        return self._buffers[SensorType.BAROMETER]

    def add_imu(self, sample: ImuSample) -> None:
        """Add an IMU sample."""
        self.imu_buffer().append(sample)

    def add_gnss(self, sample: GnssFix) -> None:
        """Add a GNSS fix."""
        self.gnss_buffer().append(sample)

    def add_mag(self, sample: MagSample) -> None:
        """Add a magnetometer sample."""
        self.mag_buffer().append(sample)

    def add_baro(self, sample: BaroSample) -> None:
        """Add a barometer sample."""
        self.baro_buffer().append(sample)

    def _interpolate_imu(
        self, buffer: RingBuffer[ImuSample], target_time: Timestamp
    ) -> Optional[ImuSample]:
        """Interpolate IMU data to target_time.

        Returns None if no data within max_interpolation_age_ns.
        """
        left, right = buffer.find_closest(target_time)
        now = time.time_ns()

        # Check if we have recent data
        if right is not None and (now - right.timestamp_ns) > self._max_interpolation_age_ns:
            return None  # Data too old

        if left is None and right is None:
            return None  # No data

        if left is None:
            # Target is before first sample -> use first sample (or None if too old?)
            # For simplicity, we return the first sample if it's not too old.
            if (now - right.timestamp_ns) <= self._max_interpolation_age_ns:
                return right
            return None

        if right is None:
            # Target is after last sample -> use last sample
            if (now - left.timestamp_ns) <= self._max_interpolation_age_ns:
                return left
            return None

        # Both left and right exist -> interpolate
        left_time = left.timestamp_ns
        right_time = right.timestamp_ns
        if left_time == right_time:
            return left  # Avoid division by zero

        # Interpolate acceleration
        accel_x = lin_interp(
            target_time, left_time, right_time, left.accel_m_s2[0], right.accel_m_s2[0]
        )
        accel_y = lin_interp(
            target_time, left_time, right_time, left.accel_m_s2[1], right.accel_m_s2[1]
        )
        accel_z = lin_interp(
            target_time, left_time, right_time, left.accel_m_s2[2], right.accel_m_s2[2]
        )
        # Interpolate gyroscope
        gyro_x = lin_interp(
            target_time, left_time, right_time, left.gyro_rad_s[0], right.gyro_rad_s[0]
        )
        gyro_y = lin_interp(
            target_time, left_time, right_time, left.gyro_rad_s[1], right.gyro_rad_s[1]
        )
        gyro_z = lin_interp(
            target_time, left_time, right_time, left.gyro_rad_s[2], right.gyro_rad_s[2]
        )

        return ImuSample(
            timestamp_ns=target_time,
            accel_m_s2=(accel_x, accel_y, accel_z),
            gyro_rad_s=(gyro_x, gyro_y, gyro_z),
        )

    def _interpolate_gnss(
        self, buffer: RingBuffer[GnssFix], target_time: Timestamp
    ) -> Optional[GnssFix]:
        """Interpolate GNSS data to target_time.

        Note: Latitude/longitude/altitude are interpolated linearly.
        Velocity is interpolated linearly.
        This is a simplification; for rigorous applications, one should convert to ECEF.
        """
        left, right = buffer.find_closest(target_time)
        now = time.time_ns()

        if right is not None and (now - right.timestamp_ns) > self._max_interpolation_age_ns:
            return None  # Data too old

        if left is None and right is None:
            return None

        if left is None:
            if (now - right.timestamp_ns) <= self._max_interpolation_age_ns:
                return right
            return None

        if right is None:
            if (now - left.timestamp_ns) <= self._max_interpolation_age_ns:
                return left
            return None

        # Both exist -> interpolate
        left_time = left.timestamp_ns
        right_time = right.timestamp_ns
        if left_time == right_time:
            return left

        # Interpolate each component
        latitude = lin_interp(
            target_time, left_time, right_time, left.latitude_deg, right.latitude_deg
        )
        longitude = lin_interp(
            target_time, left_time, right_time, left.longitude_deg, right.longitude_deg
        )
        altitude = lin_interp(
            target_time, left_time, right_time, left.altitude_m, right.altitude_m
        )
        velocity_north = lin_interp(
            target_time,
            left_time,
            right_time,
            left.velocity_ned_mps[0],
            right.velocity_ned_mps[0],
        )
        velocity_east = lin_interp(
            target_time,
            left_time,
            right_time,
            left.velocity_ned_mps[1],
            right.velocity_ned_mps[1],
        )
        velocity_down = lin_interp(
            target_time,
            left_time,
            right_time,
            left.velocity_ned_mps[2],
            right.velocity_ned_mps[2],
        )
        # For accuracy values, we could interpolate or take the worse (max). We'll interpolate.
        horiz_acc = lin_interp(
            target_time,
            left_time,
            right_time,
            left.horizontal_accuracy_m,
            right.horizontal_accuracy_m,
        )
        vert_acc = lin_interp(
            target_time,
            left_time,
            right_time,
            left.vertical_accuracy_m,
            right.vertical_accuracy_m,
        )
        speed_acc = lin_interp(
            target_time,
            left_time,
            right_time,
            left.speed_accuracy_mps,
            right.speed_accuracy_mps,
        )
        sat_count = int(
            lin_interp(
                target_time, left_time, right_time, left.satellite_count, right.satellite_count
            )
        )

        return GnssFix(
            timestamp_ns=target_time,
            latitude_deg=latitude,
            longitude_deg=longitude,
            altitude_m=altitude,
            velocity_ned_mps=(velocity_north, velocity_east, velocity_down),
            horizontal_accuracy_m=horiz_acc,
            vertical_accuracy_m=vert_acc,
            speed_accuracy_mps=speed_acc,
            satellite_count=sat_count,
        )

    def _interpolate_mag(
        self, buffer: RingBuffer[MagSample], target_time: Timestamp
    ) -> Optional[MagSample]:
        """Interpolate magnetometer data to target_time."""
        left, right = buffer.find_closest(target_time)
        now = time.time_ns()

        if right is not None and (now - right.timestamp_ns) > self._max_interpolation_age_ns:
            return None

        if left is None and right is None:
            return None

        if left is None:
            if (now - right.timestamp_ns) <= self._max_interpolation_age_ns:
                return right
            return None

        if right is None:
            if (now - left.timestamp_ns) <= self._max_interpolation_age_ns:
                return left
            return None

        left_time = left.timestamp_ns
        right_time = right.timestamp_ns
        if left_time == right_time:
            return left

        # Linear interpolation for each component
        mx = lin_interp(
            target_time, left_time, right_time, left.magnetic_field_ut[0], right.magnetic_field_ut[0]
        )
        my = lin_interp(
            target_time, left_time, right_time, left.magnetic_field_ut[1], right.magnetic_field_ut[1]
        )
        mz = lin_interp(
            target_time, left_time, right_time, left.magnetic_field_ut[2], right.magnetic_field_ut[2]
        )

        return MagSample(
            timestamp_ns=target_time,
            magnetic_field_ut=(mx, my, mz),
        )

    def _interpolate_baro(
        self, buffer: RingBuffer[BaroSample], target_time: Timestamp
    ) -> Optional[BaroSample]:
        """Interpolate barometer data to target_time."""
        left, right = buffer.find_closest(target_time)
        now = time.time_ns()

        if right is not None and (now - right.timestamp_ns) > self._max_interpolation_age_ns:
            return None

        if left is None and right is None:
            return None

        if left is None:
            if (now - right.timestamp_ns) <= self._max_interpolation_age_ns:
                return right
            return None

        if right is None:
            if (now - left.timestamp_ns) <= self._max_interpolation_age_ns:
                return left
            return None

        left_time = left.timestamp_ns
        right_time = right.timestamp_ns
        if left_time == right_time:
            return left

        pressure = lin_interp(
            target_time, left_time, right_time, left.pressure_pa, right.pressure_pa
        )

        return BaroSample(
            timestamp_ns=target_time,
            pressure_pa=pressure,
        )

    def get_snapshot(self, timestamp_ns: Timestamp) -> Optional[SensorSnapshot]:
        """Get a time-synchronized snapshot of all sensor data at timestamp_ns.

        Each sensor stream is interpolated to the target timestamp.
        If any required stream is too stale (or missing), returns None.

        Args:
            timestamp_ns: Target timestamp in nanoseconds.

        Returns:
            SensorSnapshot containing interpolated data for all streams,
            or None if any stream is unavailable or too stale.
        """
        imu = self._interpolate_imu(self.imu_buffer(), timestamp_ns)
        gnss = self._interpolate_gnss(self.gnss_buffer(), timestamp_ns)
        mag = self._interpolate_mag(self.mag_buffer(), timestamp_ns)
        baro = self._interpolate_baro(self.baro_buffer(), timestamp_ns)

        # IMU, mag, and baro are considered required for basic operation.
        # GNSS can be None (indicating outage).
        if imu is None or mag is None or baro is None:
            return None

        return SensorSnapshot(
            timestamp_ns=timestamp_ns,
            imu=imu,
            gnss=gnss,  # May be None
            mag=mag,
            baro=baro,
        )

    def get_latest_snapshot(self) -> Optional[SensorSnapshot]:
        """Get a snapshot using the latest available timestamp from any sensor.

        Uses the most recent timestamp among all sensors as the reference.
        """
        latest_time: Optional[Timestamp] = None
        for buffer in self._buffers.values():
            latest_sample = buffer.get_latest()
            if latest_sample is not None:
                if latest_time is None or latest_sample.timestamp_ns > latest_time:
                    latest_time = latest_sample.timestamp_ns

        if latest_time is None:
            return None  # No data at all

        return self.get_snapshot(latest_time)

    def clear_all(self) -> None:
        """Clear all buffers."""
        for buffer in self._buffers.values():
            buffer.clear()