"""
Coordinate frame definitions and conventions for the dead reckoning system.

All frames are right-handed orthogonal coordinate systems.
Rotations use Hamilton quaternion convention: q = [w, x, y, z].
Rotation matrix R_a^b rotates a vector FROM frame a TO frame b:
    v_b = R_a^b @ v_a

Frame Chain:
    Sensor(S) -> Body/Phone(B) -> Vehicle(V) -> Navigation(N)

    v_n = R_b^n @ R_v^b^{-1} ... but in practice:
    v_n = R_v^n @ R_b^v @ v_b

    where R_b^v is the phone-to-vehicle rotation (what this module estimates).

References:
    - Android Sensor Coordinate System documentation
    - Titterton & Weston, "Strapdown Inertial Navigation Technology"
    - Groves, "Principles of GNSS, Inertial, and Multisensor Integrated Navigation Systems"
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class CoordinateFrame(Enum):
    """Enumeration of coordinate frames used in the system."""

    SENSOR = auto()
    """
    Sensor Frame (S):
    Raw tri-axis sensor coordinates as reported by the hardware.
    For Android devices, this matches the Android sensor coordinate system:
        X: points right when device is held in portrait, screen facing user
        Y: points up when device is held in portrait, screen facing user
        Z: points out of the screen (toward the user)
    Units: accelerometer in m/s², gyroscope in rad/s, magnetometer in µT.
    Handedness: RIGHT-HANDED.
    """

    BODY = auto()
    """
    Body / Phone Frame (B):
    Orthogonalized sensor body frame after factory calibration corrections.
    In our system, identical to the Sensor frame for consumer-grade IMUs
    (factory misalignment correction is not implemented at this stage).
    Axes identical to SENSOR frame.
    Handedness: RIGHT-HANDED.
    """

    VEHICLE = auto()
    """
    Vehicle Frame (V):
        X_v: Forward (direction of vehicle travel)
        Y_v: Right (lateral, completing right-handed system)
        Z_v: Down (gravitational direction)
    This is the standard Forward-Right-Down (FRD) vehicle body frame.
    Handedness: RIGHT-HANDED.

    Note: This is independent of vehicle type (car, motorcycle, scooter).
    For motorcycles/scooters, the vehicle frame still has X forward and Z down
    when the vehicle is upright — lean angles are captured separately.
    """

    NAVIGATION = auto()
    """
    Navigation Frame (N):
    Local tangent plane frame, North-East-Down (NED):
        X_n: North
        Y_n: East
        Z_n: Down (toward Earth center)
    Origin: WGS-84 reference point (latitude, longitude, altitude).
    Handedness: RIGHT-HANDED.
    """

    EARTH = auto()
    """
    Earth Frame (E):
    Earth-Centered Earth-Fixed (ECEF) Cartesian coordinates.
    Used for global geodetic mapping; not directly used in alignment.
    Handedness: RIGHT-HANDED.
    """


class VehicleType(Enum):
    """Vehicle type classification for constraint adaptation."""
    UNKNOWN = auto()
    CAR = auto()
    MOTORCYCLE = auto()
    SCOOTER = auto()


class AlignmentState(Enum):
    """Phone-to-vehicle alignment confidence state."""

    UNINITIALIZED = auto()
    """No alignment estimate available. Waiting for sufficient data."""

    GRAVITY_ONLY = auto()
    """
    Roll and pitch estimated from gravity vector.
    Heading (yaw) is unconstrained — partially aligned.
    Sufficient for vertical/tilt-aware processing but not for
    horizontal navigation.
    """

    PARTIALLY_ALIGNED = auto()
    """
    Some heading information available but not fully reliable.
    Examples: magnetometer-only heading, low-speed GNSS heading,
    or insufficient dynamic data for confident yaw estimation.
    """

    FULLY_ALIGNED = auto()
    """
    Roll, pitch AND heading are well-constrained.
    GNSS-velocity heading or sufficient vehicle dynamics have
    established a reliable phone-to-vehicle rotation.
    """

    DEGRADED = auto()
    """
    Previously aligned but confidence has dropped.
    Possible causes: phone movement detected, prolonged straight-line
    driving (heading drift), or sensor anomaly.
    System continues with last-known alignment but flags uncertainty.
    """

    LOST = auto()
    """
    Alignment is invalid. Phone has been moved/reoriented, or
    sensor data is inconsistent with the current alignment estimate.
    System must re-initialize alignment.
    """


@dataclass(frozen=True)
class AlignmentStatus:
    """Current alignment state and confidence metrics.

    Attributes:
        state: Current alignment state.
        confidence: Overall alignment confidence in [0, 1].
            0.0 = no confidence, 1.0 = fully confident.
        gravity_confidence: Confidence in gravity (roll/pitch) estimate [0, 1].
        heading_confidence: Confidence in heading (yaw) estimate [0, 1].
        roll_rad: Estimated roll angle in radians (rotation about vehicle X/forward).
        pitch_rad: Estimated pitch angle in radians (rotation about vehicle Y/right).
        yaw_rad: Estimated yaw offset in radians (rotation about vehicle Z/down).
            This is the heading offset between phone forward and vehicle forward,
            NOT the vehicle heading in navigation frame.
    """
    state: AlignmentState
    confidence: float
    gravity_confidence: float
    heading_confidence: float
    roll_rad: float
    pitch_rad: float
    yaw_rad: float
    timestamp_ns: int = 0

    def is_usable(self) -> bool:
        """Whether the alignment is sufficiently reliable for navigation."""
        return self.state in (
            AlignmentState.GRAVITY_ONLY,
            AlignmentState.FULLY_ALIGNED,
            AlignmentState.PARTIALLY_ALIGNED,
            AlignmentState.DEGRADED,
        )

    def is_heading_available(self) -> bool:
        """Whether heading (yaw) alignment is available and reasonably reliable."""
        return self.state in (
            AlignmentState.FULLY_ALIGNED,
            AlignmentState.PARTIALLY_ALIGNED,
        ) and self.heading_confidence > 0.3
