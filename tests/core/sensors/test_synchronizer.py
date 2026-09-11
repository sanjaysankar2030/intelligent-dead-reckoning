"""
Unit tests for sensor synchronizer.
"""

import pytest
import time
from unittest.mock import patch

from core.sensors.data_types import ImuSample, GnssFix, MagSample, BaroSample
from core.sensors.synchronizer import Synchronizer, SensorSnapshot


def test_synchronizer_initialization():
    """Test synchronizer initialization with default and custom parameters."""
    sync = Synchronizer()
    assert sync is not None
    assert hasattr(sync, 'imu_buffer')
    assert hasattr(sync, 'gnss_buffer')
    assert hasattr(sync, 'mag_buffer')
    assert hasattr(sync, 'baro_buffer')

    # Test custom buffer sizes
    sync_custom = Synchronizer(
        imu_buffer_size=500,
        gnss_buffer_size=50,
        mag_buffer_size=250,
        baro_buffer_size=100,
        max_interpolation_age_s=0.05
    )
    assert sync_custom is not None


def test_add_and_get_samples():
    """Test adding samples and retrieving them."""
    sync = Synchronizer()

    # Add IMU sample
    imu_sample = ImuSample(
        timestamp_ns=1000000000,
        accel_m_s2=(1.0, 0.0, 9.81),
        gyro_rad_s=(0.0, 0.1, 0.0)
    )
    sync.imu_buffer().append(imu_sample)

    # Add GNSS fix
    gnss_fix = GnssFix(
        timestamp_ns=1000000000,
        latitude_deg=12.9716,
        longitude_deg=77.5946,
        altitude_m=920.5,
        velocity_ned_mps=(0.0, 0.0, 0.0),
        horizontal_accuracy_m=2.0,
        vertical_accuracy_m=3.0,
        speed_accuracy_mps=0.1,
        satellite_count=10
    )
    sync.gnss_buffer().append(gnss_fix)

    # Add magnetometer sample
    mag_sample = MagSample(
        timestamp_ns=1000000000,
        magnetic_field_ut=(20.0, 0.0, 45.0)
    )
    sync.mag_buffer().append(mag_sample)

    # Add barometer sample
    baro_sample = BaroSample(
        timestamp_ns=1000000000,
        pressure_pa=101325.0
    )
    sync.baro_buffer().append(baro_sample)

    # Get latest from each buffer
    assert sync.imu_buffer().get_latest() == imu_sample
    assert sync.gnss_buffer().get_latest() == gnss_fix
    assert sync.mag_buffer().get_latest() == mag_sample
    assert sync.baro_buffer().get_latest() == baro_sample


def test_find_closest():
    """Test finding closest samples in buffer."""
    sync = Synchronizer()
    buffer = sync.imu_buffer()

    # Add samples at known times
    t0 = 1000000000
    t1 = 2000000000
    t2 = 3000000000

    buffer.append(ImuSample(timestamp_ns=t0, accel_m_s2=(0,0,0), gyro_rad_s=(0,0,0)))
    buffer.append(ImuSample(timestamp_ns=t1, accel_m_s2=(1,0,0), gyro_rad_s=(0,1,0)))
    buffer.append(ImuSample(timestamp_ns=t2, accel_m_s2=(0,1,0), gyro_rad_s=(0,0,1)))

    # Test exact match
    left, right = buffer.find_closest(t1)
    assert left is not None and left.timestamp_ns == t1
    assert right is not None and right.timestamp_ns == t1

    # Test between samples
    left, right = buffer.find_closest(1500000000)  # Midway between t0 and t1
    assert left is not None and left.timestamp_ns == t0
    assert right is not None and right.timestamp_ns == t1

    # Test before first sample
    left, right = buffer.find_closest(500000000)
    assert left is None
    assert right is not None and right.timestamp_ns == t0

    # Test after last sample
    left, right = buffer.find_closest(3500000000)
    assert left is not None and left.timestamp_ns == t2
    assert right is None


def test_linear_interpolation():
    """Test linear interpolation helper."""
    from core.sensors.synchronizer import lin_interp

    assert lin_interp(0, 0, 10, 0, 20) == 0.0
    assert lin_interp(10, 0, 10, 0, 20) == 20.0
    assert lin_interp(5, 0, 10, 0, 20) == 10.0
    assert lin_interp(2.5, 0, 10, 0, 20) == 5.0


