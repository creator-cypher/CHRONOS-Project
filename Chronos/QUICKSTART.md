# Chronos — Quickstart

## Requirements
- Python 3.11+
- A Gemini API key (already in `.env`)

## Setup & Run

```bash
cd Chronos
pip install -r requirements.txt
streamlit run app.py
```

Browser opens automatically at `http://localhost:8501`.

## First Use

1. Click **>** to open the sidebar
2. Go to **＋ Upload Image** — upload any photo
3. Click **Save & Analyse** — Gemini tags it automatically
4. The frame displays it immediately

The display auto-refreshes every **5 minutes** and selects the best image for the current time of day.

---

## Running the Baseline (Comparison)

The static slideshow baseline cycles images with **no AI scoring** — used as the control condition for evaluation.

```bash
# Run alongside the adaptive app on a different port
streamlit run app_baseline.py --server.port 8502
```

Open `http://localhost:8502` to view the baseline.
Use **Prev / Next / Shuffle** to navigate images manually.

---

## Running the Scenario Test Runner

The scenario runner evaluates the decision engine across predefined contexts and prints a structured report.

```bash
# Must be run with python (not streamlit run)
python tests/scenario_runner.py

# Scores only — no interaction summary or Test 4
python tests/scenario_runner.py --quiet
```

**What it tests:**

| Test | Description |
|------|-------------|
| Test 1 | Time period coverage — dawn / morning / afternoon / evening / night |
| Test 2 | Sensitivity levels — low / medium / high (afternoon context) |
| Test 3 | Preferred mood override — all 6 moods (evening context) |
| Test 4 | Interaction signal — does like/skip shift scores? |

All scenario runs are saved to `context_logs` and visible in the main app under **Recent History**.

---

## Like / Skip Feedback

In the sidebar under **Now Displaying**, use **👍 Like** and **⊘ Skip** to give feedback.
Each net like adds +0.05 to that image's score (capped at ±0.15), nudging future selections.
