"""
Quaternion math utilities for rotation representation and manipulation.

Convention:
    Hamilton quaternion: q = [w, x, y, z] where w is the scalar part.
    A quaternion q_a^b represents the rotation FROM frame a TO frame b:
        v_b = q_a^b * v_a * conj(q_a^b)
    or equivalently with the rotation matrix:
        v_b = R(q_a^b) @ v_a

    Quaternion multiplication follows Hamilton convention:
        (q1 * q2) applies q2 first, then q1.

All angles are in radians unless otherwise noted.
"""

from __future__ import annotations

import math
from typing import Tuple

import numpy as np


# Type alias: quaternion as (w, x, y, z)
Quat = Tuple[float, float, float, float]

# Identity quaternion
QUAT_IDENTITY: Quat = (1.0, 0.0, 0.0, 0.0)


def quat_normalize(q: Quat) -> Quat:
    """Normalize a quaternion to unit length.

    Args:
        q: Quaternion (w, x, y, z).

    Returns:
        Normalized quaternion.
    """
    norm = math.sqrt(q[0]**2 + q[1]**2 + q[2]**2 + q[3]**2)
    if norm < 1e-15:
        return QUAT_IDENTITY
    inv_norm = 1.0 / norm
    return (q[0] * inv_norm, q[1] * inv_norm, q[2] * inv_norm, q[3] * inv_norm)


def quat_conjugate(q: Quat) -> Quat:
    """Conjugate (inverse for unit quaternions) of a quaternion.

    For a unit quaternion representing rotation R, conj(q) represents R^T.

    Args:
        q: Quaternion (w, x, y, z).

    Returns:
        Conjugate quaternion (w, -x, -y, -z).
    """
    return (q[0], -q[1], -q[2], -q[3])


def quat_multiply(q1: Quat, q2: Quat) -> Quat:
    """Hamilton quaternion multiplication: q1 * q2.

    Applies q2 first, then q1.
    If q1 = q_b^c and q2 = q_a^b, then q1*q2 = q_a^c.

    Args:
        q1: Left quaternion (w, x, y, z).
        q2: Right quaternion (w, x, y, z).

    Returns:
        Product quaternion (w, x, y, z).
    """
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return (
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
    )