def test_snapshot_generation():
    """Test generating time-synchronized snapshots."""
    # Mock time to make test data appear recent
    mock_time = 1000000000 + 50000000  # 50ms after base_time
    with patch('time.time_ns', return_value=mock_time):
        sync = Synchronizer(max_interpolation_age_s=1.0)  # Allow 1 second max age

        base_time = 1000000000  # 1 second epoch

        # Add IMU samples
        sync.imu_buffer().append(ImuSample(
            timestamp_ns=base_time,
            accel_m_s2=(1.0, 0.0, 9.81),
            gyro_rad_s=(0.0, 0.1, 0.0)
        ))
        sync.imu_buffer().append(ImuSample(
            timestamp_ns=base_time + 10000000,  # 10ms later
            accel_m_s2=(2.0, 0.0, 9.81),
            gyro_rad_s=(0.0, 0.2, 0.0)
        ))

        # Add GNSS fix
        sync.gnss_buffer().append(GnssFix(
            timestamp_ns=base_time,
            latitude_deg=12.9716,
            longitude_deg=77.5946,
            altitude_m=920.5,
            velocity_ned_mps=(0.0, 0.0, 0.0),
            horizontal_accuracy_m=2.0,
            vertical_accuracy_m=3.0,
            speed_accuracy_mps=0.1,
            satellite_count=10
        ))

        # Add magnetometer sample
        sync.mag_buffer().append(MagSample(
            timestamp_ns=base_time,
            magnetic_field_ut=(20.0, 0.0, 45.0)
        ))

        # Add barometer sample
        sync.baro_buffer().append(BaroSample(
            timestamp_ns=base_time,
            pressure_pa=101325.0
        ))

        # Get snapshot at exact time
        snapshot = sync.get_snapshot(base_time)
        assert snapshot is not None
        assert snapshot.timestamp_ns == base_time
        assert snapshot.imu.accel_m_s2 == (1.0, 0.0, 9.81)
        assert snapshot.gnss is not None
        assert snapshot.gnss.latitude_deg == 12.9716
        assert snapshot.mag.magnetic_field_ut == (20.0, 0.0, 45.0)
        assert snapshot.baro.pressure_pa == 101325.0

        # Get snapshot at interpolated time (midway between IMU samples)
        interp_time = base_time + 5000000  # 5ms after first IMU sample
        snapshot = sync.get_snapshot(interp_time)
        assert snapshot is not None
        assert snapshot.timestamp_ns == interp_time
        # IMU should be interpolated: accel=(1.5, 0, 9.81), gyro=(0, 0.15, 0)
        assert snapshot.imu.accel_m_s2[0] == pytest.approx(1.5, abs=1e-6)
        assert snapshot.imu.accel_m_s2[1] == pytest.approx(0.0, abs=1e-6)
        assert snapshot.imu.accel_m_s2[2] == pytest.approx(9.81, abs=1e-6)
        assert snapshot.imu.gyro_rad_s[0] == pytest.approx(0.0, abs=1e-6)
        assert snapshot.imu.gyro_rad_s[1] == pytest.approx(0.15, abs=1e-6)
        assert snapshot.imu.gyro_rad_s[2] == pytest.approx(0.0, abs=1e-6)

        # Other sensors should be identical (no change in input)
        assert snapshot.gnss is not None
        assert snapshot.gnss.latitude_deg == 12.9716
        assert snapshot.mag.magnetic_field_ut == (20.0, 0.0, 45.0)
        assert snapshot.baro.pressure_pa == 101325.0


