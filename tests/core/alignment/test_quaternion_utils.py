"""
Unit tests for quaternion utility functions.
"""

import math

import numpy as np
import pytest

from core.alignment.quaternion_utils import (
    QUAT_IDENTITY,
    quat_angle_between,
    quat_conjugate,
    quat_from_axis_angle,
    quat_from_euler,
    quat_from_rotation_matrix,
    quat_from_two_vectors,
    quat_multiply,
    quat_normalize,
    quat_rotate_vector,
    quat_to_euler,
    quat_to_rotation_matrix,
    wrap_angle,
)


def test_quat_normalize():
    q = (2.0, 0.0, 0.0, 0.0)
    q_norm = quat_normalize(q)
    assert q_norm == (1.0, 0.0, 0.0, 0.0)

    q = (1.0, 1.0, 1.0, 1.0)
    q_norm = quat_normalize(q)
    assert math.isclose(math.sqrt(sum(x*x for x in q_norm)), 1.0)

    # Zero quaternion maps to identity
    q = (0.0, 0.0, 0.0, 0.0)
    assert quat_normalize(q) == QUAT_IDENTITY


def test_quat_conjugate():
    q = (1.0, 2.0, 3.0, 4.0)
    q_conj = quat_conjugate(q)
    assert q_conj == (1.0, -2.0, -3.0, -4.0)


def test_quat_multiply():
    # Identity multiplication
    q1 = (0.5, 0.5, 0.5, 0.5)
    assert quat_multiply(q1, QUAT_IDENTITY) == q1
    assert quat_multiply(QUAT_IDENTITY, q1) == q1

    # Rotation composition: rx(90) then ry(90)
    q_rx = quat_from_axis_angle((1.0, 0.0, 0.0), math.pi/2)
    q_ry = quat_from_axis_angle((0.0, 1.0, 0.0), math.pi/2)

    # (q_ry * q_rx) vector rotates by q_rx then q_ry
    q_combined = quat_multiply(q_ry, q_rx)

    v = (0.0, 1.0, 0.0)  # Y-axis vector
    # rx(90) sends Y->Z. ry(90) sends Z->X
    v_rot = quat_rotate_vector(q_combined, v)
    assert math.isclose(v_rot[0], 1.0, abs_tol=1e-10)
    assert math.isclose(v_rot[1], 0.0, abs_tol=1e-10)
    assert math.isclose(v_rot[2], 0.0, abs_tol=1e-10)


def test_quat_rotate_vector():
    # Rotate [1, 0, 0] by 90 deg around Z
    q = quat_from_axis_angle((0.0, 0.0, 1.0), math.pi/2)
    v = (1.0, 0.0, 0.0)
    v_rot = quat_rotate_vector(q, v)

    assert math.isclose(v_rot[0], 0.0, abs_tol=1e-10)
    assert math.isclose(v_rot[1], 1.0, abs_tol=1e-10)
    assert math.isclose(v_rot[2], 0.0, abs_tol=1e-10)


def test_quat_euler_conversion():
    # ZYX convention: yaw, pitch, roll
    r, p, y = math.pi/4, math.pi/6, math.pi/3
    q = quat_from_euler(r, p, y)
    r2, p2, y2 = quat_to_euler(q)

    assert math.isclose(r, r2, abs_tol=1e-10)
    assert math.isclose(p, p2, abs_tol=1e-10)
    assert math.isclose(y, y2, abs_tol=1e-10)


def test_quat_matrix_conversion():
    r, p, y = math.pi/4, math.pi/6, math.pi/3
    q = quat_from_euler(r, p, y)

    R = quat_to_rotation_matrix(q)
    q2 = quat_from_rotation_matrix(R)

    # Check that q2 represents same rotation (q and -q are same rotation)
    assert math.isclose(abs(q[0]), abs(q2[0]), abs_tol=1e-10)
    assert math.isclose(abs(q[1]), abs(q2[1]), abs_tol=1e-10)
    assert math.isclose(abs(q[2]), abs(q2[2]), abs_tol=1e-10)
    assert math.isclose(abs(q[3]), abs(q2[3]), abs_tol=1e-10)


def test_quat_from_two_vectors():
    v1 = np.array([1.0, 0.0, 0.0])
    v2 = np.array([0.0, 1.0, 0.0])

    q = quat_from_two_vectors(v1, v2)
    v1_tuple = (float(v1[0]), float(v1[1]), float(v1[2]))
    v1_rot = quat_rotate_vector(q, v1_tuple)

    assert math.isclose(v1_rot[0], v2[0], abs_tol=1e-10)
    assert math.isclose(v1_rot[1], v2[1], abs_tol=1e-10)
    assert math.isclose(v1_rot[2], v2[2], abs_tol=1e-10)

    # Test anti-parallel vectors
    v3 = np.array([-1.0, 0.0, 0.0])
    q_opp = quat_from_two_vectors(v1, v3)
    v1_rot2 = quat_rotate_vector(q_opp, v1_tuple)

    assert math.isclose(v1_rot2[0], v3[0], abs_tol=1e-10)
    assert math.isclose(v1_rot2[1], v3[1], abs_tol=1e-10)
    assert math.isclose(v1_rot2[2], v3[2], abs_tol=1e-10)


def test_wrap_angle():
    assert math.isclose(wrap_angle(0.0), 0.0)
    assert math.isclose(wrap_angle(math.pi), math.pi)
    assert math.isclose(wrap_angle(2 * math.pi), 0.0)
    assert math.isclose(wrap_angle(3 * math.pi), math.pi)
    assert math.isclose(wrap_angle(-3 * math.pi), -math.pi)
