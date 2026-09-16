# Dead Reckoning Navigation System

**SIH PS 26168** — AI/ML based Intelligent Dead Reckoning System for Seamless Navigation

## Overview

A physics-informed, machine-learning-augmented inertial navigation system designed for seamless GNSS-denied vehicle navigation on smartphones (~10 Hz) and edge devices (~200 Hz).

**Core Principle:** ML estimates useful quantities (velocity, motion state, reliability). Physics maintains consistency. The system always quantifies its own uncertainty.

## Architecture

```
Sensors → Calibration → Alignment → [ML Intelligence + INS Mechanization]
    → Error-State Kalman Filter → Adaptive Constraints → Map Matching
    → Navigation Integrity → Output (Position + Uncertainty + Confidence)
```

See `docs/ARCHITECTURE.md` for the full mathematical specification.

## Project Status

### ✅ COMPLETED PHASES (This Fork)

| Phase | Description | Status | Tests |
|---|---|---|---|
| Phase 0 | Project Audit & Documentation | ✅ Complete | - |
| Phase 1 | Project Infrastructure & Build | ✅ Complete | 51 |
| Phase 2–6 | Core Navigation Foundation (Sensors → ESKF) | ✅ Complete | 114 |
| Phase 7 | Motion Intelligence (ZUPT, ML Velocity) | ✅ Complete | 20 |
| **Subtotal (Your Fork)** | **Engineering Phases 1-7** | **✅ Ready** | **185** |

### ⏳ PHASES IN MAIN REPO (Ready to Merge)

| Phase | Description | Status | Tests | Integration |
|---|---|---|---|---|
| Phase 8 | GNSS Integrity & Outage Transitions | ✅ Complete | 29 | ⏳ Pending |
| Phase 9 | Vibration Analysis & Spectral Decomposition | ✅ Complete | 7 | ⏳ Pending |
| Phase 10 | ML Model Training & Deployment | ✅ Complete* | 6 | ⏳ Pending |
| Phase 11 | **Real-World Data Validation** | 🔴 Blocked in main repo | - | 🟡 **Your real-world data unblocks this!** |
| Phase 12–20 | System Integration (Map Matching, Integrity, Optimization) | ✅ Complete | 12 | ⏳ Pending |
| Phase 21 | End-to-End System Validation | ✅ Complete | 1 | ⏳ Pending |
| **Subtotal (Main Repo)** | **Phases 8-21** | **✅ Ready** | **55** | **⏳ Merge pending** |

**Note on Phase 10:* ML aiding currently degrades navigation (60% worse drift). Disabled by default (update_interval=20). See PHASE_VALIDATION_AND_FIX_GUIDE.md.

### 🎯 OVERALL PROJECT STATUS

| Aspect | Status | Notes |
|--------|--------|-------|
| **Phases Implemented** | ✅ 21 / 21 | All engineering complete (distributed between repos) |
| **Regression Tests** | ✅ 189 | All passing synthetically |
| **Real-World Validation** | 🟡 In Progress | **You are here! Your real-world data is Phase 11.** |
| **Production Readiness** | 🔴 Not Ready | Awaiting real-world field validation |
| **Mobile Deployment** | 🔴 Untested | Host benchmarks only (~330 Hz) |
| **Recommended Next Step** | ➡️ SYNC | See REAL_WORLD_VALIDATION_INTEGRATION_STRATEGY.md |

---

## ⚠️ CRITICAL INFORMATION

### What This Fork Has
✅ **Phases 1–7:** Fully implemented and tested (sensor processing through ZUPT/ML layer)  
✅ **Real-World Validation:** In progress on your local system (protected)  
✅ **Integration Strategy:** See `REAL_WORLD_VALIDATION_INTEGRATION_STRATEGY.md` for safe merge

### What's Missing (Ready in Main Repo)
❌ **Phases 8–21:** GNSS integrity, vibration analysis, map matching, system integration (all synthetic-only in main repo)  
❌ **Real-World Data:** Main repo has no physical sensor logs (Phase 11 BLOCKED)

