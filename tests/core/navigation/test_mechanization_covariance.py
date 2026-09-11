"""
Unit tests for covariance propagation.
"""

import numpy as np
import pytest
from core.navigation.mechanization import StrapdownINS
from core.sensors.data_types import ImuSample

def test_covariance_growth():
    """Covariance should grow over time due to process noise integration."""
    ins = StrapdownINS(
        accel_noise_std=0.1,
        gyro_noise_std=0.01,
        accel_bias_walk_std=0.001,
        gyro_bias_walk_std=0.0001
    )
    
    init_cov = np.trace(ins.covariance)
    
    # Run stationary for 10 seconds (1000 steps at 100Hz)
    for i in range(1000):
        t_ns = (i + 1) * 10_000_000
        sample = ImuSample(
            timestamp_ns=t_ns,
            accel_m_s2=(0.0, 0.0, -9.80665),
            gyro_rad_s=(0.0, 0.0, 0.0)
        )
        ins.propagate(sample, propagate_covariance=True)
        
    final_cov = np.trace(ins.covariance)
    
    # Process noise should inject uncertainty, trace must increase
    assert final_cov > init_cov
    
    # Check symmetric positive semi-definite loosely
    assert np.allclose(ins.covariance, ins.covariance.T)
    eigenvalues = np.linalg.eigvals(ins.covariance)
    assert np.all(eigenvalues > -1e-6)

def test_skip_covariance_prop():
    """Verify covariance is unaffected if propagate_covariance=False."""
    ins = StrapdownINS()
    init_cov = ins.covariance.copy()
    
    t_ns = 1 * 10_000_000
    sample = ImuSample(
        timestamp_ns=t_ns,
        accel_m_s2=(0.0, 0.0, -9.80665),
        gyro_rad_s=(0.0, 0.0, 0.0)
    )
    ins.propagate(sample, propagate_covariance=False)
    
    assert np.array_equal(ins.covariance, init_cov)
