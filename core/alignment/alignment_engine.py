"""
Phone-to-vehicle alignment engine.

Combines gravity-based tilt estimation and heading estimation to produce
a complete phone-to-vehicle rotation estimate with confidence metrics
and reorientation detection.

Architecture:
    Raw IMU/Mag/GNSS -> [Gravity Aligner] + [Heading Estimator]
                              -> [Alignment Fusion] -> AlignmentStatus
                              -> [Reorientation Detection]

The alignment engine maintains the estimated phone-to-vehicle rotation
as a quaternion: q_phone^vehicle (rotates FROM phone frame TO vehicle frame).

Users can query:
- Current alignment state and confidence
- Estimated roll/pitch/yaw offsets
- Whether alignment is usable for navigation
- Reorientation/alignment-loss detection
"""

from __future__ import annotations

from collections import deque
import math
from typing import Deque, Optional, Tuple

import numpy as np

from ..sensors.data_types import GnssFix, ImuSample, MagSample
from .frames import AlignmentState, AlignmentStatus, VehicleType
from .gravity_alignment import GravityAligner
from .heading_estimator import HeadingEstimator
from .quaternion_utils import (
    Quat,
    quat_conjugate,
    quat_from_euler,
    quat_multiply,
    quat_normalize,
    quat_rotate_vector,
    wrap_angle,
)


