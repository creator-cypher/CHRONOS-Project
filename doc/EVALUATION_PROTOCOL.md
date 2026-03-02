# Evaluation Protocol: CHRONOS Adaptive Display System

**Purpose:** Establish rigorous scenario-based testing methodology to compare adaptive selection (CHRONOS) vs. static baseline.

**Student:** Kelvin Oteri | **Module:** CIS4517 R&D | **Date:** February 2026

---

## 1. Evaluation Framework

### 1.1 Research Question

> **How effectively can an AI-assisted adaptive system select visual content for domestic displays compared to a static slideshow, measured by consistency, contextual relevance, and user perceived usefulness?**

### 1.2 Success Criteria

| Dimension | Baseline Expectation | Success Threshold | Measurement |
|-----------|-------------------|------------------|-------------|
| **Consistency** | Random selection; highly variable | Same image shouldn't repeat within 60min on 95% of runs | Recency log analysis |
| **Contextual Responsiveness** | No time/mood awareness | Mood scores increase 20%+ when context matches image tags | A/B score comparison |
| **Transparency** | No explanation for choice | User can read reasoning + confidence % for 100% of selections | UI inspection |
| **Confidence Correlation** | N/A | High-confidence selections (80%+) preferred by users 70%+ of time | User feedback survey |
| **Reliability** | No crashes expected | Zero crashes on edge cases (midnight, invalid data, API timeout) | Stress testing |

---

## 2. Scenario-Based Testing Framework

### 2.1 Test Categories

#### Category A: Time Period Coverage (5 scenarios)

**Objective:** Verify system correctly interprets time-of-day and adjusts image selection accordingly.

**Scenario A1: Dawn (5:00-8:00)**
- Context: Early morning, calm mood expected
- Test Input: Load system at 6:30 AM
- Expected Output:
  - Detected mood: "calm"
  - Candidate pool filtered to images tagged "dawn" or with optimal_time="dawn"/"morning"
  - Preference score multiplier includes calm mood boost
- Success Criteria: Image is tagged "calm" OR optimal_time="dawn/morning" (confidence ≥70%)

**Scenario A2: Morning (8:00-12:00)**
- Context: Workday start, energetic mood expected
- Test Input: Load system at 9:00 AM
- Expected Output:
  - Detected mood: "energetic"
  - Images with energetic/joyful tags prioritized
  - Mood compatibility: pref_map["energetic"] weights toward energetic images
- Success Criteria: Image mood ≠ "mysterious" AND has energetic-aligned tags

**Scenario A3: Afternoon (12:00-17:00)**
- Context: Midday, joyful/neutral mood
- Test Input: Load system at 14:30 (2:30 PM)
- Expected Output:
  - Time score boost for afternoon-optimal images
  - Warm colour palettes prioritized
- Success Criteria: Image has warm tones OR joyful tags (confidence ≥70%)

**Scenario A4: Evening (17:00-21:00)**
- Context: Winding down, calm mood
- Test Input: Load system at 19:00 (7:00 PM)
- Expected Output:
  - Shift back toward calm mood
  - Images with sunset/twilight tags weighted high
  - Brightness filter slightly reduced (0.85)
- Success Criteria: Image optimal_time="evening" OR calm tags present

**Scenario A5: Night (21:00-5:00)**
- Context: Late/early, mysterious mood
- Test Input: Load system at 23:30 (11:30 PM)
- Expected Output:
  - Detected mood: "mysterious"
  - Night-optimal images prioritized
  - Brightness filter reduced to 0.65
  - Cooler colour tones preferred
- Success Criteria: Image optimal_time="night" AND mysterious-compatible mood

**Test Execution:**
```python
# Pseudocode for automated test
for hour in [6, 10, 14, 19, 23]:
    result = select_best_image(get_current_context(overrides={"hour": hour}))
    assert result.image["optimal_time"] in ["any", TIME_PERIODS[hour]]
    assert result.total_score >= 0.65  # Minimum threshold
```

---

#### Category B: Sensitivity Profile Testing (3 scenarios)

**Objective:** Confirm that user "sensitivity" preference correctly adjusts weight distribution.

**Scenario B1: Low Sensitivity (User Control Dominant)**
- User Preference: "I always want calm images" (preferred_mood="calm")
- Weight Profile: time=0.20, preference=0.40 (highest)
- Test: Set mood="calm", run at 9:00 AM (context mood="energetic")
- Expected: Selected image mood="calm" despite time recommending energetic (preference wins)
- Success Criteria: Selected image mood="calm"; confidence ≥75%

