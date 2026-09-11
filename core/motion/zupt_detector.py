"""
Zero-Velocity Update (ZUPT) Detector using soft probabilistic thresholds.

Estimates P(stationary) based on:
- Accelerometer magnitude variance
- Gyroscope magnitude variance
- Temporal consistency
"""
from __future__ import annotations

import math
from collections import deque
from typing import Tuple
import numpy as np


class ZuptDetector:
    """
    Soft ZUPT detector that estimates stationary probability P(stat) ∈ [0, 1].

    Unlike hard thresholding, this provides continuous probability that allows
    adaptive measurement covariance scaling: R_zupt = R_base / (P_stat^gamma + epsilon).
    """

    def __init__(
        self,
        window_size: int = 50,
        accel_var_threshold: float = 0.5,  # (m/s²)²
        gyro_var_threshold: float = 0.01,  # (rad/s)²
        accel_mean_threshold: float = 0.3,  # m/s² deviation from gravity norm
        gyro_mean_threshold: float = 0.05,  # rad/s mean
    ):
        """
        Args:
            window_size: Number of samples for rolling statistics.
            accel_var_threshold: Variance threshold below which accel is "still".
            gyro_var_threshold: Variance threshold below which gyro is "still".
            accel_mean_threshold: Deviation from 9.81 m/s² indicating motion.
            gyro_mean_threshold: Mean gyro magnitude indicating rotation.
        """
        self.window_size = window_size
        self.accel_var_thresh = accel_var_threshold
        self.gyro_var_thresh = gyro_var_threshold
        self.accel_mean_thresh = accel_mean_threshold
        self.gyro_mean_thresh = gyro_mean_threshold

        # Rolling buffers for accelerometer and gyroscope norms
        self.accel_norms: deque = deque(maxlen=window_size)
        self.gyro_norms: deque = deque(maxlen=window_size)

        # Temporal consistency tracking
        self.last_probability: float = 0.0
        self.consistency_alpha: float = 0.6  # Temporal smoothing factor (0.6 = 40% new, 60% history)

    def add_sample(self, accel: Tuple[float, float, float], gyro: Tuple[float, float, float]) -> None:
        """
        Add a sensor sample to the rolling window.

        Args:
            accel: Acceleration in body frame (m/s²).
            gyro: Angular velocity in body frame (rad/s).
        """
        accel_norm = math.sqrt(accel[0]**2 + accel[1]**2 + accel[2]**2)
        gyro_norm = math.sqrt(gyro[0]**2 + gyro[1]**2 + gyro[2]**2)

        self.accel_norms.append(accel_norm)
        self.gyro_norms.append(gyro_norm)

    def get_stationary_probability(self) -> float:
        """
        Compute the soft stationary probability P(stat) ∈ [0, 1].

        Returns:
            Probability that the sensor is stationary.
        """
        if len(self.accel_norms) < self.window_size:
            # Insufficient data: assume uncertain motion
            return 0.0

        # Convert to numpy for efficient computation
        accel_arr = np.array(self.accel_norms)
        gyro_arr = np.array(self.gyro_norms)

        # Compute statistics
        accel_var = float(np.var(accel_arr))
        gyro_var = float(np.var(gyro_arr))
        accel_mean = float(np.mean(accel_arr))
        gyro_mean = float(np.mean(gyro_arr))

        # Accelerometer deviation from gravity norm (9.80665 m/s²)
        accel_dev = abs(accel_mean - 9.80665)

        # Individual probabilities using sigmoid-like soft thresholds
        # P(stat | accel_var) = exp(-k * (var / thresh))
        # When var << thresh, P → 1; when var >> thresh, P → 0
        # Adjusted coefficients for better sensitivity

        p_accel_var = math.exp(-2.0 * (accel_var / self.accel_var_thresh))
        p_gyro_var = math.exp(-2.0 * (gyro_var / self.gyro_var_thresh))
        p_accel_mean = math.exp(-3.0 * (accel_dev / self.accel_mean_thresh))
        p_gyro_mean = math.exp(-3.0 * (gyro_mean / self.gyro_mean_thresh))

        # Combined probability (product model assumes independence)
        p_stat_raw = p_accel_var * p_gyro_var * p_accel_mean * p_gyro_mean

        # Apply temporal consistency smoothing only if we have history
        if self.last_probability > 0.0:
            p_stat = self.consistency_alpha * self.last_probability + (1 - self.consistency_alpha) * p_stat_raw
        else:
            # First meaningful estimate: use raw value
            p_stat = p_stat_raw

        # Clamp to valid probability range
        p_stat = float(np.clip(p_stat, 0.0, 1.0))

        self.last_probability = p_stat

        return p_stat

    def is_stationary_hard(self, threshold: float = 0.7) -> bool:
        """
        Hard binary decision for backward compatibility.

        Args:
            threshold: Probability threshold above which to declare stationary.

        Returns:
            True if P(stat) > threshold.
        """
        return self.get_stationary_probability() > threshold

    def get_adaptive_zupt_covariance(
        self,
        base_variance: float = 0.01,
        gamma: float = 2.0,
        epsilon: float = 1e-6
    ) -> np.ndarray:
        """
        Compute adaptive ZUPT measurement covariance based on stationary probability.

        R_zupt = diag(sigma_base² / (P_stat^gamma + epsilon))

        When P_stat → 1 (very stationary), R_zupt → sigma_base² (low uncertainty).
        When P_stat → 0 (moving), R_zupt → ∞ (high uncertainty, effectively ignored).

        Args:
            base_variance: Baseline measurement variance when fully stationary.
            gamma: Exponent penalizing uncertain detections (≥ 2 recommended).
            epsilon: Regularization to prevent division by zero.

        Returns:
            3x3 diagonal covariance matrix for 3D velocity ZUPT.
        """
        p_stat = self.get_stationary_probability()

        # Scale variance inversely with probability
        var = base_variance / (p_stat**gamma + epsilon)

        # Cap maximum variance to prevent numerical issues
        var = min(var, 1e6)

        return np.eye(3) * var

    def reset(self) -> None:
        """Clear the rolling buffers and reset temporal state."""
        self.accel_norms.clear()
        self.gyro_norms.clear()
        self.last_probability = 0.0