def test_snapshot_with_missing_data():
    """Test snapshot generation when some data is missing."""
    # Mock time to make test data appear recent
    mock_time = 1000000000 + 50000000  # 50ms after base_time
    with patch('time.time_ns', return_value=mock_time):
        sync = Synchronizer(max_interpolation_age_s=1.0)

        base_time = 1000000000

        # Add only IMU and mag (no GNSS or baro)
        sync.imu_buffer().append(ImuSample(
            timestamp_ns=base_time,
            accel_m_s2=(1.0, 0.0, 9.81),
            gyro_rad_s=(0.0, 0.1, 0.0)
        ))
        sync.mag_buffer().append(MagSample(
            timestamp_ns=base_time,
            magnetic_field_ut=(20.0, 0.0, 45.0)
        ))
        # Note: No baro sample added

        # Should return None because baro is missing
        snapshot = sync.get_snapshot(base_time)
        assert snapshot is None

        # Add baro now
        sync.baro_buffer().append(BaroSample(
            timestamp_ns=base_time,
            pressure_pa=101325.0
        ))

        # Should work now (GNSS can be None)
        snapshot = sync.get_snapshot(base_time)
        assert snapshot is not None
        assert snapshot.timestamp_ns == base_time
        assert snapshot.imu is not None
        assert snapshot.mag is not None
        assert snapshot.baro is not None
        assert snapshot.gnss is None  # This is allowed


def test_stale_data_rejection():
    """Test that stale data is rejected based on max_interpolation_age."""
    # Mock time to make test data appear recent initially
    mock_time = 1000000000 + 50000000  # 50ms after base_time
    with patch('time.time_ns', return_value=mock_time):
        sync = Synchronizer(max_interpolation_age_s=0.1)  # 100ms max age

        base_time = 1000000000

        # Add old IMU sample (200ms old) - but make it appear recent by adjusting mock time
        old_time = base_time - 200000000  # 200ms in the past
        sync.imu_buffer().append(ImuSample(
            timestamp_ns=old_time,
            accel_m_s2=(1.0, 0.0, 9.81),
            gyro_rad_s=(0.0, 0.1, 0.0)
        ))

        # Add recent mag and baro (make them appear recent too)
        sync.mag_buffer().append(MagSample(
            timestamp_ns=base_time,
            magnetic_field_ut=(20.0, 0.0, 45.0)
        ))
        sync.baro_buffer().append(BaroSample(
            timestamp_ns=base_time,
            pressure_pa=101325.0
        ))

        # Should return None because IMU data is too stale (200ms > 100ms max)
        snapshot = sync.get_snapshot(base_time)
        assert snapshot is None

        # Add recent IMU sample
        sync.imu_buffer().append(ImuSample(
            timestamp_ns=base_time,
            accel_m_s2=(2.0, 0.0, 9.81),
            gyro_rad_s=(0.0, 0.2, 0.0)
        ))

        # Should work now
        snapshot = sync.get_snapshot(base_time)
        assert snapshot is not None
        assert snapshot.imu.accel_m_s2 == (2.0, 0.0, 9.81)
        assert snapshot.imu.gyro_rad_s == (0.0, 0.2, 0.0)


def test_clear_all():
    """Test clearing all buffers."""
    sync = Synchronizer()

    # Add samples to all buffers
    sync.imu_buffer().append(ImuSample(
        timestamp_ns=1000000000,
        accel_m_s2=(1.0, 0.0, 9.81),
        gyro_rad_s=(0.0, 0.1, 0.0)
    ))
    sync.gnss_buffer().append(GnssFix(
        timestamp_ns=1000000000,
        latitude_deg=12.9716,
        longitude_deg=77.5946,
        altitude_m=920.5,
        velocity_ned_mps=(0.0, 0.0, 0.0),
        horizontal_accuracy_m=2.0,
        vertical_accuracy_m=3.0,
        speed_accuracy_mps=0.1,
        satellite_count=10
    ))
    sync.mag_buffer().append(MagSample(
        timestamp_ns=1000000000,
        magnetic_field_ut=(20.0, 0.0, 45.0)
    ))
    sync.baro_buffer().append(BaroSample(
        timestamp_ns=1000000000,
        pressure_pa=101325.0
    ))

    # Verify buffers have data
    assert len(sync.imu_buffer()) == 1
    assert len(sync.gnss_buffer()) == 1
    assert len(sync.mag_buffer()) == 1
    assert len(sync.baro_buffer()) == 1

    # Clear all
    sync.clear_all()

    # Verify buffers are empty
    assert len(sync.imu_buffer()) == 0
    assert len(sync.gnss_buffer()) == 0
    assert len(sync.mag_buffer()) == 0
    assert len(sync.baro_buffer()) == 0


if __name__ == "__main__":
    pytest.main([__file__])