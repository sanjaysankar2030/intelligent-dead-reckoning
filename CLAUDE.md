# CLAUDE.md — Dead Reckoning Project Instructions

## Project Overview
**SIH PS 26168** — AI/ML-augmented Intelligent Dead Reckoning Navigation System.
Physics-informed, machine-learning-augmented inertial navigation system designed for seamless GNSS-denied vehicle navigation on smartphones (~10-200 Hz).

## Core Principles
1. **Strict Sequential Phased Delivery**: Never begin a subsequent phase until the current phase is fully implemented, tested, verified, and approved.
2. **Honesty & No Fabricated Claims**: Never fabricate performance metrics or claim real-world accuracy without experimental evidence from real datasets. Clearly classify evidence (implemented, unit tested, synthetic tested, real-data tested, not validated).
3. **Rigorous Mathematics & Coordinate Frames**: Strictly document and adhere to coordinate frame conventions (Android body frame, phone frame, vehicle frame, local navigation NED/ENU frame, ECEF).
4. **Modularity**: Maintain clean separation:
   `Raw Sensor -> Sensor Abstraction / Sync -> Calibration -> Alignment -> Motion Intelligence + INS Mechanization -> Error-State Kalman Filter (ESKF) -> Adaptive Constraints -> Map Matching -> Navigation Integrity -> Output`

## Development & Test Commands
- Run all tests: `pytest`
- Run specific test file: `pytest tests/path/to/test_file.py -v`
- Python version: Python 3.14 / NumPy 2.x compatible.
- Strict typing with dataclasses and standard numpy arrays. Always explicitly cast numpy booleans when asserting equality in tests (`bool(...)`).

## Architecture & Documentation References
- Architecture: `docs/ARCHITECTURE.md`
- Implementation Roadmap: `docs/IMPLEMENTATION_ROADMAP.md`
- Project State: `PROJECT_STATE.md`
- Engineering Log: `ENGINEERING_LOG.md`
- Task List: `TODO.md`
