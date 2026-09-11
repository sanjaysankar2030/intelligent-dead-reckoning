import math
import numpy as np
import pytest

from core.navigation.mechanization import StrapdownINS
from core.navigation.state import NavState
from core.filters.eskf import ErrorStateKalmanFilter, UpdateResult
from core.alignment.quaternion_utils import quat_to_euler

def test_eskf_initialization():
    ins = StrapdownINS()
    eskf = ErrorStateKalmanFilter(ins)
    assert eskf.ins is ins

def test_kalman_gain_and_injection_position():
    ins = StrapdownINS()
    
    # Intentionally set a nominal position error
    ins.state.position_m = (10.0, -5.0, 3.0)
    
    # Inflate covariance so gain is near 1
    ins.covariance = np.eye(15) * 100.0
    
    eskf = ErrorStateKalmanFilter(ins)
    
    # Simulate GNSS measurement saying position is (0, 0, 0)
    R = np.eye(3) * 0.001
    res = eskf.update_position((0.0, 0.0, 0.0), R, gate=1e6)
    
    assert res.accepted
    
    # The state should be pulled back heavily towards (0, 0, 0)
    assert math.isclose(ins.state.position_m[0], 0.0, abs_tol=1e-2)
    assert math.isclose(ins.state.position_m[1], 0.0, abs_tol=1e-2)
    assert math.isclose(ins.state.position_m[2], 0.0, abs_tol=1e-2)
    
    # Verify covariance decreased for position block
    assert ins.covariance[0,0] < 1.0

def test_kalman_gain_and_injection_velocity():
    ins = StrapdownINS()
    ins.state.velocity_mps = (5.0, -5.0, 5.0)
    ins.covariance = np.eye(15) * 100.0
    
    eskf = ErrorStateKalmanFilter(ins)
    
    R = np.eye(3) * 0.001
    res = eskf.update_velocity((0.0, 0.0, 0.0), R, gate=1e6)
    
    assert res.accepted
    assert math.isclose(ins.state.velocity_mps[0], 0.0, abs_tol=1e-2)
    assert math.isclose(ins.state.velocity_mps[1], 0.0, abs_tol=1e-2)
    assert math.isclose(ins.state.velocity_mps[2], 0.0, abs_tol=1e-2)

def test_kalman_gain_and_injection_attitude():
    # To test attitude, we need an observation that projects onto attitude.
    # Velocity update with a prior velocity is standard.
    # If velocity is [10, 0, 0] nominally, but gps says [0, 10, 0], 
    # it implies an attitude error of ~90 degrees.
    # But since P is diagonal, and H_vel for attitude is non-zero ONLY if f is non-zero,
    # Wait, we test injection analytically.
    ins = StrapdownINS()
    eskf = ErrorStateKalmanFilter(ins)
    
    # Manually inject an error state
    delta_x = np.zeros(15)
    # 90 degrees around Z axis (yaw)
    delta_x[8] = math.pi / 2
    
    eskf._inject_error_state(delta_x)
    
    q_new = ins.state.attitude_q_v2n
    # Norm must be preserved
    assert math.isclose(np.linalg.norm(q_new), 1.0, abs_tol=1e-6)
    
    r, p, y = quat_to_euler(q_new)
    assert math.isclose(r, 0.0, abs_tol=1e-5)
    assert math.isclose(p, 0.0, abs_tol=1e-5)
    assert math.isclose(y, math.pi / 2, abs_tol=1e-5)

def test_cov_symmetry_and_psd():
    ins = StrapdownINS()
    ins.covariance = np.random.rand(15, 15)
    # Ensure starting is PSD randomly
    ins.covariance = ins.covariance @ ins.covariance.T
    
    eskf = ErrorStateKalmanFilter(ins)
    z = np.zeros(3)
    H = np.zeros((3, 15))
    H[0:3, 0:3] = np.eye(3)
    R = np.eye(3)
    
    eskf._apply_measurement(z, H, R, mahalanobis_gate=float('inf'))
    
    # Check symmetry
    P = ins.covariance
    assert np.allclose(P, P.T)
    # Check PSD
    eigvals = np.linalg.eigvals(P)
    assert np.all(eigvals > -1e-6)

def test_gating():
    ins = StrapdownINS()
    ins.covariance = np.eye(15)
    eskf = ErrorStateKalmanFilter(ins)
    
    # Measure 10s of meters off, with 1 cov and 1 R -> Innovation Cov = 2.
    # z^T S^-1 z = 10^2 / 2 = 50. Mahalanobis = sqrt(50) = 7.07
    z = np.array([10.0, 0.0, 0.0])
    H = np.zeros((3, 15))
    H[0:3, 0:3] = np.eye(3)
    R = np.eye(3)
    
    # Should reject if gate is 5.0
    res = eskf._apply_measurement(z, H, R, mahalanobis_gate=5.0)
    assert not res.accepted
    
    # Should accept if gate is > 7.07
    res = eskf._apply_measurement(z, H, R, mahalanobis_gate=8.0)
    assert res.accepted

def test_innovation_calculation():
    ins = StrapdownINS()
    ins.state.position_m = (1.0, -1.0, 0.0)
    eskf = ErrorStateKalmanFilter(ins)
    
    res = eskf.update_position((5.0, 5.0, 0.0), np.eye(3), gate=float('inf'))
    
    assert math.isclose(res.innovation[0], 4.0, abs_tol=1e-5)
    assert math.isclose(res.innovation[1], 6.0, abs_tol=1e-5)
    assert math.isclose(res.innovation[2], 0.0, abs_tol=1e-5)
