# Requirements Traceability Matrix

**Project:** SIH PS 26168 — AI/ML based Intelligent Dead Reckoning System  
**Document Version:** 1.0.0  
**Date:** 2026-09-10  

---

## 1. Traceability Summary

| PS 26168 Requirement Description | System Module | Implementation Class / Component | Verification / Test Suite | Target Phase |
|---|---|---|---|---|
| **1. GNSS-Denied Dead Reckoning** | `core/navigation/` + `core/filters/` | `InertialMechanizer`, `ErrorStateKalmanFilter` | `tests/test_eskf.py`, `tests/test_dead_reckoning.py` | Phase 5, 6 |
| **2. Multi-Rate Input Support (10 Hz & 200 Hz)** | `core/sensors/` + `apps/edge_daemon/` | `SensorSynchronizer`, `EdgeNavigationEngine` | `tests/test_sync.py`, `tests/test_edge_rate.py` | Phase 2, 21 |
| **3. Smartphone Sensor Acquisition** | `apps/android/` | Android SensorEventListener, LocationListener | Android Instrument Tests | Phase 2, 20 |
| **4. Arbitrary Phone Mounting / Alignment** | `core/alignment/` | `PhoneToVehicleAligner` | `tests/test_alignment.py` | Phase 4 |
| **5. Sensor Bias & Calibration** | `core/calibration/` | `SensorCalibrator`, `MagnetometerCalibrator` | `tests/test_calibration.py` | Phase 3 |
| **6. Vehicle Awareness (Car, Motorcycle, Scooter)** | `core/models/` + `core/constraints/` | `VehicleClassifier`, `AdaptiveNHC` | `tests/test_vehicle_classifier.py`, `tests/test_nhc.py` | Phase 11, 12 |
| **7. ML Motion State & Velocity Estimation** | `core/models/` | `MotionIntelligenceModel` (TCN/GRU) | `tests/test_motion_model.py` | Phase 10 |
| **8. Soft / Adaptive ZUPT** | `core/constraints/` | `SoftZuptEngine` | `tests/test_zupt.py` | Phase 9 |
| **9. Vibration & Roughness Analysis** | `core/motion/` | `VibrationAnalyzer` | `tests/test_vibration.py` | Phase 8 |
| **10. Magnetic Disturbance Rejection** | `core/motion/` | `MagneticReliabilityMonitor` | `tests/test_magnetic.py` | Phase 13 |
| **11. Seamless GNSS / DR Transitions** | `core/gnss/` | `GnssIntegrityManager`, `TransitionFader` | `tests/test_gnss_transitions.py` | Phase 7 |
| **12. Multi-Hypothesis Map Matching** | `core/map/` | `MapMatcher`, `MultiHypothesisTracker` | `tests/test_map_matching.py` | Phase 14, 15 |
| **13. Multi-Level Parking Disambiguation** | `core/map/` | `VerticalDisambiguator` | `tests/test_vertical_resolver.py` | Phase 15 |
| **14. Navigation Integrity & Uncertainty Reporting**| `core/integrity/` | `NavigationIntegrityEngine` | `tests/test_integrity.py` | Phase 16 |
| **15. Deterministic Sensor Replay & Simulation** | `tools/replay/` + `tools/simulator/` | `SensorReplayer`, `GnssOutageSimulator` | `tests/test_replay.py`, `tests/test_simulator.py` | Phase 2, 7 |
| **16. Benchmark & Ablation Evaluation** | `tools/evaluation/` + `tools/ablation/` | `TrajectoryEvaluator`, `AblationRunner` | `tests/test_evaluation_metrics.py` | Phase 17, 19 |
| **17. 1% Trajectory Drift Objective** | Full System Integration | Comprehensive System Pipeline | `tools/evaluation/benchmark_iovnbd.py` | Phase 17, 19 |
| **18. Real-Time Web Telemetry Dashboard** | `apps/web_dashboard/` | FastAPI WebSocket Telemetry Server & UI | `tests/test_api_endpoints.py` | Phase 22 |

---

## 2. Requirement Details & Acceptance Criteria

### REQ-01: Physics-Consistent Inertial Mechanization
- **Requirement:** Integrate specific forces and angular velocities via accurate strapdown equations in WGS-84 Local-Level NED coordinate frame.
- **Criteria:** Position, velocity, and quaternion orientation must remain smooth and numerically stable with exact unit quaternion normalization.

### REQ-02: Uncertainty-Aware Error-State Kalman Filter
- **Requirement:** 15-state nominal & error state propagation with dynamic accelerometer and gyroscope bias tracking.
- **Criteria:** Filter covariance matrix $P_k$ must remain positive semi-definite (enforced via Joseph form) and envelope true position errors during simulated blackouts.

### REQ-03: Machine Learning Motion Intelligence
- **Requirement:** Extract forward vehicle velocity $\hat{v}_{\text{fwd}}$ and motion probabilities ($P_{\text{stat}}$, $P_{\text{mag\_ok}}$) using a lightweight temporal neural network.
- **Criteria:** Velocity prediction error RMSE $< 0.8\text{ m/s}$ across validation datasets without hardcoding heuristics.

### REQ-04: Multi-Vehicle Adaptive Constraints
- **Requirement:** Dynamically adapt lateral and vertical Non-Holonomic Constraints (NHC) based on detected vehicle class (Car vs. Motorcycle/Scooter lean).
- **Criteria:** Motorcycle lean angles up to $35^\circ$ during turns must not cause filter divergence or false lateral velocity clamping.

### REQ-05: Dynamic Phone Reorientation Handling
- **Requirement:** Continuously estimate $R_p^v$ and detect if phone shifts or slips during transit.
- **Criteria:** Re-estimate orientation within 5 seconds of phone disturbance without crashing the navigation filter.

### REQ-06: Seamless GNSS Blackout Recovery
- **Requirement:** Prevent position / velocity step jumps when GNSS signal is lost or restored.
- **Criteria:** Outage recovery transition smoothly converges within 3 filter update cycles with zero discontinuous coordinate spikes.
