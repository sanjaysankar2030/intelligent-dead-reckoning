# Project Audit Report
**Date:** 2026-09-10  
**Project:** SIH PS 26168 — AI/ML based Intelligent Dead Reckoning System  
**Status:** GREEN FIELD PROJECT

## Executive Summary

This is a **completely new project** with no existing implementation. The repository is empty except for the base directory structure.

This changes the development approach from "audit and refactor" to "ground-up implementation following the specified architecture."

---

## A. What Already Works

**NOTHING** — The repository is empty.

---

## B. What Is Incomplete

**EVERYTHING** — No code exists yet.

---

## C. What Should Be Preserved

**N/A** — No existing code to preserve.

---

## D. What Should Be Refactored

**N/A** — No existing code to refactor.

---

## E. What Is Technically Incorrect

**N/A** — No existing code to evaluate.

---

## F. PS 26168 Requirements Already Satisfied

**NONE** — Implementation has not begun.

---

## G. PS 26168 Requirements Remaining

**ALL REQUIREMENTS** must be implemented from scratch:

### Core Functional Requirements

1. **GNSS-Denied Navigation**
   - Dead reckoning when GNSS unavailable
   - Seamless transitions between GNSS and DR modes
   - ~1% trajectory error target during outages

2. **Multi-Platform Support**
   - Smartphone operation (~10 Hz)
   - Edge deployment capability (~200 Hz)

3. **Vehicle Awareness**
   - Support for cars, motorcycles, scooters
   - Vehicle-specific constraint adaptation

4. **Sensor Fusion**
   - Accelerometer, gyroscope, magnetometer
   - GNSS/NavIC integration
   - Optional barometer

5. **Intelligence Layer**
   - ML-based motion state classification
   - Forward velocity estimation
   - Stationary detection
   - Vibration analysis
   - Magnetic reliability assessment

6. **Navigation Integrity**
   - Uncertainty quantification
   - Confidence estimation
   - Degradation state awareness

7. **Map Integration**
   - Road matching
   - Multi-hypothesis location reasoning
   - Multi-level parking disambiguation

8. **Real-time Performance**
   - Low latency operation
   - Mobile-optimized inference
   - Battery efficiency

---

## H. Recommended Implementation Order

Given the green field status, follow the phased approach exactly as specified in the master instructions:

### PHASE 0: Foundation ✓ (Current Phase)
- [x] Repository audit (COMPLETE — determined empty state)
- [ ] Create documentation structure
- [ ] Define architecture
- [ ] Create implementation roadmap
- [ ] Establish requirements traceability
- [ ] Set up project structure
- [ ] Initialize version control

### PHASE 1: Project Infrastructure
**Priority:** CRITICAL  
**Dependencies:** None  
**Estimated Effort:** 2-3 days

- [ ] Create directory structure
- [ ] Set up Python/Kotlin environments
- [ ] Configure build systems
- [ ] Establish testing framework
- [ ] Create CI/CD pipeline skeleton
- [ ] Set up development tools

### PHASE 2: Sensor Abstraction Layer
**Priority:** CRITICAL  
**Dependencies:** Phase 1  
**Estimated Effort:** 3-4 days

- [ ] Define sensor data structures
- [ ] Implement timestamp synchronization
- [ ] Create sensor abstraction interfaces
- [ ] Build Android sensor acquisition
- [ ] Create sensor logging system
- [ ] Implement replay capability

### PHASE 3: Calibration System
**Priority:** HIGH  
**Dependencies:** Phase 2  
**Estimated Effort:** 4-5 days

- [ ] Accelerometer bias estimation
- [ ] Gyroscope bias estimation
- [ ] Magnetometer calibration
- [ ] Scale factor estimation
- [ ] Online calibration update
- [ ] Calibration persistence

### PHASE 4: Phone-to-Vehicle Alignment
**Priority:** HIGH  
**Dependencies:** Phase 3  
**Estimated Effort:** 5-6 days

- [ ] Gravity-based initial alignment
- [ ] GNSS velocity-based refinement
- [ ] Dynamic alignment estimation
- [ ] Alignment confidence tracking
- [ ] Phone movement detection
- [ ] Re-alignment triggers

### PHASE 5: Inertial Navigation Baseline
**Priority:** CRITICAL  
**Dependencies:** Phase 4  
**Estimated Effort:** 6-8 days

- [ ] Attitude propagation (quaternion-based)
- [ ] Velocity propagation
- [ ] Position propagation
- [ ] Coordinate frame transformations
- [ ] Numerical stability handling
- [ ] Baseline trajectory generation

