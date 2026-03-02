# CHRONOS/AURA System Audit Report
**Date:** February 28, 2026
**Status:** Critical Issues Identified & Resolved
**Project Level:** Master's R&D Prototype (CIS4517)

---

## EXECUTIVE SUMMARY

The CHRONOS Adaptive Ambient Display System demonstrates a mature modular architecture with three well-separated layers (Metadata, Context, Decision Engine). However, **three critical logic and UI discrepancies** were identified that undermine the thesis claims about "adaptive decision-making" and "system reliability."

### Top 3 Critical Issues Found & Fixed:

| # | Issue | Location | Severity | Impact |
|---|-------|----------|----------|--------|
| **1** | Time Period Classification produces "dead end" moods when detected_mood is None or corrupted | `logic/context.py:37-56`, `logic/engine.py:169` | HIGH | Reasoning overlay displays incorrect mood explanation |
| **2** | Sidebar Toggle FAB (Floating Action Button) has insufficient z-index layering due to stacking context conflict | `app.py:509-610`, CSS line 413-421 | HIGH | Toggle button may become invisible when sidebar is open (viewport z-index inversion) |
| **3** | Image selection algorithm does not validate context data before scoring, allowing invalid moods to crash preference scoring | `logic/engine.py:210-220` | MEDIUM | Non-standard mood values break mood_score calculation |

---

## DETAILED FINDINGS

### Issue #1: Context Layer Dead End (Logic Validation Gap)

**File:** `logic/context.py:37-56` and `logic/engine.py:169-170`

**Problem:**
```python
def get_current_context(overrides: Optional[dict] = None) -> dict:
    now = datetime.now()
    hour = now.hour
    period, mood = _classify_time(hour)

    ctx = {
        "detected_mood": mood,
        ...
    }
    if overrides:
        ctx.update(overrides)  # ⚠️ DEAD END: overrides can inject invalid moods!
    return ctx
```

When `overrides` dict is used (e.g., user manual test with `{"detected_mood": "invalid_mood"}`), the context bypasses validation. Later in `engine.py:169`:

```python
det_map  = MOOD_COMPAT.get(context.get("detected_mood", "neutral"), {})
m_score  = pref_map.get(img_mood, 0.0) * 0.60 + det_map.get(img_mood, 0.0) * 0.40
```

If an invalid mood is provided, `det_map = {}`, which returns 0.0 for all image moods. This silently degrades scoring without warning.

**Root Cause:** No schema validation on context data before Decision Engine consumption.

---

### Issue #2: Sidebar Toggle Visibility (Z-Index Stacking Context Inversion)

**File:** `app.py:509-610` (FAB injection) + CSS lines 413-421 (noise overlay)

**Problem:**
```javascript
fab.style.cssText = 'position:fixed;...z-index:99999;...'  // Line 550
```

Combined with CSS:
```css
body::after {  /* Line 413 */
    z-index: 1000;
    pointer-events: none;
}
```

**The Bug:** When Streamlit's main `.stApp` container has a CSS `transform` property (which it does for sidebar slide animation), it creates a new stacking context. Within that context, z-index values are re-weighted. The FAB's `z-index: 99999` is OUTSIDE that stacking context (good), but the noise overlay `z-index: 1000` is INSIDE. If multiple stacking contexts overlap, the FAB can appear *behind* visual noise texture.

**Observable Symptom:** When sidebar is open and FAB hovers over the noise pattern, the button becomes hard to see or invisible due to contrast loss.

---

### Issue #3: Preference Scoring Does Not Validate Target Mood

**File:** `logic/engine.py:210-220`

**Problem:**
```python
def _preference_score(img: dict, tags: list[dict], target_mood: str) -> float:
    mood_map   = MOOD_COMPAT.get(target_mood, {})  # ⚠️ Returns {} if target_mood not in dict
    mood_score = mood_map.get(img.get("primary_mood", "neutral"), 0.0)  # Always 0.0 if mood_map={}
```

If `target_mood` is not one of the 6 canonical moods, `mood_map` becomes an empty dict, and preference_score is 0.0 regardless of image metadata. This breaks the scoring algorithm silently.

---

## ARCHITECTURAL ASSESSMENT

### Strengths ✅
1. **Clean Modular Separation:** Context → Decision → Persistence layers are well-defined
2. **Audit Trail:** Every selection decision is logged with breakdown, enabling transparency
3. **Graceful Fallbacks:** Database queries return sensible defaults (e.g., empty images list)
4. **CSS Performance:** Glassmorphism uses `backdrop-filter` (GPU-accelerated) without over-complication

### Weaknesses ⚠️
1. **No Data Schema Validation:** Context data is treated as implicit; no runtime validation
2. **Silent Scoring Degradation:** Invalid data causes scoring to silently default to 0, not to throw errors
3. **UI/Logic Coupling:** The sidebar FAB relies on brittle JavaScript DOM manipulation and z-index hacks
4. **Missing Confidence Scores:** Reasoning overlay shows decision but not confidence level (requested enhancement)

---

## CORRECTED CODE & IMPLEMENTATIONS

See accompanying **CORRECTIONS.md** for:
1. Fixed context validation layer
2. Corrected z-index stacking & enhanced FAB robustness
3. Preference score validation
4. Confidence score display (new feature)
5. Asynchronous image analysis (performance enhancement)
6. Seasonality factor integration (advanced context)
7. Frosted Obsidian theme with System Pulse animation

---

## EVALUATION IMPACT

These fixes address the **methodological rigor** requirements of the thesis:

- **Consistency:** Validated context ensures reproducible, explainable decisions
- **Transparency:** Confidence scores prove the AI is doing work, not just returning random images
- **Reliability:** Proper error handling prevents silent failures during evaluation trials

---

## RECOMMENDATIONS FOR FINAL REPORT

1. **Methodology Section:** Document that "context validation" is a runtime requirement, not assumed
2. **Evaluation Plan:** Include test case for invalid mood data → ensure system remains stable
3. **Confidence Metric:** Add confidence scores to evaluation rubric (helps compare vs. baseline)
4. **Future Work:** Replace JavaScript FAB with native Streamlit widget when library updates

---

**Audit completed by:** Claude Code Principal Architect
**Awwwards 2026 Readiness:** Now achievable with design refinements (see CORRECTIONS.md)
