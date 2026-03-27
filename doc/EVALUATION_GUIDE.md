# CHRONOS — Phase 3 Evaluation Guide
## Adaptive vs Static Baseline Comparison

---

## Overview

This document supports the Phase 3 evaluation (Weeks 9–10) of the CHRONOS adaptive display system. It describes how to run the static baseline comparison, collect scenario outcome data, and interpret the exported logs for the final report.

---

## 1. What is the Static Baseline?

The **Static Baseline** is a non-adaptive display mode built into CHRONOS for evaluation purposes. When enabled, it completely disables the AI scoring engine and replaces it with a simple **round-robin algorithm**: images are cycled in order from least-shown to most-shown, with no awareness of time, mood, season, or user preferences.

This mirrors how a conventional digital photo frame or slideshow operates, providing a direct comparison point against the adaptive system.

| | Adaptive (AI) Mode | Static Baseline Mode |
|---|---|---|
| Selection method | Weighted scoring (time + mood + quality + preference) | Round-robin by display count |
| Context awareness | Time of day, season, detected mood | None |
| Personalisation | Like/Skip feedback, mood preference, sensitivity | None |
| Kids safety filter | Active | Active (content still filtered) |
| Logged as | `selection_mode = adaptive` | `selection_mode = baseline` |

---

## 2. Enabling Static Baseline Mode

1. Open the CHRONOS sidebar
2. Scroll to the **⚗ Evaluation Mode** expander (near the bottom, above Recent History)
3. Toggle **"Static Baseline (no AI)"** ON
4. The display will immediately begin cycling images without AI scoring
5. Toggle OFF to restore adaptive behaviour at any time

> The mode is stored per-user in the database — switching accounts does not affect other users' settings.

---

## 3. Running the Comparison Scenarios

Run each scenario for a minimum of **30 minutes** to collect at least 15 display decisions (one per 2-minute refresh cycle). Record your observations using the table in Section 5.

### Scenario A — Morning Context (Adaptive)
- Time: 07:00–09:00
- Baseline mode: OFF
- Mood preference: Auto (system-detected)
- Expected: Energetic/joyful images, warm tones

### Scenario B — Morning Context (Baseline)
- Time: 07:00–09:00
- Baseline mode: ON
- Same image library as Scenario A
- Expected: Images cycle in order regardless of morning context

### Scenario C — Evening Context (Adaptive)
- Time: 19:00–21:00
- Baseline mode: OFF
- Mood preference: Auto
- Expected: Calm/mysterious images, cooler tones

### Scenario D — Evening Context (Baseline)
- Time: 19:00–21:00
- Baseline mode: ON
- Expected: Same round-robin order as Scenario B (no evening adjustment)

### Scenario E — Manual Mood Override (Adaptive)
- Any time
- Set mood to **Energetic** manually
- Baseline mode: OFF
- Expected: High-energy images selected, system responds within one refresh cycle

### Scenario F — Kids Profile (Adaptive vs Baseline)
- Switch to Kids account
- Run 30 min adaptive, then 30 min baseline
- Expected: Both modes show only kids-safe content; adaptive additionally prefers joyful/energetic moods

---

## 4. Exporting Scenario Logs

After each scenario, export the decision log as CSV:

1. Open the sidebar → **☰ Recent History** expander
2. Click **⬇ Export All Logs (CSV)**
3. Save with a descriptive filename, e.g. `scenario_A_morning_adaptive.csv`

### CSV Columns

| Column | Description |
|---|---|
| `timestamp` | Date and time of the display decision |
| `selection_mode` | `adaptive` or `baseline` |
| `image` | Title of the selected image |
| `image_mood` | Primary mood tag assigned by Gemini |
| `time_period` | Time period at decision time (dawn/morning/afternoon/evening/night) |
| `detected_mood` | Mood detected from time/context |
| `score` | Total AI score (0.000–1.000); always 0.000 in baseline mode |
| `t_time` | Time-match sub-score |
| `t_mood` | Mood-match sub-score |
| `t_pref` | User preference sub-score |
| `t_quality` | Aesthetic quality sub-score |
| `t_recency` | Recency penalty applied |
| `t_interaction` | Like/Skip interaction delta |
| `override` | `yes` if manually forced via override toggle |

