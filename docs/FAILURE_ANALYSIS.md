# Failure Mode Analysis

**Project:** SIH PS 26168 — AI/ML based Intelligent Dead Reckoning System  
**Document Version:** 1.0.0  
**Date:** 2026-09-10  
**Status:** Template — Populated with anticipated failure modes. Will be updated with observed failures.

---

## Overview

This document catalogs known, anticipated, and observed failure modes of the dead reckoning system. For each failure:
- **Symptom:** What the user/evaluator observes.
- **Root Cause:** Physical/algorithmic origin.
- **Detection Method:** How the system identifies the failure is occurring.
- **Mitigation:** What the system does to reduce impact.
- **Remaining Limitation:** What cannot be fully solved.

---

## FM-01: Prolonged Straight Constant-Speed Driving

| Field | Description |
|---|---|
| **Symptom** | Gradual heading drift during long straight sections without turning events. Forward velocity may remain accurate but accumulated heading error causes lateral position drift. |
| **Root Cause** | Gyroscope bias drift is unobservable without heading reference. During straight driving, no dynamic maneuvers provide heading correction. Magnetometer may be unreliable near vehicles/infrastructure. |
| **Detection** | Monitor heading uncertainty growth rate $\dot{\sigma}_\psi$. If $\sigma_\psi > \theta_{\text{warn}}$ and no turns detected for $T > T_{\text{straight}}$, flag degradation. |
| **Mitigation** | (1) Apply cautious magnetic heading updates when $P(\text{mag\_ok}) > 0.8$. (2) Constrain heading rate near zero during straight driving (ZARU — Zero Angular Rate Update). (3) Use road map heading when map-matched with high confidence. |
| **Remaining Limitation** | Without any heading reference (magnetic, map, or dynamic), pure gyroscope heading will drift at $\sim 1{-}5°/\text{min}$ for MEMS sensors. This is a fundamental limitation of strap-down inertial navigation. |

---

## FM-02: Severe Road Vibration

| Field | Description |
|---|---|
| **Symptom** | Position jitter, false motion detection, false velocity estimates during standstill on rough idle or rough road driving. |
| **Root Cause** | Engine vibration and road roughness inject high-frequency energy into accelerometer, masking true vehicle dynamics. |
| **Detection** | Spectral analysis detecting dominant energy in 10-30 Hz band (engine) or broadband roughness signature. Vibration confidence index output from vibration analyzer. |
| **Mitigation** | (1) Vibration-aware ZUPT rejects false stationary triggers during high vibration. (2) Pre-filtering separates motion band (0-5 Hz) from vibration band (>10 Hz) before feature extraction. (3) ML model trained with vibration augmentation. |
| **Remaining Limitation** | Extreme vibration (e.g., severely damaged roads, motorcycle on unpaved terrain) may reduce velocity estimation accuracy by 20-40%. |

---

## FM-03: Motorcycle Lean During Cornering

| Field | Description |
|---|---|
| **Symptom** | NHC falsely constrains lateral velocity during motorcycle turns, causing trajectory undershoot on curves. |
| **Root Cause** | Standard NHC assumes zero lateral velocity. Motorcycles generate significant lateral acceleration during lean cornering. Roll angle couples into the constraint model. |
| **Detection** | Monitor roll rate $\dot{\phi}$ and yaw rate $\dot{\psi}$. If $|\dot{\phi}| > \phi_{\text{lean\_thresh}}$ or $|\dot{\psi}| > \psi_{\text{turn\_thresh}}$, flag turning state. |
| **Mitigation** | (1) Vehicle-aware NHC relaxes lateral constraint proportional to $\sin^2(\phi_{\text{lean}})$. (2) During detected turns, NHC measurement noise $R_{\text{nhc}}$ is increased, weakening the constraint. |
| **Remaining Limitation** | If vehicle is misclassified as car when actually motorcycle, lean compensation is absent. Classification confidence must be monitored. |

---

## FM-04: Magnetic Disturbance (Infrastructure, Vehicles)

| Field | Description |
|---|---|
| **Symptom** | Sudden heading jump when passing under power lines, near metal structures, or beside large vehicles. |
| **Root Cause** | Magnetometer measures total magnetic field including local disturbances. Near ferromagnetic materials, the measured field can deviate $>20\mu T$ from earth's field. |
| **Detection** | Monitor $\|B_{\text{measured}}\| - \|B_{\text{reference}}\|$. Threshold-based anomaly detection with adaptive reference updating during reliable periods. |
| **Mitigation** | (1) Magnetic reliability score $P(\text{mag\_ok})$ gates compass updates. (2) When $P(\text{mag\_ok}) < 0.3$, compass updates are fully rejected. (3) Gradual reference field adaptation to avoid sudden recalibrations. |
| **Remaining Limitation** | Persistent magnetic disturbance (e.g., inside vehicle cabin with strong static distortion) may render magnetometer completely unusable. System must function without compass. |

---

## FM-05: Phone Movement / Reorientation During Transit