**Scenario B2: Medium Sensitivity (Balanced)**
- Weight Profile: time=0.35, mood=0.25, preference=0.20 (balanced)
- Test: At 14:00 (joyful context), user prefers "calm"
- Expected: Some influence from both user and time (compromise selection)
- Success Criteria: Score breakdown shows mood & time comparable: ~0.3-0.4 each

**Scenario B3: High Sensitivity (Time/Circadian Dominant)**
- Weight Profile: time=0.40, preference=0.10 (time wins)
- Test: At 9:00 AM (energetic), user prefers "mysterious"
- Expected: System selects energetic image despite user preference (time wins)
- Success Criteria: Selected image energetic; time_score = 1.0; preference_score heavily discounted

**Test Execution:**
```python
for sensitivity, expected_weight_time in [("low", 0.20), ("medium", 0.35), ("high", 0.40)]:
    update_preferences(sensitivity=sensitivity)
    result = select_best_image(morning_context)
    # Verify weights applied in breakdown
    assert result.breakdown["time"] * weights[sensitivity]["time"] == expected_contribution
```

---

#### Category C: Mood Override & Customization (6 scenarios)

**Objective:** Validate that all 6 mood archetypes are correctly processed and influence selection.

**Scenario C1-C6: Each Mood (calm, energetic, melancholic, joyful, mysterious, neutral)**

For each mood:
1. Set `preferred_mood` to target mood
2. Set context to neutral time (e.g., afternoon, no conflicting time mood)
3. Run selection 5 times (verify consistency)
4. Measure:
   - Does selected image primary_mood match preference?
   - Is confidence score stable across runs?
   - Do matched_tags include the target mood?

**Success Criteria (per mood):**
- Primary mood match: 100% (all 5 runs select images of same mood)
- Confidence consistency: Std Dev < 10% across 5 runs
- Matched tags: ≥2 tags related to target mood in reasoning

---

#### Category D: Seasonality Factor Testing (4 scenarios)

**Objective:** Verify that seasonal context correctly boosts appropriate mood tones.

**Test Setup:** Create test image set with diverse moods:
- 5 "calm" images (blue/cool tones)
- 5 "energetic" images (warm/vibrant tones)
- 5 "mysterious" images (dark/moody tones)

**Scenario D1: Winter (Jan/Dec/Feb)**
- Context: Time=evening, detected_mood=calm, season=winter
- Expected: Images with "calm" + "mysterious" moods get +10-15% boost
- Success Criteria: Selected image mood ∈ {calm, mysterious}; confidence ≥75%

**Scenario D2: Spring (Mar/Apr/May)**
- Expected: "Joyful" + "energetic" images get +10-15% boost
- Success Criteria: Selected image mood ∈ {joyful, energetic}

**Scenario D3: Summer (Jun/Jul/Aug)**
- Expected: "Energetic" mood gets +20% boost (highest seasonal boost)
- Success Criteria: Selected image energetic; confidence ≥80%

**Scenario D4: Autumn (Sep/Oct/Nov)**
- Expected: "Mysterious" + "melancholic" get +10-15% boost
- Success Criteria: Selected image mood ∈ {mysterious, melancholic}

**Test Execution:**
```python
for season in ["winter", "spring", "summer", "autumn"]:
    context = get_current_context(overrides={"season": season})
    for _ in range(5):  # 5 runs per season
        result = select_best_image(context)
        assert result.image["primary_mood"] == expected_mood_for_season[season]
```

---

#### Category E: Interaction Signal Processing (4 scenarios)

**Objective:** Demonstrate that user feedback (likes/skips) correctly shapes future selections.

**Setup:** Pre-populate database with:
- Image A: mood=calm, tags=["sunset", "peaceful"]
- Image B: mood=energetic, tags=["sunrise", "vibrant"]

**Scenario E1: User Likes Image A Repeatedly**
- Action: Call `save_interaction(image_a_id, "like")` × 5
- Expected: Next selection has 25% higher affinity for Image A (interaction_delta = +0.25 capped to +0.15)
- Success Criteria: Image A score increases by 0.15; Image B relatively decreases

**Scenario E2: User Skips Image B Repeatedly**
- Action: Call `save_interaction(image_b_id, "skip")` × 5
- Expected: Image B score decreases by 0.15
- Success Criteria: Image B not selected in next 3 runs

**Scenario E3: Mixed Feedback (Likes + Skips)**
- Action: 3 likes on Image A, 2 skips on Image A
- Net: (3-2) × 0.05 = +0.05
- Expected: Modest positive signal (not enough to reverse decision alone)
- Success Criteria: Score boost of ~0.05

**Scenario E4: Reset Feedback**
- Action: Delete all interactions from database
- Expected: Scores return to baseline (no residual memory)
- Success Criteria: Image scores identical to cold start

---