def quat_rotate_vector(q: Quat, v: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Rotate a 3D vector by a unit quaternion.

    Computes: v' = q * [0, v] * conj(q)

    Args:
        q: Unit quaternion (w, x, y, z) representing rotation.
        v: 3D vector (x, y, z).

    Returns:
        Rotated vector (x', y', z').
    """
    # Optimized rotation without full quaternion multiply
    w, qx, qy, qz = q
    vx, vy, vz = v

    # Cross product: t = 2 * (q_vec x v)
    tx = 2.0 * (qy * vz - qz * vy)
    ty = 2.0 * (qz * vx - qx * vz)
    tz = 2.0 * (qx * vy - qy * vx)

    # v' = v + w * t + q_vec x t
    return (
        vx + w * tx + (qy * tz - qz * ty),
        vy + w * ty + (qz * tx - qx * tz),
        vz + w * tz + (qx * ty - qy * tx),
    )


def quat_from_axis_angle(axis: Tuple[float, float, float], angle: float) -> Quat:
    """Create quaternion from axis-angle representation.

    Args:
        axis: Unit rotation axis (x, y, z). Must be unit length.
        angle: Rotation angle in radians.

    Returns:
        Unit quaternion (w, x, y, z).
    """
    half = angle * 0.5
    s = math.sin(half)
    c = math.cos(half)
    return (c, axis[0] * s, axis[1] * s, axis[2] * s)


def quat_from_euler(roll: float, pitch: float, yaw: float) -> Quat:
    """Create quaternion from Euler angles (ZYX intrinsic / aerospace convention).

    Rotation order: yaw (Z) -> pitch (Y) -> roll (X).
    This corresponds to the standard aerospace/vehicle convention where:
        yaw   rotates about the Down axis (Z in vehicle NED frame)
        pitch rotates about the Right axis (Y in vehicle FRD frame)
        roll  rotates about the Forward axis (X in vehicle FRD frame)

    Args:
        roll:  Rotation about X axis (forward) in radians.
        pitch: Rotation about Y axis (right) in radians.
        yaw:   Rotation about Z axis (down) in radians.

    Returns:
        Unit quaternion (w, x, y, z).
    """
    cr = math.cos(roll * 0.5)
    sr = math.sin(roll * 0.5)
    cp = math.cos(pitch * 0.5)
    sp = math.sin(pitch * 0.5)
    cy = math.cos(yaw * 0.5)
    sy = math.sin(yaw * 0.5)

    w = cr * cp * cy + sr * sp * sy
    x = sr * cp * cy - cr * sp * sy
    y = cr * sp * cy + sr * cp * sy
    z = cr * cp * sy - sr * sp * cy

    return quat_normalize((w, x, y, z))


def quat_to_euler(q: Quat) -> Tuple[float, float, float]:
    """Extract Euler angles from quaternion (ZYX intrinsic / aerospace convention).

    Args:
        q: Unit quaternion (w, x, y, z).

    Returns:
        (roll, pitch, yaw) in radians.
        roll  in [-pi, pi]
        pitch in [-pi/2, pi/2]
        yaw   in [-pi, pi]
    """
    w, x, y, z = q

    # Roll (X axis rotation)
    sinr_cosp = 2.0 * (w * x + y * z)
    cosr_cosp = 1.0 - 2.0 * (x * x + y * y)
    roll = math.atan2(sinr_cosp, cosr_cosp)

    # Pitch (Y axis rotation) — clamp to avoid NaN at gimbal lock
    sinp = 2.0 * (w * y - z * x)
    sinp = max(-1.0, min(1.0, sinp))
    pitch = math.asin(sinp)

    # Yaw (Z axis rotation)
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    yaw = math.atan2(siny_cosp, cosy_cosp)

    return (roll, pitch, yaw)


def quat_to_rotation_matrix(q: Quat) -> np.ndarray:
    """Convert unit quaternion to 3x3 rotation matrix.

    Args:
        q: Unit quaternion (w, x, y, z).

    Returns:
        3x3 rotation matrix R such that v_rotated = R @ v.
    """
    w, x, y, z = q

    # Precompute products
    xx = x * x
    yy = y * y
    zz = z * z
    xy = x * y
    xz = x * z
    yz = y * z
    wx = w * x
    wy = w * y
    wz = w * z

    return np.array([
        [1.0 - 2.0*(yy + zz), 2.0*(xy - wz),       2.0*(xz + wy)],
        [2.0*(xy + wz),       1.0 - 2.0*(xx + zz),  2.0*(yz - wx)],
        [2.0*(xz - wy),       2.0*(yz + wx),         1.0 - 2.0*(xx + yy)],
    ])


def quat_from_rotation_matrix(R: np.ndarray) -> Quat:
    """Convert 3x3 rotation matrix to unit quaternion.

    Uses Shepperd's method for numerical stability.

    Args:
        R: 3x3 rotation matrix.

    Returns:
        Unit quaternion (w, x, y, z).
    """
    trace = R[0, 0] + R[1, 1] + R[2, 2]

    if trace > 0:
        s = 0.5 / math.sqrt(trace + 1.0)
        w = 0.25 / s
        x = (R[2, 1] - R[1, 2]) * s
        y = (R[0, 2] - R[2, 0]) * s
        z = (R[1, 0] - R[0, 1]) * s
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = 2.0 * math.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2])
        w = (R[2, 1] - R[1, 2]) / s
        x = 0.25 * s
        y = (R[0, 1] + R[1, 0]) / s
        z = (R[0, 2] + R[2, 0]) / s
    elif R[1, 1] > R[2, 2]:
        s = 2.0 * math.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2])
        w = (R[0, 2] - R[2, 0]) / s
        x = (R[0, 1] + R[1, 0]) / s
        y = 0.25 * s
        z = (R[1, 2] + R[2, 1]) / s
    else:
        s = 2.0 * math.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1])
        w = (R[1, 0] - R[0, 1]) / s
        x = (R[0, 2] + R[2, 0]) / s
        y = (R[1, 2] + R[2, 1]) / s
        z = 0.25 * s

    return quat_normalize((w, x, y, z))


def quat_from_two_vectors(v_from: np.ndarray, v_to: np.ndarray) -> Quat:
    """Compute the shortest rotation quaternion that rotates v_from to v_to.

    Args:
        v_from: Source direction vector (will be normalized).
        v_to: Target direction vector (will be normalized).

    Returns:
        Unit quaternion representing the rotation.
    """
    v_from = v_from / (np.linalg.norm(v_from) + 1e-15)
    v_to = v_to / (np.linalg.norm(v_to) + 1e-15)

    dot = float(np.dot(v_from, v_to))

    # Vectors are nearly parallel
    if dot > 0.999999:
        return QUAT_IDENTITY

    # Vectors are nearly anti-parallel
    if dot < -0.999999:
        # Find an orthogonal axis
        ortho = np.array([1.0, 0.0, 0.0])
        if abs(v_from[0]) > 0.9:
            ortho = np.array([0.0, 1.0, 0.0])
        axis = np.cross(v_from, ortho)
        axis = axis / np.linalg.norm(axis)
        return (0.0, float(axis[0]), float(axis[1]), float(axis[2]))

    cross = np.cross(v_from, v_to)
    w = 1.0 + dot
    return quat_normalize((w, float(cross[0]), float(cross[1]), float(cross[2])))


def quat_angle_between(q1: Quat, q2: Quat) -> float:
    """Compute the rotation angle between two quaternions.

    Args:
        q1: First quaternion (w, x, y, z).
        q2: Second quaternion (w, x, y, z).

    Returns:
        Angle in radians in [0, pi].
    """
    # q_diff = conj(q1) * q2
    q_diff = quat_multiply(quat_conjugate(q1), q2)
    # Angle is 2 * acos(|w|)
    w_abs = min(1.0, abs(q_diff[0]))
    return 2.0 * math.acos(w_abs)


def wrap_angle(angle: float) -> float:
    """Wrap angle to [-pi, pi].

    Args:
        angle: Angle in radians.

    Returns:
        Wrapped angle in [-pi, pi].
    """
    while angle > math.pi:
        angle -= 2.0 * math.pi
    while angle < -math.pi:
        angle += 2.0 * math.pi
    return angle