### PHASE 6: Error-State Kalman Filter
**Priority:** CRITICAL  
**Dependencies:** Phase 5  
**Estimated Effort:** 8-10 days

- [ ] State definition and initialization
- [ ] Process model implementation
- [ ] Jacobian computation
- [ ] Covariance propagation
- [ ] Measurement model framework
- [ ] State update mechanism
- [ ] Quaternion normalization

### PHASE 7: GNSS Integrity Module
**Priority:** HIGH  
**Dependencies:** Phase 6  
**Estimated Effort:** 4-5 days

- [ ] GNSS quality estimation
- [ ] Reliability scoring
- [ ] Jump detection
- [ ] Consistency checking
- [ ] Innovation monitoring
- [ ] Smooth transition logic

### PHASE 8: Vibration Analysis
**Priority:** MEDIUM  
**Dependencies:** Phase 5  
**Estimated Effort:** 5-6 days

- [ ] Time-domain feature extraction
- [ ] Frequency-domain analysis
- [ ] Spectral energy computation
- [ ] Vibration classification
- [ ] Reliability scoring
- [ ] Temporal tracking

### PHASE 9: Adaptive ZUPT
**Priority:** HIGH  
**Dependencies:** Phase 6, 8  
**Estimated Effort:** 5-6 days

- [ ] ML-based stationary detection
- [ ] Vibration-aware confidence
- [ ] Soft ZUPT implementation
- [ ] Adaptive measurement covariance
- [ ] False/missed ZUPT metrics
- [ ] Integration with EKF

### PHASE 10: ML Forward Velocity Estimation
**Priority:** HIGH  
**Dependencies:** Phase 6  
**Estimated Effort:** 8-10 days

- [ ] Dataset preparation pipeline
- [ ] Temporal model architecture selection
- [ ] Multi-task learning framework
- [ ] Training pipeline
- [ ] Uncertainty estimation
- [ ] Real-time inference optimization
- [ ] Integration with navigation filter

### PHASE 11: Vehicle Classification
**Priority:** MEDIUM  
**Dependencies:** Phase 10  
**Estimated Effort:** 6-8 days

- [ ] Vehicle-specific feature engineering
- [ ] Classification model training
- [ ] Confidence estimation
- [ ] Real-time classification
- [ ] Motorcycle lean detection
- [ ] Vehicle-specific constraints

### PHASE 12: Adaptive NHC
**Priority:** MEDIUM  
**Dependencies:** Phase 11  
**Estimated Effort:** 4-5 days

- [ ] Vehicle-aware constraint selection
- [ ] Motion-state-dependent adaptation
- [ ] Constraint confidence calculation
- [ ] Integration with EKF
- [ ] Performance validation

### PHASE 13: Magnetic Reliability
**Priority:** MEDIUM  
**Dependencies:** Phase 6  
**Estimated Effort:** 4-5 days

- [ ] Magnetic field magnitude monitoring
- [ ] Anomaly detection
- [ ] Calibration quality assessment
- [ ] Reliability scoring
- [ ] Adaptive heading updates

### PHASE 14: Map Matching
**Priority:** MEDIUM  
**Dependencies:** Phase 7  
**Estimated Effort:** 8-10 days

- [ ] OSM integration
- [ ] Road network representation
- [ ] Single-hypothesis matching
- [ ] Topology consistency
- [ ] Heading-based filtering
- [ ] Match confidence scoring

### PHASE 15: Multi-Hypothesis Location
**Priority:** LOW  
**Dependencies:** Phase 14  
**Estimated Effort:** 8-10 days

- [ ] Hypothesis generation
- [ ] Vertical disambiguation
- [ ] Multi-level parking support
- [ ] Hypothesis scoring
- [ ] Best hypothesis selection
- [ ] Confidence estimation

### PHASE 16: Navigation Integrity Output
**Priority:** HIGH  
**Dependencies:** Phase 6-13  
**Estimated Effort:** 4-5 days

- [ ] Uncertainty extraction from covariance
- [ ] Overall confidence computation
- [ ] Degradation state machine
- [ ] Integrity API design
- [ ] Output formatting

### PHASE 17: IO-VNBD Benchmark
**Priority:** HIGH  
**Dependencies:** Phase 1-16  
**Estimated Effort:** 5-6 days

- [ ] Dataset acquisition
- [ ] Format conversion
- [ ] Ground truth alignment
- [ ] Benchmark evaluation pipeline
- [ ] Metric computation
- [ ] Result visualization

### PHASE 18: Multi-Vehicle Dataset Pipeline
**Priority:** MEDIUM  
**Dependencies:** Phase 2  
**Estimated Effort:** 6-8 days

