"""
Gravity-based tilt (roll/pitch) alignment estimator.

Estimates the orientation of the phone relative to the local gravity vector
during static or quasi-static conditions. This constrains two of three
rotation degrees of freedom (roll and pitch), leaving heading (yaw)
unconstrained.

The gravity vector in the phone frame reveals the phone's tilt:
    a_phone ≈ R_vehicle^phone @ [0, 0, g]^T   (vehicle Z is down)

From the measured gravity direction in phone frame, we extract:
    pitch = atan2(-a_x, sqrt(a_y² + a_z²))
    roll  = atan2(a_y, a_z)

These angles describe how the phone is tilted relative to the vehicle's
level plane, independent of the phone's heading orientation.

No assumption is made about a fixed mounting orientation.
"""

from __future__ import annotations

import math
from collections import deque
from typing import Deque, Optional, Tuple

import numpy as np

from ..sensors.data_types import ImuSample
from .frames import AlignmentState
from .quaternion_utils import Quat, quat_from_euler, quat_normalize


# Standard gravity magnitude
GRAVITY_MAGNITUDE = 9.80665  # m/s²


class GravityAligner:
    """Estimates roll and pitch from the accelerometer gravity vector.

    During static conditions the accelerometer measures only gravity (plus noise).
    By averaging over a window of samples and checking that conditions are
    sufficiently static, we obtain a reliable tilt estimate.

    The output is a partial rotation (roll, pitch) that orients the phone's
    tilt relative to the gravity (down) direction. Heading (yaw) remains
    unobservable from gravity alone.
    """

    def __init__(
        self,
        window_size: int = 50,
        max_accel_deviation: float = 1.0,
        max_gyro_magnitude: float = 0.15,
        min_samples: int = 20,
    ):
        """
        Args:
            window_size: Number of samples to average over.
            max_accel_deviation: Maximum allowed deviation of accel magnitude
                from gravity (m/s²) for a sample to be considered static.
            max_gyro_magnitude: Maximum allowed gyro magnitude (rad/s) for
                a sample to be considered static.
            min_samples: Minimum number of valid static samples before
                producing an estimate.
        """
        self.window_size = window_size
        self.max_accel_deviation = max_accel_deviation
        self.max_gyro_magnitude = max_gyro_magnitude
        self.min_samples = min_samples

        self._accel_window: Deque[np.ndarray] = deque(maxlen=window_size)
        self._valid_count = 0

        # Current estimate
        self._roll: float = 0.0
        self._pitch: float = 0.0
        self._confidence: float = 0.0
        self._is_valid: bool = False

    def add_sample(self, sample: ImuSample) -> bool:
        """Add an IMU sample and update the gravity estimate.

        Args:
            sample: IMU sample.

        Returns:
            True if the sample was accepted as static, False otherwise.
        """
        accel = np.array(sample.accel_m_s2)
        gyro = np.array(sample.gyro_rad_s)

        # Check static conditions
        accel_mag = float(np.linalg.norm(accel))
        accel_dev = abs(accel_mag - GRAVITY_MAGNITUDE)
        gyro_mag = float(np.linalg.norm(gyro))

        is_static = bool(
            accel_dev <= self.max_accel_deviation
            and gyro_mag <= self.max_gyro_magnitude
        )

        if not is_static:
            return False

        self._accel_window.append(accel)
        self._valid_count = len(self._accel_window)

        if self._valid_count >= self.min_samples:
            self._update_estimate()

        return True

    def _update_estimate(self) -> None:
        """Recompute roll/pitch from the averaged gravity vector."""
        accel_array = np.array(list(self._accel_window))
        mean_accel = np.mean(accel_array, axis=0)

        # Gravity direction in phone frame (accelerometer measures -g when stationary
        # because it measures the reaction force, but Android sensors report the
        # specific force which equals +g in the upward direction when stationary).
        #
        # For a phone lying screen-up on a table (Android convention):
        #   accel ≈ [0, 0, +9.81]  (Z points out of screen, gravity reaction is upward)
        #
        # The gravity vector (downward) in phone frame is therefore:
        #   g_phone = -mean_accel / ||mean_accel|| * g  (pointing down)
        #
        # But for tilt angles, we just need the normalized direction:
        #   gravity_dir = mean_accel / ||mean_accel||
        #
        # In the Vehicle frame (FRD), gravity points in +Z direction: [0, 0, +g].
        # The phone measures acceleration ≈ [0, 0, +g] when Z_phone is up (anti-gravity).
        # So the "up" direction in phone frame is: mean_accel / ||mean_accel||
        # And the "down" direction is: -mean_accel / ||mean_accel||

        accel_norm = float(np.linalg.norm(mean_accel))
        if accel_norm < 1e-6:
            return

        # Normalize to get the direction the accelerometer points (upward/anti-gravity)
        ax, ay, az = mean_accel[0] / accel_norm, mean_accel[1] / accel_norm, mean_accel[2] / accel_norm

        # Extract tilt angles.
        # We want the rotation that maps the Vehicle down-axis [0,0,1] to the
        # phone's down direction. The phone's down direction is -[ax, ay, az].
        # Equivalently, the phone's "up" direction [ax, ay, az] should map to [0,0,-1].
        #
        # Using the standard aerospace decomposition for the gravity vector
        # measured in the body frame:
        #   pitch = atan2(-g_x, sqrt(g_y² + g_z²))
        #   roll  = atan2(g_y, g_z)
        # where g = [g_x, g_y, g_z] is the measured acceleration (anti-gravity, upward).

        self._pitch = math.atan2(-ax, math.sqrt(ay**2 + az**2))
        self._roll = math.atan2(ay, az)

        # Confidence based on:
        # 1. How close accel magnitude is to gravity
        # 2. How many samples we have
        # 3. Variance of the measurements
        accel_std = float(np.std(np.linalg.norm(accel_array, axis=1)))
        mag_error = abs(accel_norm - GRAVITY_MAGNITUDE)

        sample_factor = min(1.0, self._valid_count / max(1, self.window_size))
        mag_factor = max(0.0, 1.0 - mag_error / GRAVITY_MAGNITUDE)
        noise_factor = max(0.0, 1.0 - accel_std / 0.5)

        self._confidence = sample_factor * mag_factor * noise_factor
        self._is_valid = True

    @property
    def is_valid(self) -> bool:
        """Whether a valid gravity estimate is available."""
        return self._is_valid

    @property
    def roll(self) -> float:
        """Estimated roll in radians."""
        return self._roll

    @property
    def pitch(self) -> float:
        """Estimated pitch in radians."""
        return self._pitch

    @property
    def confidence(self) -> float:
        """Gravity alignment confidence in [0, 1]."""
        return self._confidence

    def get_tilt_quaternion(self, yaw: float = 0.0) -> Quat:
        """Get quaternion representing current tilt estimate.

        Returns a rotation quaternion from vehicle frame to phone frame,
        with the specified yaw (defaults to 0, since gravity cannot constrain yaw).

        Args:
            yaw: Heading offset in radians (default 0).

        Returns:
            Quaternion (w, x, y, z) representing R_vehicle^phone.
        """
        return quat_from_euler(self._roll, self._pitch, yaw)

    def get_gravity_direction_phone(self) -> np.ndarray:
        """Get the estimated gravity direction in the phone frame.

        Returns:
            Unit vector pointing in the gravity (down) direction as measured
            in the phone coordinate frame.
        """
        if not self._is_valid or self._valid_count == 0:
            return np.array([0.0, 0.0, -1.0])

        accel_array = np.array(list(self._accel_window))
        mean_accel = np.mean(accel_array, axis=0)
        accel_norm = np.linalg.norm(mean_accel)
        if accel_norm < 1e-6:
            return np.array([0.0, 0.0, -1.0])

        # The measured acceleration points "up" (anti-gravity).
        # The gravity direction (down) is the opposite.
        return -mean_accel / accel_norm

    def reset(self) -> None:
        """Reset to uninitialized state."""
        self._accel_window.clear()
        self._valid_count = 0
        self._roll = 0.0
        self._pitch = 0.0
        self._confidence = 0.0
        self._is_valid = False
