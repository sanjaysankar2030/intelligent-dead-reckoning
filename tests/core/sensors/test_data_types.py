"""
Unit tests for sensor data structures.
"""

import pytest
from core.sensors.data_types import (
    ImuSample,
    GnssFix,
    MagSample,
    BaroSample,
    SensorType,
    TimestampSyncError,
    lin_interp,
    slerp,
)


def test_imu_sample_creation():
    """Test IMU sample creation and immutability."""
    sample = ImuSample(
        timestamp_ns=1234567890,
        accel_m_s2=(1.0, 2.0, 9.81),
        gyro_rad_s=(0.1, 0.2, 0.3)
    )

    assert sample.timestamp_ns == 1234567890
    assert sample.accel_m_s2 == (1.0, 2.0, 9.81)
    assert sample.gyro_rad_s == (0.1, 0.2, 0.3)

    # Test immutability
    with pytest.raises(AttributeError):
        sample.timestamp_ns = 999999999


def test_gnss_fix_creation():
    """Test GNSS fix creation."""
    fix = GnssFix(
        timestamp_ns=1234567890,
        latitude_deg=12.9716,
        longitude_deg=77.5946,
        altitude_m=920.5,
        velocity_ned_mps=(10.0, 0.0, -0.1),
        horizontal_accuracy_m=2.5,
        vertical_accuracy_m=3.0,
        speed_accuracy_mps=0.2,
        satellite_count=12
    )

    assert fix.latitude_deg == 12.9716
    assert fix.longitude_deg == 77.5946
    assert fix.altitude_m == 920.5
    assert fix.velocity_ned_mps == (10.0, 0.0, -0.1)
    assert fix.horizontal_accuracy_m == 2.5
    assert fix.vertical_accuracy_m == 3.0
    assert fix.speed_accuracy_mps == 0.2
    assert fix.satellite_count == 12


def test_mag_sample_creation():
    """Test magnetometer sample creation."""
    sample = MagSample(
        timestamp_ns=1234567890,
        magnetic_field_ut=(20.0, -15.0, 45.0)
    )

    assert sample.timestamp_ns == 1234567890
    assert sample.magnetic_field_ut == (20.0, -15.0, 45.0)


def test_baro_sample_creation():
    """Test barometer sample creation."""
    sample = BaroSample(
        timestamp_ns=1234567890,
        pressure_pa=101325.0
    )

    assert sample.timestamp_ns == 1234567890
    assert sample.pressure_pa == 101325.0


def test_sensor_type_enum():
    """Test SensorType enumeration."""
    assert SensorType.ACCELEROMETER.name == "ACCELEROMETER"
    assert SensorType.GYROSCOPE.name == "GYROSCOPE"
    assert SensorType.MAGNETOMETER.name == "MAGNETOMETER"
    assert SensorType.GNSS.name == "GNSS"
    assert SensorType.BAROMETER.name == "BAROMETER"


def test_lin_interp():
    """Test linear interpolation function."""
    # Basic test
    assert lin_interp(0, 0, 10, 0, 20) == 0.0
    assert lin_interp(10, 0, 10, 0, 20) == 20.0
    assert lin_interp(5, 0, 10, 0, 20) == 10.0
    assert lin_interp(2.5, 0, 10, 0, 20) == 5.0

    # Edge case: same start and end time
    assert lin_interp(5, 0, 0, 10, 20) == 10.0  # Should return v0


def test_slerp():
    """Test spherical linear interpolation for quaternions."""
    # Identity quaternion
    q0 = (1.0, 0.0, 0.0, 0.0)
    q1 = (1.0, 0.0, 0.0, 0.0)

    # Interpolating between identical quaternions should give identity
    result = slerp(q0, q1, 0.5)
    assert result == pytest.approx((1.0, 0.0, 0.0, 0.0), abs=1e-6)

    # 90-degree rotation around Z axis
    import math
    q0 = (1.0, 0.0, 0.0, 0.0)  # Identity
    q1 = (math.cos(math.pi/4), 0.0, 0.0, math.sin(math.pi/4))  # 90-degree around Z

    # Halfway should be 45-degree rotation
    result = slerp(q0, q1, 0.5)
    expected_w = math.cos(math.pi/8)
    expected_z = math.sin(math.pi/8)
    assert result == pytest.approx((expected_w, 0.0, 0.0, expected_z), abs=1e-6)


if __name__ == "__main__":
    pytest.main([__file__])