- [ ] Android data collection app
- [ ] Metadata schema
- [ ] Automated logging
- [ ] Data validation
- [ ] Storage/organization system
- [ ] Car/motorcycle/scooter collection protocol

### PHASE 19: Ablation Framework
**Priority:** MEDIUM  
**Dependencies:** Phase 17  
**Estimated Effort:** 5-6 days

- [ ] Configuration management
- [ ] Automated variant testing
- [ ] Metric aggregation
- [ ] Report generation
- [ ] Comparison visualization

### PHASE 20: Mobile Optimization
**Priority:** HIGH  
**Dependencies:** Phase 1-16  
**Estimated Effort:** 6-8 days

- [ ] Profiling and bottleneck identification
- [ ] Model quantization
- [ ] Code optimization
- [ ] Memory optimization
- [ ] Battery impact measurement
- [ ] Performance validation

### PHASE 21: Edge Deployment
**Priority:** MEDIUM  
**Dependencies:** Phase 20  
**Estimated Effort:** 6-8 days

- [ ] Platform abstraction layer
- [ ] High-rate IMU adapter
- [ ] Edge deployment packaging
- [ ] 200 Hz performance validation
- [ ] Deployment documentation

### PHASE 22: Final Demonstration
**Priority:** HIGH  
**Dependencies:** All phases  
**Estimated Effort:** 4-5 days

- [ ] Demo mode implementation
- [ ] Real-time visualization dashboard
- [ ] Presentation materials
- [ ] Performance summary reports
- [ ] Video demonstrations
- [ ] Documentation finalization

---

## Development Timeline Estimate

**Total Estimated Duration:** 18-24 weeks (4.5-6 months)

**Critical Path:**
1. Infrastructure (Phase 1)
2. Sensors (Phase 2)
3. Calibration (Phase 3)
4. Alignment (Phase 4)
5. INS Baseline (Phase 5)
6. EKF (Phase 6)
7. GNSS Integration (Phase 7)
8. ML Velocity (Phase 10)
9. ZUPT (Phase 9)
10. Integrity (Phase 16)
11. Benchmark (Phase 17)
12. Optimization (Phase 20)
13. Demo (Phase 22)

**Parallelizable Work:**
- Vibration analysis (Phase 8) can proceed alongside Phases 7-9
- Vehicle classification (Phase 11) can proceed alongside other ML work
- Map matching (Phase 14-15) can be developed independently
- Dataset collection (Phase 18) should start early

---

## Technical Risks

### HIGH RISK

1. **ML Model Performance**
   - **Risk:** Velocity/state estimation insufficient for <1% drift
   - **Mitigation:** Early prototyping, multiple architecture trials, extensive validation

2. **Real-time Performance on Mobile**
   - **Risk:** Cannot achieve 10 Hz with acceptable battery drain
   - **Mitigation:** Early profiling, quantization, model compression research

3. **Phone-to-Vehicle Alignment**
   - **Risk:** Unstable or inaccurate alignment degrades entire system
   - **Mitigation:** Multiple alignment algorithms, extensive testing, fallback mechanisms

4. **Dataset Availability**
   - **Risk:** Insufficient labeled data for training, especially motorcycles
   - **Mitigation:** Early data collection, semi-supervised techniques, transfer learning

### MEDIUM RISK

5. **GNSS Transition Smoothness**
   - **Risk:** Discontinuities when switching modes
   - **Mitigation:** Careful state management, gradual weighting transitions

6. **Magnetic Disturbance Handling**
   - **Risk:** False heading corrections from bad magnetometer data
   - **Mitigation:** Conservative reliability thresholds, extensive testing

7. **Vehicle Classification Errors**
   - **Risk:** Misclassification leads to inappropriate constraints
   - **Mitigation:** Soft confidence-based constraints rather than hard switching

### LOW RISK

8. **Map Matching Complexity**
   - **Risk:** Multi-hypothesis tracking too complex for real-time
   - **Mitigation:** Start with single hypothesis, add complexity if needed

9. **Edge Deployment Portability**
   - **Risk:** Platform-specific issues at 200 Hz
   - **Mitigation:** Clean abstraction layers, early testing on target hardware

---

## Data Requirements

### Training Data Needed

1. **Car Data:** 50-100 hours diverse scenarios
2. **Motorcycle Data:** 30-50 hours diverse scenarios
3. **Scooter Data:** 20-30 hours diverse scenarios

