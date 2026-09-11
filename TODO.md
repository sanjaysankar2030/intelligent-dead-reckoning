# SIH PS 26168 Dead Reckoning TODO

## Completed (Phases 1-5)
- [x] Basic Project Skeleton & Environment Setup
- [x] Dependency management (Python 3.14 compatible constraints)
- [x] Immutable Data Types & Replays (`ImuSample`, `GnssFix`, iterators)
- [x] Magnetometer SVD hard/soft iron & basic IMU automated steady-state calibration
- [x] Phone-to-vehicle Alignment Engine (Gravity/GNSS Heading extraction)
- [x] Implement deterministic strapdown inertial navigation integrations.
- [x] Rigorous mechanization propagation loops (Position, Velocity, Attitude).
- [x] Covariance propagation implementation for baseline Error-States. 
- [x] 84/84 regressions validated deterministically.

## Next Up: Phase 6 (Error-State Kalman Filter - ESKF)
- [ ] Connect the 15-state Error-State covariance matrix to genuine periodic measurement updates.
- [ ] Incorporate GNSS velocity & position delayed updates mathematically bridging continuous trajectory bounds.
- [ ] Establish Zero-Velocity Update (ZUPT) trigger architectures feeding observations directly to ESKF filters to correct Random Walk bias limitations.

## Future Phases
- [ ] Non-Holonomic Constraints (NHC) integration.
- [ ] Neural Net map inferences.
- [ ] Output raw trajectories to standardized API targets.