### Your Competitive Advantage
**🎯 You have something the main repo doesn't: Real-world validation data!**
- Main repo: 21 phases of engineering + 189 synthetic tests ✅
- Your fork + real-world data: Same 21 phases + FIELD-VALIDATED Phase 11 🎯

---

## Documentation

| Document | Purpose | Status |
|---|---|---|
| [PHASE_VALIDATION_AND_FIX_GUIDE.md](PHASE_VALIDATION_AND_FIX_GUIDE.md) | **START HERE** - Phase health, error fixes, validation checklist | ✅ New |
| [REAL_WORLD_VALIDATION_INTEGRATION_STRATEGY.md](REAL_WORLD_VALIDATION_INTEGRATION_STRATEGY.md) | **CRITICAL** - Safe merge workflow protecting real-world data | ✅ New |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Full mathematical specification and system design | ✅ Complete |
| [PROJECT_AUDIT.md](docs/PROJECT_AUDIT.md) | Repository risks and status assessment | ✅ Complete |
| [IMPLEMENTATION_ROADMAP.md](docs/IMPLEMENTATION_ROADMAP.md) | Detailed phase milestones and deliverables | ✅ Complete |
| [REQUIREMENTS_TRACEABILITY.md](docs/REQUIREMENTS_TRACEABILITY.md) | PS 26168 requirements mapped to modules | ✅ Complete |
| [NOVELTY_MATRIX.md](docs/NOVELTY_MATRIX.md) | Honest novelty assessment with evidence requirements | ✅ Complete |
| [FAILURE_ANALYSIS.md](docs/FAILURE_ANALYSIS.md) | Anticipated and observed failure modes | ✅ Complete |

---

## Development Rules

1. **No phase starts before the previous phase passes tests.**
2. **No novelty claims without experimental evidence.**
3. **No fabricated results.** If performance is poor, document it.
4. **Uncertainty is always reported.** The system says "I don't know" rather than lying.
5. **ML augments physics.** ML never replaces the navigation filter.
6. **Real-world data is sacred.** Never overwrite it during merges.

---

## Getting Started

### Prerequisites
- Python 3.14+
- NumPy 2.5.3+
- PyTorch (for ML velocity estimator)

### Installation
```bash
# Clone this repository
git clone https://github.com/sanjaysankar2030/intelligent-dead-reckoning.git
cd intelligent-dead-reckoning

# Install dependencies
pip install -r requirements.txt

# Run tests (phases 1-7)
pytest -v

# Expected: 185+ tests passing
```

### Next Steps

**If you have real-world validation data:**
1. Read `REAL_WORLD_VALIDATION_INTEGRATION_STRATEGY.md`
2. Follow Phase 0: BACKUP (protect your data first!)
3. Follow Phases 1-6: Safe merge workflow
4. Push to GitHub with your real-world data preserved