| Field | Description |
|---|---|
| **Symptom** | Sudden trajectory deviation after passenger handles phone, moves it to different mount position, or rotates it. |
| **Root Cause** | Phone-to-vehicle alignment $R_p^v$ becomes invalid. Navigation briefly operates with wrong coordinate transformation. |
| **Detection** | High-rate angular velocity anomaly detection: $\|\omega_{\text{measured}}\| \gg \|\omega_{\text{expected\_vehicle}}\|$. Accelerometer spike inconsistent with vehicle dynamics. |
| **Mitigation** | (1) Flag reorientation event. (2) Reset alignment confidence to low. (3) Re-estimate alignment using gravity (immediately) and dynamic forward acceleration (within 2-5 seconds). (4) Inflate position/heading covariance during re-alignment. |
| **Remaining Limitation** | During the 2-5 second re-alignment window, navigation accuracy is degraded. If no dynamic event occurs (e.g., constant velocity on straight road), yaw re-alignment may take longer. |

---

## FM-06: Incorrect Vehicle Classification

| Field | Description |
|---|---|
| **Symptom** | Inappropriate constraint behavior (e.g., rigid car NHC applied to motorcycle, causing curve errors). |
| **Root Cause** | ML classifier outputs incorrect vehicle type due to ambiguous vibration/motion profile or insufficient training data for the scenario. |
| **Detection** | Monitor classification confidence $P(\text{vehicle\_class})$. Low confidence ($<0.7$) triggers conservative mode. |
| **Mitigation** | (1) Use soft confidence-weighted constraints rather than hard vehicle class switching. (2) When confidence is low, use most conservative (loosest) constraint set. (3) Allow manual vehicle class override in app settings. |
| **Remaining Limitation** | With insufficient multi-vehicle training data, classification for scooters (intermediate between car and motorcycle) may be weak initially. |

---

## FM-07: Multi-Level Parking Vertical Ambiguity

| Field | Description |
|---|---|
| **Symptom** | System incorrectly reports floor level (e.g., shows vehicle on level 2 when actually on level 3). |
| **Root Cause** | Barometric pressure drift over time, inter-floor height smaller than pressure resolution, or non-standard floor heights. |
| **Detection** | High vertical position uncertainty $\sigma_z > h_{\text{floor}} / 2$. Multiple hypotheses with similar scores. |
| **Mitigation** | (1) Multi-hypothesis tracking maintains candidates for adjacent floors. (2) Spiral ramp detection (helical yaw pattern) provides transition evidence. (3) Present alternative hypotheses to user rather than forcing single answer. |
| **Remaining Limitation** | Without barometer (some phones lack it) or with strong atmospheric pressure transients, vertical resolution may be insufficient for confident floor identification. |

---

## FM-08: Long GNSS Outage (> 60 seconds)

| Field | Description |
|---|---|
| **Symptom** | Progressive position error growth, expanding uncertainty ellipse, eventual degradation to UNRELIABLE integrity state. |
| **Root Cause** | MEMS IMU bias instability and noise accumulate without external corrections. Position error growth is approximately $\frac{1}{2} b_a t^2$ for uncompensated bias, partially bounded by ML velocity and constraints. |
| **Detection** | Outage timer, covariance magnitude monitoring, drift ratio estimation. |
| **Mitigation** | (1) ML velocity constrains longitudinal drift. (2) ZUPT bounds velocity during stops. (3) NHC constrains lateral drift. (4) Map matching constrains position to road network. (5) Honest uncertainty reporting prevents false user confidence. |
| **Remaining Limitation** | Beyond ~120 seconds without any correction source, drift exceeds 5% trajectory distance for typical MEMS sensors. This is a fundamental sensor limitation. |

---

## FM-09: GNSS Multipath / Urban Canyon

| Field | Description |
|---|---|
| **Symptom** | GNSS position jumps 10-50m, reported accuracy does not reflect true error, innovation gate may not reject. |
| **Root Cause** | GNSS signals reflect off buildings, creating multipath errors. Reported accuracy metrics from GNSS chipset may be optimistic. |
| **Detection** | Innovation test: $y^T S^{-1} y > \gamma_{\text{chi2}}$. Speed consistency check: GNSS velocity vs. IMU-derived velocity. Position jump detection: $\|p_{\text{gnss, new}} - p_{\text{predicted}}\| > \alpha \sigma_p$. |
| **Mitigation** | (1) Strong innovation gating rejects inconsistent GNSS. (2) Gradual re-weighting when GNSS returns rather than immediate full trust. (3) Treat suspected multipath as degraded GNSS rather than complete outage. |
| **Remaining Limitation** | Subtle multipath that passes innovation gates but introduces slow bias is difficult to detect without multi-constellation consistency checks. |

---

## FM-10: Stop-and-Go Traffic

| Field | Description |
|---|---|
| **Symptom** | Accumulated position error from many small motion/stop transitions, each potentially triggering or missing ZUPT. |
| **Root Cause** | Frequent transitions between moving and stationary states stress the ZUPT detector. Each missed ZUPT is a lost correction opportunity; each false ZUPT is an incorrect velocity clamping. |
| **Detection** | High transition frequency detected by ZUPT state machine. Velocity estimate oscillates near zero. |
| **Mitigation** | (1) Soft ZUPT provides partial corrections even when stationary probability is moderate. (2) ML model trained on stop-and-go scenarios. (3) Short-duration stops (<1 second) handled differently from sustained stops. |
| **Remaining Limitation** | Very rapid stop-and-go (< 0.5 second stops) may not provide sufficient stationary evidence for reliable ZUPT. |

---

## Observed Failures (Updated During Development)

| Date | Failure Mode | Dataset/Scenario | Observed Error | Resolution | Status |
|---|---|---|---|---|---|
| *No observations yet* | — | — | — | — | — |
