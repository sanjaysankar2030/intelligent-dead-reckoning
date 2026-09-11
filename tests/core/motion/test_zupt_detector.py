"""
Unit tests for ZUPT (Zero Velocity Update) detector.
"""
import pytest
import numpy as np
from core.motion.zupt_detector import ZuptDetector


def test_zupt_initialization():
    """Test ZuptDetector initialization with default and custom parameters."""
    detector = ZuptDetector()
    assert detector.window_size == 50
    assert detector.accel_var_thresh == 0.5
    assert len(detector.accel_norms) == 0

    # Custom parameters
    detector2 = ZuptDetector(window_size=100, accel_var_threshold=1.0)
    assert detector2.window_size == 100
    assert detector2.accel_var_thresh == 1.0


def test_zupt_stationary_detection():
    """Test that detector correctly identifies stationary samples."""
    detector = ZuptDetector(window_size=50)

    # Add 50 stationary samples (slight noise around gravity)
    np.random.seed(42)
    for _ in range(50):
        # Accelerometer: ~9.81 m/s² (gravity) with minimal noise
        accel = (0.01 * np.random.randn(), 0.01 * np.random.randn(), 9.81 + 0.01 * np.random.randn())
        # Gyroscope: near zero
        gyro = (0.001 * np.random.randn(), 0.001 * np.random.randn(), 0.001 * np.random.randn())
        detector.add_sample(accel, gyro)

    p_stat = detector.get_stationary_probability()

    # Should have high probability of being stationary
    assert p_stat > 0.8, f"Expected P(stat) > 0.8 for stationary samples, got {p_stat}"
    assert detector.is_stationary_hard(threshold=0.7)


def test_zupt_moving_detection():
    """Test that detector correctly identifies moving samples."""
    detector = ZuptDetector(window_size=50)

    # Add 50 moving samples with significant acceleration variation
    np.random.seed(43)
    for i in range(50):
        # Accelerometer: varying significantly
        accel = (2.0 * np.sin(i * 0.1), 1.5 * np.cos(i * 0.1), 9.81 + 1.0 * np.sin(i * 0.2))
        # Gyroscope: rotating
        gyro = (0.3 * np.sin(i * 0.15), 0.2 * np.cos(i * 0.15), 0.1 * np.sin(i * 0.1))
        detector.add_sample(accel, gyro)

    p_stat = detector.get_stationary_probability()

    # Should have low probability of being stationary
    assert p_stat < 0.3, f"Expected P(stat) < 0.3 for moving samples, got {p_stat}"
    assert not detector.is_stationary_hard(threshold=0.7)


def test_zupt_insufficient_data():
    """Test behavior with insufficient samples."""
    detector = ZuptDetector(window_size=50)

    # Add only 10 samples (less than window_size)
    for _ in range(10):
        detector.add_sample((0.0, 0.0, 9.81), (0.0, 0.0, 0.0))

    p_stat = detector.get_stationary_probability()

    # Should return 0.0 when insufficient data
    assert p_stat == 0.0


def test_zupt_adaptive_covariance():
    """Test adaptive covariance matrix scaling."""
    detector = ZuptDetector(window_size=50)

    # Add stationary samples
    np.random.seed(44)
    for _ in range(50):
        accel = (0.01 * np.random.randn(), 0.01 * np.random.randn(), 9.81 + 0.01 * np.random.randn())
        gyro = (0.001 * np.random.randn(), 0.001 * np.random.randn(), 0.001 * np.random.randn())
        detector.add_sample(accel, gyro)

    R = detector.get_adaptive_zupt_covariance(base_variance=0.01, gamma=2.0)

    # Should be 3x3 diagonal
    assert R.shape == (3, 3)
    assert np.allclose(R, np.diag(np.diag(R))), "R should be diagonal"

    # Since P(stat) is high, covariance should be close to base_variance
    p_stat = detector.get_stationary_probability()
    expected_var = 0.01 / (p_stat**2.0 + 1e-6)

    assert np.allclose(R[0, 0], expected_var, rtol=0.1)


def test_zupt_temporal_consistency():
    """Test temporal smoothing of probability estimates."""
    detector = ZuptDetector(window_size=50)

    # Fill with stationary samples
    np.random.seed(45)
    for _ in range(50):
        detector.add_sample((0.0, 0.0, 9.81), (0.0, 0.0, 0.0))

    p1 = detector.get_stationary_probability()

    # Add one noisy sample
    detector.add_sample((5.0, 5.0, 9.81), (1.0, 1.0, 1.0))

    p2 = detector.get_stationary_probability()

    # Probability shouldn't change drastically due to temporal smoothing
    # (though it will decrease slightly)
    assert abs(p2 - p1) < 0.5, "Temporal smoothing should prevent abrupt changes"


def test_zupt_reset():
    """Test reset functionality."""
    detector = ZuptDetector(window_size=50)

    # Add samples
    for _ in range(50):
        detector.add_sample((0.0, 0.0, 9.81), (0.0, 0.0, 0.0))

    p_before = detector.get_stationary_probability()
    assert p_before > 0.0

    # Reset
    detector.reset()

    # Buffers should be empty
    assert len(detector.accel_norms) == 0
    assert len(detector.gyro_norms) == 0
    assert detector.last_probability == 0.0

    # Probability should return to 0.0 (insufficient data)
    p_after = detector.get_stationary_probability()
    assert p_after == 0.0


def test_zupt_transition_stationary_to_moving():
    """Test transition from stationary to moving state."""
    detector = ZuptDetector(window_size=50)

    # Start stationary
    np.random.seed(46)
    for _ in range(50):
        accel = (0.01 * np.random.randn(), 0.01 * np.random.randn(), 9.81 + 0.01 * np.random.randn())
        gyro = (0.001 * np.random.randn(), 0.001 * np.random.randn(), 0.001 * np.random.randn())
        detector.add_sample(accel, gyro)

    p_stat_initial = detector.get_stationary_probability()
    assert p_stat_initial > 0.7

    # Transition to moving
    for i in range(50):
        accel = (3.0 * np.sin(i * 0.1), 2.0 * np.cos(i * 0.1), 9.81 + 2.0 * np.sin(i * 0.2))
        gyro = (0.5 * np.sin(i * 0.15), 0.4 * np.cos(i * 0.15), 0.2 * np.sin(i * 0.1))
        detector.add_sample(accel, gyro)

    p_stat_final = detector.get_stationary_probability()
    assert p_stat_final < 0.6, f"Should transition to moving state, got P(stat)={p_stat_final}"

    # Verify transition happened
    assert p_stat_final < p_stat_initial


def test_zupt_covariance_high_uncertainty_when_moving():
    """Test that covariance is very high when moving (effectively disabling ZUPT)."""
    detector = ZuptDetector(window_size=50)

    # Add moving samples
    np.random.seed(47)
    for i in range(50):
        accel = (5.0 * np.sin(i * 0.1), 3.0, 9.81)
        gyro = (1.0, 0.5, 0.3)
        detector.add_sample(accel, gyro)

    R = detector.get_adaptive_zupt_covariance(base_variance=0.01, gamma=2.0)

    # Covariance should be very large (much larger than base_variance)
    assert R[0, 0] > 1.0, "Moving covariance should be >> base_variance"
