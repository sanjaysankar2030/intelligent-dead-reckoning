"""Sensor I/O abstraction layer.

This module defines:
- Immutable sensor data structures (ImuSample, GnssFix, MagSample, BaroSample)
- SensorType enumeration
- Timestamp synchronization utilities
- Ring buffer for time-aligned multi-sensor streaming
- CSV/MessagePack serialization for replay
"""