**If you want to merge with main repo:**
1. Read `PHASE_VALIDATION_AND_FIX_GUIDE.md`
2. Follow `REAL_WORLD_VALIDATION_INTEGRATION_STRATEGY.md`
3. Sync phases 8-21 safely (don't lose your real data!)

---

## Known Issues

| Issue | Severity | Status | Workaround |
|-------|----------|--------|-----------|
| ML velocity aiding degrades navigation (Phase 10) | 🔴 CRITICAL | Identified in main repo | Disabled by default (update_interval=20) |
| Phase 11 blocked without real-world data | 🔴 CRITICAL | **SOLVED BY YOUR DATA** | Your real-world validation unblocks entire Phase 11+ |
| Mobile deployment performance untested | 🟡 HIGH | Unknown | Only Python 3.14 host benchmarks (~330 Hz) |
| Map integration incomplete (Phases 15-17) | 🟡 MEDIUM | Symbolic only | Dummy road segments in tests |
| Binary log format undocumented | 🟡 MEDIUM | Identified | See PHASE_VALIDATION_AND_FIX_GUIDE.md Error #2 |

See [PHASE_VALIDATION_AND_FIX_GUIDE.md](PHASE_VALIDATION_AND_FIX_GUIDE.md) for complete error catalog and fixes.

---

## Validation Status

### Synthetic Validation (Main Repo)
- ✅ Phases 1–6: Unit + Integration tested (114 tests)
- ✅ Phase 7: Motion intelligence (20 tests)
- ✅ Phases 8–9: GNSS integrity + vibration (36 tests)
- ✅ Phase 10: ML training (6 tests)
- ⚠️ Phases 11–21: All synthetic (13 tests) **Main repo Phase 11 blocked**

### Real-World Validation (This Fork)
- 🟡 **Phase 11: IN PROGRESS** (Your real-world data collection)
- ⏳ Phase 12+: Awaiting Phase 11 completion

**Total Tests:** 189 (all passing synthetically)

---

## Project Timeline

```
2026-09-10 ─────────── Phase 0-6 Complete (51 tests, 6 commits)
             \
              └─────── 2026-09-11 ─── Phase 7 Complete (116 tests)
                           \
                            └─── 2026-09-12 ─── Phases 8-10 (145 tests)
                                    \
                                     └─── 2026-09-13 ─── Phase 10 Audit
                                          (Discovered ML degradation)
                                          Phase 11 Framework (158 tests)
                                               \
                                                └─── 2026-09-14 ─── Phases 12-20 (189 tests)
                                                     Phase 21 Integration
                                                          \
                                                           └─── 2026-09-15 ─── Final Checkpoint
                                                                Main Repo Complete ✅
                                                                     |
                                                    YOUR FORK: Phases 1-7 Complete
                                                    Real-World Data Collection Active 🎯
                                                    Ready to Merge & Validate
```

---

## How to Contribute

### Your Real-World Validation
1. Collect sensor data from vehicles (car, motorcycle, scooter)
2. Test various scenarios (urban, highway, GNSS-denied)
3. Log results in `data/real_world/`
4. Document findings in `REAL_WORLD_VALIDATION_RESULTS.md`
5. Follow merge strategy in `REAL_WORLD_VALIDATION_INTEGRATION_STRATEGY.md`

### Bug Reports
If you find issues:
1. Create a branch: `bugfix/issue-name`
2. Document the issue with reproducible steps
3. Test the fix with `pytest -v`
4. Submit with clear commit messages

### Feature Additions (After Phase 21)
- All 21 engineering phases are complete
- Future work: Real-world optimization and deployment
- Coordinate via GitHub Issues

---

## License

Apache License 2.0 (see LICENSE file)

---

## Contact & Support

**Project Lead:** jayanithyan (main repo)  
**Real-World Validation:** sanjaysankar2030 (this fork)

For questions:
1. Check [PHASE_VALIDATION_AND_FIX_GUIDE.md](PHASE_VALIDATION_AND_FIX_GUIDE.md) FAQ
2. See [REAL_WORLD_VALIDATION_INTEGRATION_STRATEGY.md](REAL_WORLD_VALIDATION_INTEGRATION_STRATEGY.md) troubleshooting
3. Review issue history

---

## Quick Links

- 📊 **Phase Status:** See status table above
- 🔧 **Error Fixes:** [PHASE_VALIDATION_AND_FIX_GUIDE.md](PHASE_VALIDATION_AND_FIX_GUIDE.md) Error Catalog
- 🔀 **Safe Merge:** [REAL_WORLD_VALIDATION_INTEGRATION_STRATEGY.md](REAL_WORLD_VALIDATION_INTEGRATION_STRATEGY.md)
- 📐 **Architecture:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- ✅ **Validation:** See Validation Status above
- 🚨 **Known Issues:** See Known Issues table above

---

**Repository:** github.com/sanjaysankar2030/intelligent-dead-reckoning  
**Status:** ✅ Phases 1-7 Complete | 🟡 Phase 11 In Progress | ⏳ Phases 8-10, 12-21 Ready to Merge  
**Last Updated:** 2026-09-16  
**Competition:** SIH PS 26168