### Must Include
- Urban, suburban, highway
- Smooth and rough roads
- GNSS outages (tunnels, urban canyons)
- Magnetic disturbances
- Various phone mounting positions
- Stop-and-go traffic
- Turning, braking, acceleration
- Multi-level parking

### Ground Truth Strategy
- High-quality GNSS during clear sky
- Post-processed RTK where possible
- Manual annotation for complex scenarios
- Consistent coordinate reference frames

---

## Resource Requirements

### Development Team Roles
- Navigation algorithm engineer (INS/EKF)
- ML engineer (temporal models, training)
- Mobile developer (Android)
- Data collection/annotation
- Testing/validation engineer

### Hardware Needed
- Multiple Android smartphones (various models)
- Car, motorcycle, scooter access
- High-quality reference GNSS (optional)
- Edge computing hardware for Phase 21
- Development workstations with GPU

### Software/Services
- Python/PyTorch environment
- Android Studio
- TensorFlow Lite for mobile
- OpenStreetMap data
- IO-VNBD dataset
- Cloud compute for training (optional)

---

## Novelty Assessment

The system's potential novelty lies in the **integrated adaptive framework**, not individual components.

### NOT Novel (Use Existing Techniques)
- Error-State Kalman Filter
- IMU mechanization
- ZUPT
- NHC constraints
- Map matching algorithms
- ML temporal models

### POTENTIALLY Novel (Hypothesis to Validate)
- Integrated adaptive constraint framework driven by learned reliability
- Vehicle-aware dead reckoning with explicit two-wheeler support
- Unified uncertainty-aware navigation integrity across all modes
- ML-informed constraint confidence rather than ML-replacement of physics

### Evidence Required
- Comprehensive literature review
- Comparison with state-of-the-art systems
- Ablation studies proving integrated approach outperforms components
- Real-world validation across vehicle types

---

## Compliance with PS 26168

### Requirements Analysis

**Requirement:** GNSS-denied navigation  
**Status:** Not started  
**Implementation:** Phases 5-16

**Requirement:** AI/ML integration  
**Status:** Not started  
**Implementation:** Phases 8-11

**Requirement:** Smartphone deployment  
**Status:** Not started  
**Implementation:** Phases 2, 20

**Requirement:** Real-time operation  
**Status:** Not started  
**Implementation:** Phase 20

**Requirement:** Seamless transitions  
**Status:** Not started  
**Implementation:** Phase 7

**Requirement:** Accuracy target (~1%)  
**Status:** Not started  
**Implementation:** All phases, validated in Phase 17

---

## Next Steps

1. **Complete Phase 0 Documentation:**
   - [x] PROJECT_AUDIT.md (this document)
   - [ ] ARCHITECTURE.md
   - [ ] IMPLEMENTATION_ROADMAP.md
   - [ ] REQUIREMENTS_TRACEABILITY.md
   - [ ] NOVELTY_MATRIX.md
   - [ ] FAILURE_ANALYSIS.md (template)

2. **Set Up Development Environment:**
   - [ ] Initialize git repository
   - [ ] Create directory structure
   - [ ] Set up Python environment
   - [ ] Set up Android project structure
   - [ ] Configure build tools
   - [ ] Create initial README

3. **Begin Phase 1:**
   - [ ] Implement project infrastructure
   - [ ] Set up testing framework
   - [ ] Create basic CI/CD pipeline

---

## Recommendations

### Start Small, Validate Early
- Build simplest possible baseline first
- Validate each component independently before integration
- Measure everything, claim nothing unproven

### Prioritize Critical Path
- Focus on Phases 1-7, 10, 16, 17, 20 first
- These form the minimum viable system
- Other phases add sophistication but aren't core functionality

### Data Collection Starts Now
- Even without full app, start collecting sensor logs
- Build simple Android logger as first deliverable
- Collect diverse scenarios continuously

### Avoid Over-Engineering
- Resist adding features not required by PS 26168
- Simple solutions that work > complex solutions that might work
- Every abstraction layer must justify its existence

### Document Failures
- Track what doesn't work as carefully as what does
- Failed approaches inform the final report
- Negative results are valuable results

---

## Conclusion

This is a **ground-up implementation** of a complex, research-grade navigation system.

**Key Success Factors:**
1. Disciplined phased implementation
2. Continuous validation and measurement
3. Early data collection
4. Conservative claims backed by evidence
5. Clear separation of physics and ML
6. Explicit uncertainty quantification

**Critical Risks:**
1. ML model performance
2. Real-time mobile performance
3. Dataset availability
4. Timeline (18-24 weeks is aggressive)

**Next Immediate Action:**
Complete remaining Phase 0 documentation before writing any code.
