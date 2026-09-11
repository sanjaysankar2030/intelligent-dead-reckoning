# Engineering Log

**Project:** SIH PS 26168 — AI/ML based Intelligent Dead Reckoning System

---

## 2026-09-10: Phase 0 Complete
- Delivered project audit, system architecture, implementation roadmap, requirements traceability, novelty matrix, and failure analysis.
- Defined 22-phase sequential delivery plan.

## 2026-09-10: Phase 1 Complete
- Created Python project skeleton with `pyproject.toml`, directory structure, `__init__.py` files for all modules.

## 2026-09-10: Phase 2 Complete
- Implemented `core/sensors/data_types.py`: `ImuSample`, `MagSample`, `GnssFix`, `BaroSample`, `SensorType`, `lin_interp`, `slerp`.
- Implemented `core/sensors/synchronizer.py`: Multi-rate sensor synchronizer with closest-match and linear interpolation.
- Implemented `core/sensors/replay.py`: CSV/binary sensor logger and replay iterator.
- Tests: 14 tests passing (data_types: 5, synchronizer: 5, replay: 4).

## 2026-09-10: Phase 3 Complete
- Implemented `core/calibration/bias_calibration.py`: `StaticImuCalibrator`, arbitrary 3D orientation support, explicit `bool()` casting for Python 3.14 compatibility.
- Implemented `core/calibration/mag_calibration.py`: Centered SVD ellipsoid fitting, definiteness polarity alignment, eigenvalue decomposition sqrt matrix.
- Implemented `core/calibration/persistence.py`: `CalibrationProfile`, JSON versioned save/load with proper dataclass reconstruction.
- Implemented `core/calibration/pipeline.py`: `SensorDataPipeline` enforcing Raw → Calibration → Corrected flow.
- Implemented `core/sensors/health.py`: `ImuHealthMonitor`, `MagHealthMonitor`, `SensorHealthManager` with saturation/jitter/variance checks.
- Fixed: NumPy `longdouble` overflow on Python 3.14 via numpy==2.5.3 wheel.
- Fixed: `assert np.True_ is True` failures via explicit `bool()` wrapping.
- Fixed: Ellipsoid fitting sign ambiguity via eigenvalue polarity check.
- Fixed: JSON deserialization type mismatches in `CalibrationProfile.from_dict`.
- Fixed: Magnetometer replay test generating spatially uniform samples (Fibonacci spiral).
- Tests: 32 calibration/health tests + 5 replay determinism tests, 51 total across all modules. 51/51 passing.
- Phase 3 Engineering Checkpoint: APPROVED.

## 2026-09-11: Phase 4 Starting
- Objective: Phone-to-Vehicle Alignment Engine.
- Design based on `docs/ARCHITECTURE.md` Section 4.

## 2026-09-11: Phase 4 Implementation Checkpoint
- **Objective:** Build robust automatic Phone-to-Vehicle Alignment engine mapping Android Sensor Body frame to Forward-Right-Down (FRD) Vehicle frame.
- **Actions:**
  - Implemented strict Hamilton quaternion math utility in `quaternion_utils.py`, eschewing external non-standard library dependencies for core math.
  - Defined rigid Enum-based schemas in `frames.py` covering definitions for Sensor, Body, Vehicle, Earth, and Navigation coordinate systems as well as Alignment states.
  - Implemented `GravityAligner` in `gravity_alignment.py` estimating pure Pitch/Roll via gravity vector isolation during detected zero velocity periods.
  - Implemented `HeadingEstimator` in `heading_estimator.py` providing heading correction mostly via high-speed (>3m/s) GNSS velocity readings while avoiding magnetic interference pitfalls by strictly bounding single magnetic heading contributions.
  - Created composite `AlignmentEngine` linking gravity and heading subsystems. Integrated a State Machine enforcing progression from `UNINITIALIZED` -> `GRAVITY_ONLY` -> `PARTIALLY_ALIGNED`/`FULLY_ALIGNED`.
  - Added robust dynamic reorientation algorithms that compute quaternion delta angles $\Delta\theta > 15^\circ$ switching constraints explicitly to `LOST` state rather than trusting drifted references.
  - Authored comprehensive strict unit testing suite in `tests/core/alignment/` guaranteeing corner case accuracy, Euler boundary wrapping behaviors, deterministic heading/gravity confidence, and multi-state alignment engine state transitions.
- **Status:** Phase 4 successfully unit-tested (75/75 passing overall tests on Python 3.14 / Numpy 2.5.3). Handing off for checkpoint review.

## 2026-09-11: Phase 5 Implementation Checkpoint
- **Objective:** Deterministic Strapdown Inertial Navigation System (INS) Mechanization baseline establishing raw trajectory dynamics from phase 3-4 calibrated outputs.
- **Actions:**
  - Implemented strictly-typed `NavState` recording discrete states linking timestamps, NED Position, Velocity, Vehicle Attitude Quarternions, and 6-DOF dynamic offsets.
  - Implemented `StrapdownINS` utilizing zeroth-order hold kinematics and standard Local Tangent plane mapping via analytic Specific-Force coordinate rotations.
  - Correctly accommodated +Z downwards Navigation (NED) frame $a_n = [f_n \times q] + g_{ned}$ constraints correctly handling $+9.80665 m/s^2$ zero-offset compensation behavior on arbitrary non-leveled tables.
  - Implemented deterministic discrete mathematical transformations for arbitrary IMU input trajectories including circular tests mapping Centripetal force derivations analytically over standard non-holonomic limits.
  - Inscribed a fully analytic 15-state Continuous-Discrete error-state transition matrix ($\Phi_{15x15}$) expanding spatial variables by standard deviation Process Noise representations inside `_propagate_covariance()`.
  - Linked Phase 3, Phase 4, and Phase 5 directly inside `test_integration.py` driving Synthetic Raw Data natively from zero velocity biases into aligned stationary 0-velocity holds without mathematical drift signatures.
- **Status:** Phase 5 successfully unit-tested (84/84 passing overall tests on Python 3.14 / Numpy 2.5.3). Yielding for review prior to Phase 6 Filter propagation.
