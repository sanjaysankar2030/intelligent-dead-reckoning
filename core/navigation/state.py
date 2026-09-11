"""
Navigation state definitions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import numpy as np
from typing import Tuple

from core.alignment.quaternion_utils import Quat

@dataclass
class NavState:
    """
    Deterministic navigation state of the system in the Local Tangent Plane (NED frame).
    
    Frames:
      - Attitude represents the rotation from Vehicle frame to Navigation (NED) frame.
      - Position and Velocity are in the Navigation (NED) frame.
      - Biases are in the Sensor/Phone frame.
    """
    timestamp_ns: int
    
    # Position in Navigation frame (NED) [m, m, m]
    position_m: Tuple[float, float, float]
    
    # Velocity in Navigation frame (NED) [m/s, m/s, m/s]
    velocity_mps: Tuple[float, float, float]
    
    # Attitude quaternion: Vehicle frame TO Navigation frame (NED) [w, x, y, z]
    attitude_q_v2n: Quat
    
    # Accelerometer dynamic bias in Sensor frame [m/s^2, m/s^2, m/s^2]
    # (Does not include static calibration biases removed in Phase 3)
    accel_bias_mps2: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    
    # Gyroscope dynamic bias in Sensor frame [rad/s, rad/s, rad/s]
    # (Does not include static calibration biases removed in Phase 3)
    gyro_bias_radps: Tuple[float, float, float] = (0.0, 0.0, 0.0)

    @classmethod
    def create_initial(
        cls,
        timestamp_ns: int,
        position_m: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        velocity_mps: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        attitude_q_v2n: Quat = (1.0, 0.0, 0.0, 0.0)
    ) -> NavState:
        """Create a default initial state."""
        return cls(
            timestamp_ns=timestamp_ns,
            position_m=position_m,
            velocity_mps=velocity_mps,
            attitude_q_v2n=attitude_q_v2n,
            accel_bias_mps2=(0.0, 0.0, 0.0),
            gyro_bias_radps=(0.0, 0.0, 0.0)
        )
