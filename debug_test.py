from core.alignment.alignment_engine import AlignmentEngine
from tests.core.alignment.test_alignment_engine import create_imu_sample, create_gnss_fix

engine = AlignmentEngine(gravity_window_size=5, gravity_min_samples=5, min_confidence_for_aligned=0.3)

for _ in range(5):
    engine.add_imu_sample(create_imu_sample((0.0, 0.0, 9.80665)))

for _ in range(5):
    used, status = engine.add_gnss_fix(create_gnss_fix(0.0, 10.0))
    print(f"used={used}, conf={status.confidence}, state={status.state}, head_conf={status.heading_confidence}")