---

## 5. Observation Recording Template

Use this table to record qualitative observations during each scenario session.

| Scenario | Mode | Duration | Images Shown | Context-Appropriate? | User Perception | Notes |
|---|---|---|---|---|---|---|
| A — Morning | Adaptive | 30 min | | | | |
| B — Morning | Baseline | 30 min | | | | |
| C — Evening | Adaptive | 30 min | | | | |
| D — Evening | Baseline | 30 min | | | | |
| E — Mood Override | Adaptive | 30 min | | | | |
| F — Kids Adaptive | Adaptive | 30 min | | | | |
| F — Kids Baseline | Baseline | 30 min | | | | |

**Context-Appropriate?** — Rate 1–5 (1 = completely mismatched, 5 = perfectly matched to time/mood)
**User Perception** — Was the display experienced as useful (U), neutral (N), or distracting (D)?

---

## 6. Evaluation Criteria

Based on the project objectives, measure each mode against the following:

### 6.1 Consistency and Coherence
- **Adaptive**: Does the AI select images that belong to the same mood family across consecutive refreshes?
- **Baseline**: Does round-robin produce jarring mood transitions (e.g. dark → bright → dark)?
- **Metric**: Count mood changes between consecutive selections per 30-min session

### 6.2 Responsiveness to Contextual Changes
- **Adaptive**: When the time period changes (e.g. afternoon → evening), does the image selection shift accordingly within 1–2 refresh cycles?
- **Baseline**: Does selection change at all in response to context?
- **Metric**: Time lag (in refresh cycles) before mood shift is reflected in selection

### 6.3 Transparency and User Controllability
- **Adaptive**: The reasoning overlay shows confidence score, mood tags, and time period for every decision
- **Baseline**: Score is 0.000; reasoning states "round-robin"
- **Metric**: Qualitative — does the user understand why each image was shown?

### 6.4 Perceived Usefulness and Appropriateness
- **Adaptive**: Does the display feel relevant to the current moment?
- **Baseline**: Does the display feel random or disconnected?
- **Metric**: User rating 1–5 per session (see Section 5 table)

---

## 7. Interpreting the CSV Data

### Detecting Adaptive Responsiveness
Filter `selection_mode = adaptive` and group by `time_period`. Check whether `image_mood` clusters match the expected moods for each period:

| Time Period | Expected Dominant Moods |
|---|---|
| dawn | calm, mysterious |
| morning | energetic, joyful |
| afternoon | joyful, neutral |
| evening | calm, mysterious |
| night | mysterious, melancholic |

### Measuring Baseline Predictability
Filter `selection_mode = baseline`. Verify that `score` is always `0.000` and that images cycle independently of `time_period` or `detected_mood`.

### Comparison Metric
For each matched scenario pair (A vs B, C vs D):
1. Calculate the **mood-match rate**: percentage of decisions where `image_mood` matched `detected_mood`
2. Compare between adaptive and baseline
3. A higher rate in adaptive mode indicates effective contextual adaptation

---

## 8. Expected Findings

Based on the system design, the following outcomes are anticipated:

- **Adaptive mode** will show a statistically higher mood-match rate across all time periods
- **Baseline mode** will show approximately equal distribution across all moods regardless of time
- **User perception** will rate adaptive as more appropriate during strong context periods (early morning, late evening) where mood contrast is highest
- **Kids profile** will show identical safety behaviour between modes (content filter applies to both), with adaptive showing a preference for joyful/energetic moods

---

## 9. File Naming Convention for Collected Data

```
logs/
  scenario_A_morning_adaptive_YYYY-MM-DD.csv
  scenario_B_morning_baseline_YYYY-MM-DD.csv
  scenario_C_evening_adaptive_YYYY-MM-DD.csv
  scenario_D_evening_baseline_YYYY-MM-DD.csv
  scenario_E_mood_override_adaptive_YYYY-MM-DD.csv
  scenario_F_kids_adaptive_YYYY-MM-DD.csv
  scenario_F_kids_baseline_YYYY-MM-DD.csv
```

---

*CHRONOS Evaluation Guide — Phase 3, Week 9–10*
*Generated: March 2026*
