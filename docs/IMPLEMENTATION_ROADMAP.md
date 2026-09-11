# Implementation Roadmap & Phase Milestones

**Project:** SIH PS 26168 — AI/ML based Intelligent Dead Reckoning System  
**Execution Strategy:** Strict Sequential Phased Delivery with Rigorous Verification  
**Date:** 2026-09-10  

---

## Master Phase Schedule

```
Phase 0: Foundation & Audit                         [IN PROGRESS]
  └── Phase 1: Core Project Skeleton & Testing Infra
        └── Phase 2: Sensor Abstraction & Time Sync
              └── Phase 3: Calibration Engine (Biases, Iron Errors)
                    └── Phase 4: Phone-to-Vehicle Alignment
                          └── Phase 5: Deterministic INS Mechanization Baseline
                                └── Phase 6: Error-State Kalman Filter (ESKF)
                                      ├── Phase 7: GNSS Integrity & Smooth Transitions
                                      ├── Phase 8: Vibration Analysis & Spectral Engine
                                      ├── Phase 9: Intelligent Soft ZUPT
                                      ├── Phase 10: ML Forward Velocity Estimation
                                      ├── Phase 11: Vehicle Classification (Car/Bike/Scooter)
                                      ├── Phase 12: Vehicle-Aware Adaptive NHC
                                      ├── Phase 13: Magnetic Reliability & Anomaly Rejection
                                      ├── Phase 14: Road Map Matching Engine
                                      ├── Phase 15: Multi-Hypothesis & Multi-Level Disambiguation
                                      └── Phase 16: Navigation Integrity & Uncertainty System
                                            └── Phase 17: IO-VNBD Benchmark Suite
                                                  └── Phase 18: Multi-Vehicle Data Pipeline
                                                        └── Phase 19: Automated Ablation Framework
                                                              └── Phase 20: Mobile TFLite Optimization
                                                                    └── Phase 21: High-Rate 200 Hz Edge Daemon
                                                                          └── Phase 22: Live Interactive Demo
```

---

## Detailed Phase Breakdown

### Phase 0: Project Setup & Audit (Current)
- **Deliverables:** `PROJECT_AUDIT.md`, `ARCHITECTURE.md`, `IMPLEMENTATION_ROADMAP.md`, `REQUIREMENTS_TRACEABILITY.md`, `NOVELTY_MATRIX.md`, `FAILURE_ANALYSIS.md`.
- **Exit Criteria:** All architecture and baseline documentation reviewed and validated.

### Phase 1: Project Infrastructure & Build Environment
- **Deliverables:**
  - Python package setup (`pyproject.toml` / `setup.py`) with strict typing (`mypy`), linting (`ruff`), and testing (`pytest`).
  - Native modular directory tree (`core/`, `apps/`, `tools/`, `tests/`).
  - Automated CI configuration and testing harnesses.
- **Exit Criteria:** `pytest` passes with 100% test discovery.

### Phase 2: Sensor Abstraction & Synchronization
- **Deliverables:**
  - `core/sensors/`: `SensorType`, `ImuData`, `GnssData`, `MagData`, `BaroData` immutable data structures.
  - Thread-safe ring buffer and time-sync interpolator (linear/slerp) aligning multi-rate sensor streams (IMU ~10-200 Hz, GNSS ~1-10 Hz, Mag ~50 Hz, Baro ~20 Hz).
  - Deterministic sensor recorder and replay stream reader.
- **Exit Criteria:** Unit tests verifying stream interpolation with sub-millisecond timestamp precision.

### Phase 3: Sensor Calibration Engine
- **Deliverables:**
  - `core/calibration/`: Static Allan variance parameter containers, 6-parameter ellipsoid magnetometer fitting (hard/soft iron), static bias convergence estimator.
  - Temperature compensation hooks.
- **Exit Criteria:** Magnetometer calibration reduces raw field norm distortion by > 80% on test datasets.

### Phase 4: Dynamic Phone-to-Vehicle Alignment
- **Deliverables:**
  - `core/alignment/`: Coarse roll/pitch gravity estimator + dynamic forward acceleration yaw finder.
  - Perturbation detector flagging sudden phone rotation / slippage.
- **Exit Criteria:** Alignment converges to within 3 degrees of true vehicle heading within 5 seconds of straight driving.

### Phase 5: Deterministic Inertial Navigation Baseline
- **Deliverables:**
  - `core/navigation/`: WGS-84 ellipsoid parameters, local NED/ENU tangent plane transforms, quaternion-based attitude propagation, gravity compensation, specific force integration.
- **Exit Criteria:** Pure INS simulation matches analytical kinematic ground truth for ideal trajectories.

### Phase 6: Error-State Kalman Filter (ESKF)
- **Deliverables:**
  - `core/filters/eskf.py`: 15-state nominal & error state propagation, continuous-discrete error transition matrix $F_k$, process noise $Q_k$, Joseph-form covariance update, quaternion error injection and reset.
- **Exit Criteria:** ESKF converges on GNSS updates with covariance bounding true position error.

### Phase 7: GNSS Integrity & Seamless Blackout Transitions
- **Deliverables:**
  - `core/gnss/`: Multi-tier quality estimator (HDOP, satellite count, innovation gating, speed check).
  - Outage entry/exit state machine preventing discontinuous jumps on re-acquisition.
