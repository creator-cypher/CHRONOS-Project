# CHRONOS Quick Reference Guide
**For rapid deployment and testing**

---

## 🚀 Startup (30 seconds)

```bash
cd Chronos
streamlit run app.py
# Opens http://localhost:8501 automatically
```

## 📋 What You'll See

1. **Full-screen image** with soft fade-in
2. **Status bar** (top-left): Time + "AI active" pulse indicator
3. **Reasoning overlay** (bottom-center): Decision explanation + confidence %
4. **Sidebar** (click toggle ➜ icon, top-right): Control dashboard

---

## 🎮 First Test Run

1. **Upload Image**
   - Sidebar → "+ Upload Image"
   - Pick any photo
   - Click "Save & Analyse"
   - Wait 5-10 sec (Gemini API call)

2. **See the Frame Change**
   - Image displays automatically
   - Notice reasoning: "Afternoon + Joyful... 82% Match"
   - Confidence % tells you how sure the system is

3. **Try Feedback**
   - Click 👍 "Like" or ⊘ "Skip" in sidebar
   - Next refresh will adjust scoring

---

## ⚙️ Run Full Test Suite

```bash
python tests/scenario_runner.py
# Should see: 32/32 PASSED ✅
# Takes ~60 seconds
```

---

## 🔧 Adjust Settings

| Control | What It Does |
|---------|------------|
| **Mood** dropdown | Pick your preferred mood (always considered) |
| **Sensitivity** radio | How much to follow time-of-day vs. your preference |
| **Per-Period Moods** | Override mood for specific time (e.g., "energetic" in morning) |
| **Manual Override** | Force a specific image to always display |

---

## 📊 View Decision History

**In Sidebar:** Recent History section shows last 10 decisions with:
- Timestamp
- Selected image
- Total score
- Matched tags
- Reasoning

**In Database:** All decisions logged in `chronos.db`
```bash
sqlite3 Chronos/chronos.db "SELECT timestamp, reasoning_text FROM context_logs LIMIT 5;"
```

---

## 🎨 Theme & Styling

- **Color scheme:** Near-black background (rgba 10,10,15)
- **Glassmorphism:** Blur 30px, saturate 200%
- **Accent color:** Purple (#a78bfa)
- **Font:** Inter (variable weights)

To customize: Edit `app.py` lines 78-497 (CSS section)

---

## 🤖 AI Configuration

- **Model:** Gemini 2.5-Flash
- **Prompt:** Structured JSON (poetic description + mood + time + tags)
- **API Key:** Set in `.env` file
- **Timeout:** 15 seconds per image

To use different AI: Modify `services/vision.py`

---

## 🐛 Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| Button not visible | Hard refresh (Ctrl+Shift+R); check browser zoom |
| Image analysis stuck | Check `.env` has GEMINI_API_KEY; API quota? |
| Database corrupted | Delete `chronos.db`; restart (recreates on boot) |
| UI looks broken | Clear browser cache; try different browser |

---

## 📈 Metrics to Track

For thesis evaluation:

```bash
# Selection consistency (should never repeat same image within 60min)
SELECT image_id, COUNT(*) FROM context_logs
GROUP BY image_id HAVING COUNT(*) > 1;

# Average confidence (should be 65-85%)
SELECT AVG(CAST(json_extract(score_breakdown, '$.time') AS REAL)) FROM context_logs;

# Tag matching rate (higher is better)
SELECT AVG(json_array_length(matched_tags)) FROM context_logs;
```

---

## 🎓 For Your Thesis

### Show in Defense
1. Run app.py → demonstrate mood/time switching
2. Show sidebar toggle (fixed, always visible)
3. Display reasoning overlay (confidence %)
4. Run scenario tests → all pass
5. Open TECHNICAL_MANIFEST.md → system architecture

### Key Points to Emphasize
- "Context Layer validates all data → no silent failures"
- "Decision Engine produces confidence scores → transparency"
- "Seasonality factor → advanced context awareness"
- "32 automated tests → systematic verification"

### Expected Questions & Answers
- **"How did you verify it works?"** → Scenario test suite (32 tests)
- **"What's novel?"** → Seasonality integration + confidence transparency
- **"How is it better than baseline?"** → Adaptive + learns from feedback + context-aware
- **"Did you find bugs?"** → Yes, 3 critical ones (now fixed) — shows rigor!

---

## 📞 Support

**For Code Issues:** Check `AUDIT_REPORT.md` (detailed explanations)
**For Architecture:** Check `TECHNICAL_MANIFEST.md` (complete reference)
**For Testing:** Check `EVALUATION_PROTOCOL.md` (methodology)
**For Status:** Check `IMPLEMENTATION_LOG.md` (what's done)

---

**Version:** 1.0 (Post-Audit)
**Last Updated:** February 28, 2026
**Status:** ✅ Production Ready

