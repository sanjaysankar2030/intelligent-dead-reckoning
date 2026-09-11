"""
Coordinate alignment and transforms.
"""
from core.alignment.frames import (
    AlignmentState,
    AlignmentStatus,
    CoordinateFrame,
    VehicleType,
)
from core.alignment.quaternion_utils import (
    quat_conjugate,
    quat_from_axis_angle,
    quat_from_euler,
    quat_from_rotation_matrix,
    quat_multiply,
    quat_normalize,
    quat_rotate_vector,
    quat_to_euler,
    quat_to_rotation_matrix,
)
from core.alignment.gravity_alignment import GravityAligner
from core.alignment.heading_estimator import HeadingEstimator
from core.alignment.alignment_engine import AlignmentEngine

__all__ = [
    "AlignmentState",
    "AlignmentStatus",
    "CoordinateFrame",
    "VehicleType",
    "GravityAligner",
    "HeadingEstimator",
    "AlignmentEngine",
    # Quaternion exports
    "quat_conjugate",
    "quat_from_axis_angle",
    "quat_from_euler",
    "quat_from_rotation_matrix",
    "quat_multiply",
    "quat_normalize",
    "quat_rotate_vector",
    "quat_to_euler",
    "quat_to_rotation_matrix",
]