- **Exit Criteria:** Outage injection produces zero-step discontinuities upon GNSS recovery.

### Phase 8: Vibration Analysis & Spectral Decomposition
- **Deliverables:**
  - `core/motion/vibration.py`: Rolling FFT spectrum analyzer, spectral entropy, road roughness estimator, engine frequency isolation.
- **Exit Criteria:** Clear separation of vehicle motion dynamics from 10-30 Hz engine vibrations.

### Phase 9: Intelligent Soft ZUPT (Zero Velocity Update)
- **Deliverables:**
  - `core/constraints/zupt.py`: Stationary probability estimator $P(\text{stat})$, dynamic measurement covariance scaling $R_{\text{zupt}}(P)$.
- **Exit Criteria:** 0% false stationary detection during highway cruise; >99% true stationary detection at traffic stops.

### Phase 10: ML Forward Velocity Estimation
- **Deliverables:**
  - `core/models/`: Temporal Convolutional Network (TCN) / GRU model estimating forward velocity $\hat{v}_{\text{fwd}}$ and uncertainty $\sigma_v^2$ from raw IMU windows.
  - Integration with ESKF measurement update.
- **Exit Criteria:** Velocity RMSE $< 0.8\text{ m/s}$ during simulated GNSS outages.

### Phase 11: Vehicle Classification
- **Deliverables:**
  - `core/models/vehicle_classifier.py`: Tri-class classifier (Car, Motorcycle, Scooter) with confidence scoring based on spectral and dynamic motion profiles.
- **Exit Criteria:** $> 92\%$ classification accuracy across test splits.

### Phase 12: Vehicle-Aware Adaptive NHC
- **Deliverables:**
  - `core/constraints/nhc.py`: Adaptive Non-Holonomic Constraints accounting for car rigidity vs. motorcycle lean/yaw dynamics.
- **Exit Criteria:** Motorcycle cornering does not trigger false lateral velocity corrections.

### Phase 13: Magnetic Reliability & Anomaly Rejection
- **Deliverables:**
  - `core/motion/magnetic.py`: Dynamic field norm anomaly checker, magnetic disturbance score, adaptive compass fusion weighting.
- **Exit Criteria:** Synthetic magnetic pulse ($>20\mu T$) does not deflect navigation heading by $>2^\circ$.

### Phase 14: Road Network Map Matching
- **Deliverables:**
  - `core/map/matcher.py`: OSM graph ingestion, candidate projection, heading alignment, topological connectivity constraint.
- **Exit Criteria:** Trajectory snaps cleanly to road centerline during simulated straight and curved tunnel outages.

### Phase 15: Multi-Hypothesis & Multi-Level Disambiguation
- **Deliverables:**
  - `core/map/multi_hypothesis.py`: Particle/hypothesis manager for stacked flyovers and multi-level parking structures using barometric floor stepping.
- **Exit Criteria:** Correctly identifies floor level in spiral parking garage test profiles.

### Phase 16: Navigation Integrity & Uncertainty System
- **Deliverables:**
  - `core/integrity/`: Full covariance extraction, Horizontal Protection Level (HPL), degradation state machine (`HIGH_CONF`, `MODERATE_CONF`, `DEGRADED`, `UNRELIABLE`).
- **Exit Criteria:** 95% error bounding envelope strictly encapsulates true error without false precision.

### Phase 17: IO-VNBD Benchmark Evaluation
- **Deliverables:**
  - `tools/evaluation/`: Automated pipeline evaluating ATE, RTE, Drift %, Velocity RMSE across the public IO-VNBD dataset.
- **Exit Criteria:** Comprehensive benchmark report generated with reproducible metrics.

### Phase 18: Multi-Vehicle Data Collection Pipeline
- **Deliverables:**
  - `tools/data_pipeline/`: Standardized dataset format, validation schema, multi-vehicle logger protocols.
- **Exit Criteria:** Schema validator accepts car, motorcycle, and scooter sensor recordings.

### Phase 19: Automated Ablation Framework
- **Deliverables:**
  - `tools/ablation/`: Automated matrix execution comparing (Baseline INS, +ESKF, +ZUPT, +ML Vel, +Adaptive NHC, +Map, +Integrity).
- **Exit Criteria:** Complete ablation table and comparative trajectory plots auto-generated.

### Phase 20: Mobile Performance Optimization
- **Deliverables:**
  - `core/models/quantization.py`: INT8 TFLite / ONNX model conversion, latency benchmarks on mobile runtime.
- **Exit Criteria:** Mobile inference $< 5\text{ ms}$, memory $< 50\text{ MB}$.

### Phase 21: High-Rate 200 Hz Edge Engine
- **Deliverables:**
  - `apps/edge_daemon/`: High-performance asynchronous C++/Python engine handling 200 Hz IMU feeds.
- **Exit Criteria:** Zero frame drops at sustained 200 Hz input rate.

### Phase 22: Live Demonstration & Web Dashboard
- **Deliverables:**
  - `apps/web_dashboard/`: FastAPI WebSocket server streaming real-time trajectory, uncertainty ellipses, confidence meters, and outage controls.
- **Exit Criteria:** End-to-end interactive demo with real-time GNSS blackout injection.