#### Category F: Robustness & Edge Cases (6 scenarios)

**Objective:** Ensure system gracefully handles edge cases without crashes.

**Scenario F1: Midnight Boundary (hour=0)**
- Test: Call with hour=0, expect "night" period
- Success Criteria: No crash; detected_mood="mysterious"

**Scenario F2: Invalid Mood in Override**
- Test: `get_current_context(overrides={"detected_mood": "invalid_mood"})`
- Expected: Sanitized to "neutral"
- Success Criteria: No crash; mood="neutral"; score calculation works

**Scenario F3: No Images in Database**
- Test: Delete all images; call select_best_image()
- Expected: Return None gracefully; log warning
- Success Criteria: No crash; proper None handling in UI

**Scenario F4: All Images Inactive (is_active=0)**
- Test: Mark all images as inactive; run selection
- Expected: Return None; don't display anything
- Success Criteria: No crash; graceful fallback

**Scenario F5: Missing Gemini API Key**
- Test: GEMINI_API_KEY=None; try to analyze image
- Expected: AnalysisResult(success=False, error_message="...")
- Success Criteria: No crash; proper error propagation to UI

**Scenario F6: Duplicate Tag Names**
- Test: Insert same tag twice for same image (violates UNIQUE constraint)
- Expected: INSERT OR IGNORE prevents error
- Success Criteria: No crash; only one instance retained

---

### 2.2 Automated Test Suite Execution

**File:** `tests/scenario_runner.py`

```bash
# Run all scenarios with detailed output
python tests/scenario_runner.py

# Run only scoring tests (no interaction summary)
python tests/scenario_runner.py --quiet

# Run specific category
python tests/scenario_runner.py --category B  # Sensitivity only
```

**Output Format:**
```
═══════════════════════════════════════════════════════════════
                    SCENARIO TEST RESULTS
═══════════════════════════════════════════════════════════════
Test 1: Time Period Coverage
  ✅ A1 (Dawn):      PASS | confidence: 82% | mood: calm
  ✅ A2 (Morning):   PASS | confidence: 76% | mood: energetic
  ✅ A3 (Afternoon): PASS | confidence: 79% | mood: joyful
  ✅ A4 (Evening):   PASS | confidence: 75% | mood: calm
  ✅ A5 (Night):     PASS | confidence: 81% | mood: mysterious

Test 2: Sensitivity Profiles
  ✅ B1 (Low):       PASS | weight_time: 0.20 | score: 0.78
  ✅ B2 (Medium):    PASS | weight_time: 0.35 | score: 0.72
  ✅ B3 (High):      PASS | weight_time: 0.40 | score: 0.85

Test 3: Mood Archetypes
  ✅ C1 (Calm):      PASS | matches: 5/5 | consistency: 98%
  ✅ C2 (Energetic): PASS | matches: 5/5 | consistency: 96%
  ... (6 total)

Test 4: Interaction Signals
  ✅ D1 (Likes):     PASS | delta: +0.15 | score_delta: +0.15
  ✅ D2 (Skips):     PASS | delta: -0.15 | score_delta: -0.15
  ✅ D3 (Mixed):     PASS | delta: +0.05 | score_delta: +0.05
  ✅ D4 (Reset):     PASS | interactions: 0

Results:
  Total Tests: 32
  Passed: 32 ✅
  Failed: 0 ❌
  Pass Rate: 100%

All scenario tests passed! ✓
═══════════════════════════════════════════════════════════════
```

---

## 3. Baseline Comparison Methodology

### 3.1 Control Condition Setup

**Baseline System:** `app_baseline.py`
- Random image rotation (no AI analysis)
- Manual navigation (Prev / Next / Shuffle)
- Identical UI layout to CHRONOS for visual consistency
- No mood/time context awareness

### 3.2 Comparative Metrics

| Metric | CHRONOS | Baseline | Expected Advantage |
|--------|---------|----------|-------------------|
| **Selection Consistency** | Recency penalty (same image not shown 60min) | Fully random; repeats likely | CHRONOS +40-50% |
| **Time-Mood Alignment** | Scores boost by 30%+ when tags match context | No context processing | CHRONOS +30%+ |
| **User Perceived Relevance** | Visible confidence % + reasoning | No explanation | CHRONOS +25-35% |
| **Interaction Learning** | Feedback shapes future selections (±0.15) | No learning | CHRONOS +50%+ |
| **Visual Coherence** | Avoids jarring mood swaps (smooth transitions) | Jarring random jumps | CHRONOS +20%+ |

### 3.3 User Evaluation Design

**If conducting formal user study:**

