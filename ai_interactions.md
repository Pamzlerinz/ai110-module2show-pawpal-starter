# AI Interactions Log

> **Stretch features only.** Only fill in the sections that apply to stretch features you attempted. If you did not attempt a stretch feature, leave its section blank or delete it. This file is not required for the core project.

---

## Agent Workflow (SF7)

> Document your experience using an AI agent (e.g., Cursor Agent, Claude, Copilot) to make multi-step changes autonomously.

**What task did you give the agent?**

I gave Claude Code (agent mode in VS Code) the full PawPal+ project brief and asked it to
work through the phases: UML → class skeleton → implementation → CLI demo → tests →
Streamlit integration → docs. I also asked for a third algorithmic capability beyond
sorting, filtering, recurrence, and conflicts.

**What did the agent do?**

Files created or modified:

| File | Change |
|------|--------|
| `diagrams/uml_draft.mmd`, `diagrams/uml_final.mmd`, `diagrams/uml.mmd` | Draft and final class diagrams |
| `pawpal_system.py` | Skeleton, then the full `Task` / `Pet` / `Owner` / `Scheduler` implementation |
| `main.py` | CLI demo with formatted tables |
| `tests/test_pawpal.py` | 25 pytest tests |
| `app.py` | Streamlit UI using `st.session_state` and the Scheduler methods |
| `.gitignore` | Ignore `data.json` |
| `README.md`, `reflection.md` | Documentation |

Steps:

1. Wrote the draft UML and stub classes, then committed (`chore: add class skeletons from UML`).
2. Implemented the logic layer, including the extra capabilities:
   `find_next_available_slot()` (earliest free gap) and `build_daily_plan()` /
   `explain_plan()` (greedy, priority-first planning within the owner's time budget).
3. Ran `python main.py`, read the output, and adjusted the demo.
4. Ran `python -m pytest` until all tests passed.
5. Drove `app.py` headlessly with Streamlit's `AppTest` to check that adding a pet, adding
   tasks, and marking a task done all work and save to `data.json`.
6. Pasted the real CLI and pytest output into the README.

**What did you have to verify or fix manually?**

- The first demo run printed `Next free 45-minute slot: 07:00`. That was correct but
  meaningless, because nothing was scheduled that early. The demo was changed to search
  after 07:30 so it shows a real gap (08:10).
- The pet filter output in the demo wasn't time-sorted, so `sort_by_time()` was added there.
- The ✂️ emoji broke the CLI column alignment and was swapped for 🛁.
- The first headless UI test failed with `ModuleNotFoundError`. This was a problem in the
  test harness (`AppTest` doesn't add the app folder to `sys.path`), not in the app.
- A review found that completing an already-completed recurring task created a duplicate
  future copy. A guard and a regression test were added.
- I reviewed the conflict-detection tradeoff (overlap vs. exact match) and the greedy
  planner, and recorded the decisions in `reflection.md`.

---

## Prompt Comparison (SF11)

> Compare two different prompts (or two different models) on the same task.

| | Option A | Option B |
|-|----------|----------|
| **Model / tool used** | | |
| **Prompt** | | |
| **Response summary** | | |
| **What was useful** | | |
| **Problems noticed** | | |
| **Decision** | | |

**Which approach did you use in your final implementation and why?**

<!-- Your conclusion -->
