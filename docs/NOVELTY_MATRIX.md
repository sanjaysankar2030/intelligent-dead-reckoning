# Novelty Matrix — Systematic Novelty Assessment

**Project:** SIH PS 26168 — AI/ML based Intelligent Dead Reckoning System  
**Document Version:** 1.0.0  
**Date:** 2026-09-10  
**Status:** Hypothesis — All claims require validation

---

## Novelty Discipline

This document follows a strict policy:
- **No technique is claimed as novel until verified against existing literature.**
- **The integrated adaptive framework is treated as a hypothesis.**
- **Each row must accumulate experimental evidence before any novelty claim is made.**

---

## Novelty Assessment Table

| # | Technique | Existing Research | Existing PS / Competition Approaches | Our Implementation | What Is Different | Evidence Required | Novelty Confidence |
|---|---|---|---|---|---|---|---|
| 1 | **Error-State Kalman Filter** | Well established (Sola 2017, Groves 2013). Standard in professional INS. | Commonly used in professional systems. Some PS entries use simpler complementary filters or basic EKF. | Standard 15-state ESKF with quaternion error injection, Joseph-form covariance. | **Not novel.** Standard technique. Our contribution is correct and complete implementation. | Verify mathematical correctness against reference implementations. | **NONE** — Established technique. |
| 2 | **ML Forward Velocity Estimation** | IONet (Chen 2018), RoNIN (Herath 2020), IDOL (Sun 2021), MotionTransformer (Chen 2022). Deep learning for pedestrian/vehicle velocity from IMU. | Some PS entries use basic LSTM velocity regression. Few integrate uncertainty estimates. | TCN/GRU with multi-task heads outputting velocity + calibrated uncertainty $\sigma_v^2$. | ML velocity with **calibrated uncertainty** integrated as an adaptive measurement, not a replacement for the filter. | Velocity RMSE comparison vs. baselines. Uncertainty calibration plots (predicted vs. empirical). | **LOW** — Technique exists. Calibrated uncertainty integration may be incremental. |
| 3 | **Soft Adaptive ZUPT** | Skog 2010, Wagstaff 2017 — classic threshold ZUPT. Learned ZUPT detectors (Wang 2019). Some adaptive R scaling in PDR. | Most PS approaches use simple threshold-based ZUPT with fixed covariance. | ML stationary probability $P_{\text{stat}}$ driving continuous measurement covariance scaling $R(P)$ with vibration rejection. | Continuous confidence-driven ZUPT rather than binary on/off. Vibration-aware false positive rejection. | False ZUPT rate comparison vs. threshold methods. Performance during vibration. | **LOW-MEDIUM** — Incremental over existing adaptive ZUPT work. |
| 4 | **Vehicle-Aware Adaptive NHC** | NHC well-established for cars (Dissanayake 2001). Motorcycle-specific INS rare (limited research). | Almost all PS entries assume car-like NHC. No known PS entry handles motorcycle lean dynamics. | Lateral constraint covariance scales with lean angle and yaw rate. Vehicle class modulates constraint strength. | **Explicit motorcycle/scooter lean accommodation** in NHC is uncommon in smartphone navigation literature. | Motorcycle cornering trajectory accuracy vs. fixed NHC. Ablation with/without lean adaptation. | **MEDIUM** — Two-wheeler NHC adaptation appears under-explored in smartphone DR. Requires literature confirmation. |
| 5 | **Magnetic Reliability Scoring** | Magnetic disturbance detection well-known (Afzal 2011, Solin 2018). Reliability weighting used in some AHRS. | Most PS entries either always use compass or always ignore it. Few implement dynamic reliability. | Continuous $P(\text{mag\_ok})$ from field norm anomaly, used to weight heading updates in the EKF. | Quantitative reliability score rather than binary accept/reject. | Heading error comparison: always-compass vs. always-ignore vs. adaptive. | **LOW** — Technique exists. Implementation may be cleaner than typical PS entries but not novel. |
| 6 | **Multi-Hypothesis Map Matching** | HMM-based map matching (Newson & Krumm 2009). Particle filter MM (Gustafsson 2002). | PS entries typically use single nearest-road snap. Multi-hypothesis rare in SIH context. | Scored hypothesis set with heading, topology, and barometric vertical constraints. | Multi-level parking floor disambiguation using baro + helical motion pattern. | Multi-level test scenario results. Success rate vs. single-hypothesis. | **MEDIUM** — Multi-level parking disambiguation via baro + motion patterns may be uncommon for smartphone systems. Requires search. |
| 7 | **Integrated Adaptive Framework** | Individual components exist. Full integration with all adaptive elements simultaneously is less common in smartphone-grade systems. | PS entries typically implement 2-3 components. Full integration with vehicle awareness + magnetic reliability + adaptive constraints + map reasoning + uncertainty is rare. | All components co-operating through shared confidence/reliability signals. ML informs constraints; constraints inform filter; filter informs integrity. | **Breadth and integration depth** across vehicle types, sensor reliability, and physical constraints. | Full ablation study proving integrated system outperforms any proper subset. | **MEDIUM** — This is our main novelty hypothesis. Must prove integration > sum of parts. |
| 8 | **NavIC Support** | Hardware-dependent. NavIC constellation is India-specific. | Some PS entries mention NavIC but few implement actual multi-constellation fusion. | GNSS module treats NavIC as one constellation source alongside GPS/GLONASS/Galileo. | Integration of India-specific NavIC constellation for regional accuracy. | NavIC availability impact on accuracy in Indian urban canyons. | **LOW** — NavIC support is a feature, not a research contribution. |

---

## Verified Novelty Claims (Updated as Evidence Accumulates)

| Claim | Status | Evidence |
|---|---|---|
| *None yet* | — | *No experiments completed* |

---

## Anti-Novelty Watchlist

These are things we must **NOT** claim as novel:

1. ❌ "First AI-based dead reckoning system" — Many exist.
2. ❌ "Novel EKF/ESKF" — Standard technique.
3. ❌ "Novel LSTM/TCN for IMU" — Extensively published.
4. ❌ "Novel ZUPT" — Published since 2010.
5. ❌ "Novel map matching" — HMM MM published in 2009.
6. ❌ "Novel sensor fusion" — EKF-based fusion is textbook.

---

## Contribution Framing (Tentative — Subject to Ablation Results)

**Intended Contribution:**

> An integrated, vehicle-aware, uncertainty-quantified dead reckoning framework for smartphones that combines:
> (a) learned motion intelligence providing soft velocity and reliability signals,
> (b) physics-consistent error-state filtering with adaptive constraint confidence driven by ML outputs,
> (c) vehicle-class-specific constraint adaptation including explicit two-wheeler lean handling, and
> (d) multi-hypothesis spatial reasoning with vertical disambiguation —
> achieving measurably lower trajectory drift than ablated subsets across car, motorcycle, and scooter scenarios.

**This is a hypothesis. It becomes a claim only after ablation experiments confirm it.**