class AlignmentEngine:
    """
    Estimates phone-to-vehicle alignment using multiple sensors.

    The alignment process:
    1. Gravity alignment: estimates roll and pitch from accelerometer during static periods
    2. Heading estimation: estimates yaw from GNSS velocity, vehicle dynamics, and weak magnetometer aid
    3. Fusion: combines tilt and heading into a complete rotation estimate
    4. Confidence: estimates reliability based on signal quality and consistency
    5. Reorientation detection: monitors for sudden changes inconsistent with vehicle motion

    The output quaternion q_phone^vehicle transforms vectors FROM phone frame TO vehicle frame:
        v_vehicle = q_phone^vehicle * v_phone * conj(q_phone^vehicle)

    For use in the navigation pipeline:
        v_navigation = R_vehicle^n * R_phone^vehicle * v_phone
                     = R_vehicle^n * [q_phone^vehicle] * v_phone
    """

    def __init__(
        self,
        vehicle_type: VehicleType = VehicleType.UNKNOWN,
        gravity_window_size: int = 50,
        gravity_min_samples: int = 20,
        heading_history_size: int = 50,
        reentry_deg_threshold: float = 15.0,  # degrees
        reentry_confidence_drop: float = 0.3,
        static_accel_threshold: float = 1.0,  # m/s² deviation from gravity
        static_gyro_threshold: float = 0.15,  # rad/s
        min_confidence_for_aligned: float = 0.6,
    ):
        """
        Args:
            vehicle_type: Type of vehicle for constraint tuning.
            gravity_window_size: Window size for gravity averaging.
            gravity_min_samples: Minimum static samples for gravity estimate.
            heading_history_size: History size for heading estimates.
            reentry_deg_threshold: Degrees change to trigger reorientation detection.
            reentry_confidence_drop: Confidence drop to trigger reentry detection.
            static_accel_threshold: Max accel deviation for static detection.
            static_gyro_threshold: Max gyro magnitude for static detection.
            min_confidence_for_aligned: Minimum confidence for FULLY_ALIGNED state.
        """
        self.vehicle_type = vehicle_type

        # Sub-estimators
        self._gravity_aligner = GravityAligner(
            window_size=gravity_window_size,
            max_accel_deviation=static_accel_threshold,
            max_gyro_magnitude=static_gyro_threshold,
            min_samples=gravity_min_samples,
        )
        self._heading_estimator = HeadingEstimator(
            vehicle_type=vehicle_type,
            history_size=heading_history_size,
        )

        # State
        self._alignment_state: AlignmentState = AlignmentState.UNINITIALIZED
        self._confidence: float = 0.0
        self._last_yaw: float = 0.0
        self._last_align_quat: Quat = (1.0, 0.0, 0.0, 0.0)

        # Reorientation detection based on reference alignment
        self._reentry_deg_threshold = math.radians(reentry_deg_threshold)
        self._reference_quat: Optional[Quat] = None
        self._have_reference: bool = False

        # Minimum confidence threshold
        self._min_confidence_for_aligned = min_confidence_for_aligned

    def add_imu_sample(self, sample: ImuSample) -> Tuple[bool, Optional[AlignmentStatus]]:
        """
        Add IMU sample and update alignment estimate.

        Args:
            sample: IMU sample.

        Returns:
            (accepted_for_calibration, current_alignment_status)
            accepted_for_calibration: True if sample used for gravity alignment
            current_alignment_status: Current alignment status (always returned)
        """
        # Add to gravity alignment (static detection)
        gravity_accepted = self._gravity_aligner.add_sample(sample)

        # Add to heading estimator (uses dynamics)
        self._heading_estimator.add_imu_sample(sample)
        self._heading_estimator.update()

        # Update the combined alignment
        self._update_alignment()

        status = self.get_alignment_status()
        return gravity_accepted, status

    def add_gnss_fix(self, fix: GnssFix) -> Tuple[bool, Optional[AlignmentStatus]]:
        """
        Add GNSS fix and update alignment estimate.

        Args:
            fix: GNSS fix.

        Returns:
            (used_for_heading, current_alignment_status)
            used_for_heading: True if fix used for heading estimation
            current_alignment_status: Current alignment status (always returned)
        """
        used = self._heading_estimator.add_gnss_fix(fix)
        self._heading_estimator.update()
        self._update_alignment()
        status = self.get_alignment_status()
        return used, status

    def add_mag_sample(self, sample: MagSample) -> Tuple[bool, Optional[AlignmentStatus]]:
        """
        Add magnetometer sample and update alignment estimate.

        Args:
            sample: Magnetometer sample.

        Returns:
            (used_for_heading, current_alignment_status)
            used_for_heading: True if sample used for heading estimation
            current_alignment_status: Current alignment status (always returned)
        """
        used = self._heading_estimator.add_mag_sample(sample)
        self._update_alignment()
        status = self.get_alignment_status()
        return used, status

    def _update_alignment(self) -> None:
        """Update the combined alignment estimate from sub-estimators."""
        if self._alignment_state == AlignmentState.LOST:
            # Remain LOST until explicitly reset
            return

        # Get current estimates
        gravity_valid = self._gravity_aligner.is_valid
        heading_valid = self._heading_estimator.is_valid

        if not gravity_valid:
            self._alignment_state = AlignmentState.UNINITIALIZED
            self._confidence = 0.0
            self._last_align_quat = (1.0, 0.0, 0.0, 0.0)
            return

        # Get gravity-based roll/pitch
        roll = self._gravity_aligner.roll
        pitch = self._gravity_aligner.pitch
        gravity_conf = self._gravity_aligner.confidence

        # Get heading estimate (may be invalid)
        if heading_valid:
            yaw = self._heading_estimator.yaw_offset
            heading_conf = self._heading_estimator.confidence
        else:
            # No heading info - use last known or zero
            yaw = self._last_yaw
            heading_conf = 0.0

        # Create quaternion from estimated orientation
        # q_phone^vehicle = R(roll, pitch, yaw)
        q_new = quat_from_euler(roll, pitch, yaw)
        q_new = quat_normalize(q_new)

        # Confidence fusion: geometric mean of grav and heading confidence
        # (both must be good for high confidence)
        if heading_valid:
            conf = math.sqrt(gravity_conf * heading_conf)
        else:
            # Only gravity available -> partial alignment
            conf = gravity_conf * 0.5  # Penalize lack of heading

        # State machine
        if not gravity_valid:
            new_state = AlignmentState.UNINITIALIZED
        elif gravity_valid and not heading_valid:
            new_state = AlignmentState.GRAVITY_ONLY
        elif gravity_valid and heading_valid:
            if conf >= self._min_confidence_for_aligned:
                new_state = AlignmentState.FULLY_ALIGNED
            else:
                new_state = AlignmentState.PARTIALLY_ALIGNED
        else:
            new_state = AlignmentState.UNINITIALIZED

        # Reorientation detection: check for sudden changes inconsistent with motion
        if new_state in (AlignmentState.FULLY_ALIGNED, AlignmentState.PARTIALLY_ALIGNED, AlignmentState.GRAVITY_ONLY):
            if self._have_reference and self._reference_quat is not None:
                # If we didn't have heading before, don't penalize a suddenly discovered heading
                if self._alignment_state == AlignmentState.GRAVITY_ONLY and heading_valid:
                    # We just acquired heading, so update reference to prevent false LOST
                    self._reference_quat = q_new
                else:
                    q_last = self._reference_quat
                    angle_change = self._quat_angle_between(q_last, q_new)

                    # Large sudden change suggests phone movement/reorientation
                    if angle_change > self._reentry_deg_threshold:
                        new_state = AlignmentState.LOST
                        conf = 0.0
                        gravity_valid = False
                        self._gravity_aligner.reset()
                        self._heading_estimator.reset()
                        self._have_reference = False
                        self._reference_quat = None
                        q_new = (1.0, 0.0, 0.0, 0.0)

            # Update reference quaternion if we are aligned and not lost
            if new_state != AlignmentState.LOST and new_state != AlignmentState.UNINITIALIZED:
                if not self._have_reference or conf >= self._confidence:
                    # Update reference when confidence is high or higher than before
                    self._reference_quat = q_new
                    self._have_reference = True

        # Update state
        self._alignment_state = new_state
        self._confidence = conf
        self._last_yaw = yaw
        self._last_align_quat = q_new

    def _quat_angle_between(self, q1: Quat, q2: Quat) -> float:
        """Compute angle between two quaternions."""
        # q_diff = conj(q1) * q2
        q_diff = quat_multiply(quat_conjugate(q1), q2)
        # Angle is 2 * acos(|w|)
        w_abs = min(1.0, abs(q_diff[0]))
        return 2.0 * math.acos(w_abs)

    def get_alignment_status(self) -> AlignmentStatus:
        """
        Get current alignment status.

        Returns:
            AlignmentStatus with state, confidence, and angle estimates.
        """
        if self._alignment_state == AlignmentState.LOST:
            return AlignmentStatus(
                state=AlignmentState.LOST,
                confidence=0.0,
                gravity_confidence=0.0,
                heading_confidence=0.0,
                roll_rad=0.0,
                pitch_rad=0.0,
                yaw_rad=0.0,
                timestamp_ns=0,
            )

        if not self._gravity_aligner.is_valid:
            return AlignmentStatus(
                state=AlignmentState.UNINITIALIZED,
                confidence=0.0,
                gravity_confidence=0.0,
                heading_confidence=0.0,
                roll_rad=0.0,
                pitch_rad=0.0,
                yaw_rad=0.0,
                timestamp_ns=0,  # Would be set from latest sample
            )

        roll = self._gravity_aligner.roll
        pitch = self._gravity_aligner.pitch

        if self._heading_estimator.is_valid:
            yaw = self._heading_estimator.yaw_offset
            heading_conf = self._heading_estimator.confidence
        else:
            yaw = self._last_yaw
            heading_conf = 0.0

        gravity_conf = self._gravity_aligner.confidence

        return AlignmentStatus(
            state=self._alignment_state,
            confidence=self._confidence,
            gravity_confidence=gravity_conf,
            heading_confidence=heading_conf,
            roll_rad=roll,
            pitch_rad=pitch,
            yaw_rad=yaw,
            timestamp_ns=0,  # Would be set from latest sample in real use
        )

    @property
    def is_aligned(self) -> bool:
        """Whether alignment is usable for navigation (roll/pitch at least)."""
        status = self.get_alignment_status()
        return status.is_usable()

    @property
    def is_heading_available(self) -> bool:
        """Whether heading (yaw) alignment is available."""
        status = self.get_alignment_status()
        return status.is_heading_available()

    def get_phone_to_vehicle_quaternion(self) -> Quat:
        """
        Get current phone-to-vehicle rotation quaternion.

        Returns:
            Quaternion (w, x, y, z) representing rotation from phone frame
            to vehicle frame. Returns identity if no alignment.
        """
        status = self.get_alignment_status()
        if not status.is_usable():
            return (1.0, 0.0, 0.0, 0.0)

        return quat_from_euler(
            status.roll_rad,
            status.pitch_rad,
            status.yaw_rad,
        )

    def reset(self) -> None:
        """Reset alignment engine to initial state."""
        self._gravity_aligner.reset()
        self._heading_estimator.reset()
        self._alignment_state = AlignmentState.UNINITIALIZED
        self._confidence = 0.0
        self._last_yaw = 0.0
        self._last_align_quat = (1.0, 0.0, 0.0, 0.0)
        self._yaw_history.clear()
        self._quat_history.clear()
        self._timestamp_history.clear()