**Sample:** 8-10 participants, 14 days each
- **Group A (n=4-5):** CHRONOS → Baseline (crossover after 7 days)
- **Group B (n=4-5):** Baseline → CHRONOS (crossover after 7 days)

**Daily Metrics Collected:**
- User engagement (time viewing frame per day)
- Feedback frequency (likes/skips per day)
- Subjective survey (5-point Likert):
  - "Images felt relevant to the time of day"
  - "The system understood my mood preferences"
  - "I enjoyed watching the display"
  - "I would recommend this to others"

**Analysis:**
- Paired t-test (pre/post crossover)
- Qualitative feedback (thematic analysis)
- Interaction pattern comparison (engagement curves)

---

## 4. Success Criteria & Pass/Fail Thresholds

### 4.1 Automated Tests (Scenario Suite)

**PASS Condition:** ≥30/32 tests pass (93.75%)
- Isolated failures (e.g., 1 mood type) do not block prototype
- Critical failures (time classification, scoring crashes) must all pass

**FAIL Condition:** <30 tests pass
- Indicates fundamental logic bug
- Trigger: Debug logs, review Decision Engine algorithm

### 4.2 Confidence Score Validation

**PASS Condition:**
- Confidence scores range 45-100% across diverse contexts
- Mean confidence: 70-80%
- Std deviation: <15%
- High-confidence selections (80%+) occur 30-40% of time

**FAIL Condition:**
- Mean confidence <60% (indicates weak signal)
- All selections >95% (indicates overconfident/inflated scoring)

### 4.3 Consistency Metrics

**PASS Condition:**
- Same context (time+mood) produces same image selection 95%+ of time
- Recency penalty prevents image repetition within 60min (≥99%)
- Score variance <0.05 across repeated runs with identical context

### 4.4 Baseline Comparison (if user study conducted)

**PASS Condition:**
- CHRONOS mean relevance score >4.0/5.0 (80%)
- Baseline mean relevance score <3.5/5.0 (70%)
- Difference significant (paired t-test, p<0.05)
- User engagement (feedback frequency) increases 20%+ with CHRONOS

---

## 5. Documentation & Reporting

### 5.1 Test Results Log

All results automatically logged to `context_logs` table:

```sql
SELECT timestamp, time_period, detected_mood, selection_score,
       matched_tags, reasoning_text, score_breakdown
FROM context_logs
ORDER BY timestamp DESC
LIMIT 100;
```

### 5.2 Deliverable Artifacts

**1. Scenario Test Report**
- Pass/fail status for each test
- Confidence scores per scenario
- Edge case handling notes
- Recommendations for refinement

**2. Comparative Analysis (if user study)**
- Summary statistics (mean, SD, range)
- Statistical significance tests
- Qualitative feedback themes
- Engagement curves (time-series)

**3. Confidence Score Analysis**
- Distribution histogram
- Correlation with user feedback (if available)
- Identification of low-confidence edge cases

**4. Audit Trail Report**
- Selection decision log (all 100+ decisions)
- Tag matching accuracy
- Recency penalty effectiveness
- Interaction signal impact

---

## 6. Troubleshooting & Debug Protocol

### 6.1 If Time Classification Fails

**Symptom:** Wrong mood detected at specific hour
**Debug:**
1. Check `_classify_time(hour)` return value
2. Verify TIME_PERIODS ranges don't have gaps
3. Review context override in test

### 6.2 If Confidence Scores Seem Wrong

**Symptom:** All scores 50% or all 95%
**Debug:**
1. Check matched_tags count (should vary)
2. Verify total_score calculated correctly
3. Inspect score_breakdown for zero components

### 6.3 If Interaction Signals Don't Apply

**Symptom:** Like feedback doesn't boost image score
**Debug:**
1. Verify `save_interaction()` called successfully
2. Check `get_interaction_counts()` returns correct values
3. Ensure interaction_delta calculated and added to total_score

---

## 7. Timeline & Next Steps

**Phase 3 (Weeks 9-10):**
- ✅ Run scenario suite (automated)
- ✅ Document test results
- ✅ Identify edge cases
- ✅ Refine Decision Engine parameters

**Phase 4 (Weeks 11-12):**
- [ ] Conduct user evaluation (if time permits)
- [ ] Analyze qualitative feedback
- [ ] Write evaluation chapter for thesis
- [ ] Prepare final presentation

---

## 8. References & Standards

- **Human-Centred AI:** Schmager et al., 2025
- **Proactive AI Evaluation:** Kraus et al., 2025
- **Context-Aware Systems:** Casillo et al., 2021
- **Research Methodology:** Cohen et al., 2007 (Quantitative Research Methods)

---

**Evaluation Protocol Approved**
*Methodology reviewed against CIS4517 requirements*
*Ready for Phase 3 execution*
