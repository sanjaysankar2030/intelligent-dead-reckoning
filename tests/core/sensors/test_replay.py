"""
Unit tests for sensor replay functionality.
"""

import pytest
import tempfile
import os
from pathlib import Path

from core.sensors.data_types import ImuSample
from core.sensors.replay import SensorLogger, SensorReplayIterator, ReplayConfig, create_sample_log


def test_sensor_logger_csv():
    """Test logging to CSV format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "test_log.csv"

        # Create logger and log some samples
        with SensorLogger(log_path, format="csv") as logger:
            # Log a few IMU samples
            for i in range(5):
                sample = ImuSample(
                    timestamp_ns=1000000000 + i * 10000000,  # 10ms apart
                    accel_m_s2=(1.0 + i * 0.1, 0.0, 9.81),
                    gyro_rad_s=(0.0, 0.1 * i, 0.0)
                )
                logger.log_imu(sample)

        # Verify file was created and has correct content
        assert log_path.exists()
        content = log_path.read_text()
        lines = content.strip().split('\n')

        # Should have header + 5 data lines
        assert len(lines) == 6
        assert lines[0] == 'timestamp_ns,sensor_type,accel_x,accel_y,accel_z,gyro_x,gyro_y,gyro_z,mag_x,mag_y,mag_z,gnss_lat,gnss_lon,gnss_alt,gnss_vel_n,gnss_vel_e,gnss_vel_d,gnss_h_acc,gnss_v_acc,gnss_speed_acc,gnss_satellites,baro_pressure'

        # Check first data line
        parts = lines[1].split(',')
        assert parts[0] == '1000000000'  # timestamp
        assert parts[1] == 'IMU'         # sensor type
        assert parts[2] == '1.0'         # accel_x
        assert parts[5] == '0.0'         # gyro_x


def test_sensor_logger_binary():
    """Test logging to binary format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "test_log.bin"

        # Create logger and log some samples
        with SensorLogger(log_path, format="bin") as logger:
            # Log a few IMU samples
            for i in range(3):
                sample = ImuSample(
                    timestamp_ns=1000000000 + i * 10000000,  # 10ms apart
                    accel_m_s2=(1.0 + i * 0.1, 0.0, 9.81),
                    gyro_rad_s=(0.0, 0.1 * i, 0.0)
                )
                logger.log_imu(sample)

        # Verify file was created
        assert log_path.exists()
        assert log_path.stat().st_size > 8  # Should be larger than just header

        # Try to read it back (basic test)
        with open(log_path, 'rb') as f:
            header = f.read(8)
            assert header.startswith(b'DRLog\x00\x01')  # Magic header: DRLog + version 0x0001


def test_create_sample_log():
    """Test synthetic log generation."""
    samples = create_sample_log(duration_s=1.0, imu_rate_hz=10)

    # Should have 10 samples (1 second * 10 Hz)
    assert len(samples) == 10

    # Check first and last samples
    assert isinstance(samples[0], ImuSample)
    assert isinstance(samples[-1], ImuSample)

    # Timestamps should be increasing
    for i in range(1, len(samples)):
        assert samples[i].timestamp_ns > samples[i-1].timestamp_ns


def test_replay_config():
    """Test replay configuration."""
    config = ReplayConfig(
        playback_speed=2.0,
        loop=True,
        inject_gnss_blackout=True,
        blackout_start_s=5.0,
        blackout_duration_s=10.0,
        inject_sensor_noise=True,
        noise_accel_std=0.01,
        noise_gyro_std=0.001,
        noise_mag_std=0.1,
        noise_baro_std=1.0
    )

    assert config.playback_speed == 2.0
    assert config.loop is True
    assert config.inject_gnss_blackout is True
    assert config.blackout_start_s == 5.0
    assert config.blackout_duration_s == 10.0
    assert config.inject_sensor_noise is True
    assert config.noise_accel_std == 0.01
    assert config.noise_gyro_std == 0.001
    assert config.noise_mag_std == 0.1
    assert config.noise_baro_std == 1.0


def test_replay_iterator_initialization():
    """Test replay iterator initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "test_log.bin"

        # Create a simple log file first
        with SensorLogger(log_path, format="bin") as logger:
            sample = ImuSample(
                timestamp_ns=1000000000,
                accel_m_s2=(1.0, 0.0, 9.81),
                gyro_rad_s=(0.0, 0.1, 0.0)
            )
            logger.log_imu(sample)

        # Initialize replay iterator
        config = ReplayConfig(playback_speed=1.0)
        iterator = SensorReplayIterator(log_path, config)

        assert iterator is not None
        assert iterator.file_path == log_path
        assert iterator.config == config


if __name__ == "__main__":
    pytest.main([__file__])