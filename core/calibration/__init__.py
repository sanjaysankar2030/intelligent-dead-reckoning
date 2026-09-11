"""Sensor calibration engine.

This module provides:
- Static bias estimation for accelerometers and gyroscopes
- Magnetometer hard/soft iron calibration (ellipsoid fitting)
- Scale factor estimation where applicable
- Online calibration update capabilities
- Temperature compensation hooks
"""