# PawPal+ 🐾

**PawPal+** is a pet care planning assistant. It helps a busy owner track feedings, walks,
medications, and appointments for several pets, then uses scheduling logic to sort, filter,
de-conflict, and prioritize those tasks.

The project follows a **CLI-first** workflow. All logic lives in `pawpal_system.py`. It was
verified with a terminal demo (`main.py`) and a pytest suite before being connected to the
Streamlit UI (`app.py`).

## Getting started

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python main.py          # CLI demo
python -m pytest        # test suite
streamlit run app.py    # web app
```

## Project structure

| File | Purpose |
|------|---------|
| `pawpal_system.py` | Logic layer: `Task`, `Pet`, `Owner`, `Scheduler` |
| `main.py` | CLI demo that exercises every scheduler feature |
| `app.py` | Streamlit UI wired to the logic layer |
| `tests/test_pawpal.py` | pytest suite (25 tests) |
| `diagrams/uml_draft.mmd` | Phase 1 UML draft |
| `diagrams/uml_final.mmd` | Final UML matching the implementation (also copied to `diagrams/uml.mmd`) |

## Architecture

- **`Task`** (dataclass): one activity, with a description, an `"HH:MM"` time, a duration,
  a priority (`low` / `medium` / `high`), a frequency (`once` / `daily` / `weekly`), a due
  date, a completion flag, and the name of the pet it belongs to.
- **`Pet`** (dataclass): pet details plus its list of tasks.
- **`Owner`**: manages several pets, has a daily time budget (`available_minutes`), and
  handles JSON save and load.
- **`Scheduler`**: the "brain". It reads every task through `Owner.get_all_tasks()` and
  sorts, filters, completes, de-conflicts, and plans them.

See [`diagrams/uml_final.mmd`](diagrams/uml_final.mmd) for the full class diagram.

## ✨ Features

- **Sorting by time**: tasks are returned in chronological order. Times are compared as
  minutes after midnight, not as text.
- **Priority sorting**: high → medium → low, with ties broken by start time.
- **Filtering** by pet name and/or completion status.
- **Daily and weekly recurrence**: completing a recurring task automatically creates the
  next occurrence one day or one week later.
- **Conflict warnings**: tasks whose time windows overlap on the same day are reported as
  readable warnings. The program never crashes on a conflict.
- **Next available slot**: finds the earliest gap in the day that fits a task of a given
  length.
- **Time-budget daily plan**: picks the highest-priority tasks that fit in the owner's
  available minutes and explains why each task was included or skipped.
- **JSON persistence**: pets and tasks are saved to `data.json` and reloaded on the next run.
- **Formatted output**: emoji task icons, color-coded priority dots, and aligned CLI tables.
  See the Output Formatting section below.

## 🎨 Output Formatting

| Feature | Where | How |
|---------|-------|-----|
| Emoji task icons (🦮 walk, 🍖 food, 💊 meds, 🏥 vet, 🛁 grooming, 🎾 play) | `task_icon()` in `main.py` | Keyword match on the task description |
| Color-coded priority (🔴 high, 🟡 medium, 🟢 low) | `PRIORITY_ICON` in `main.py` and `app.py` | Lookup dict |
| Status indicators (✅ done / ⏳ todo) | `print_tasks()` in `main.py`, `task_rows()` in `app.py` | Based on `Task.completed` |
| Aligned CLI tables | `print_tasks()` in `main.py` | f-string width specifiers (`:<6`, `:>4`), no external library |
| UI tables and alerts | `app.py` | `st.dataframe`, `st.warning` (conflicts and skipped tasks), `st.success` (completions and free slots), `st.info`, `st.error` |

## 📐 Smarter Scheduling

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | `Scheduler.sort_by_time()`, `Scheduler.sort_by_priority()` | `sorted()` with a lambda key. `"HH:MM"` is converted with `to_minutes()` so `"9:30"` sorts before `"10:00"`. Priority sort uses the tuple key `(priority_rank, minutes)`. |
| Filtering | `Scheduler.filter_tasks(tasks, pet_name, completed)`, `Scheduler.todays_schedule(day)` | `None` means "don't filter on this". Pet names match case-insensitively. `todays_schedule` keeps only tasks due that day. |
| Conflict handling | `Scheduler.detect_conflicts()` | Groups pending tasks by date, sorts each day, and checks whether a task starts before the previous one ends (`start + duration`). Returns a list of warning strings. Back-to-back tasks do not count as conflicts. |
| Recurring tasks | `Task.next_occurrence()`, `Scheduler.mark_task_complete()` | Uses `timedelta(days=1)` or `timedelta(weeks=1)`, so month and year rollovers are handled correctly. The new task is added to the same pet automatically. |
| Next free slot | `Scheduler.find_next_available_slot()` | Walks the sorted busy windows and returns the first gap that is long enough, or `None`. |
| Budget planning | `Scheduler.build_daily_plan()`, `Scheduler.explain_plan()` | Greedy by priority: a task is kept if it fits in the remaining minutes. Skipped tasks come with a reason. |

## 🖥️ Sample Output

Output of `python main.py`:

```
🐾 PawPal+ — Today's Schedule for Jordan (2026-10-08)

📅 All tasks, sorted by time
------------------------------------------------------------------
  Time   Pet     Task                      Min  Priority   Status
  07:30  Mochi   🦮 Morning walk             30  🔴 high    ⏳ todo
  07:45  Luna    💊 Flea medication           5  🔴 high    ⏳ todo
  08:00  Luna    🍖 Breakfast                10  🔴 high    ⏳ todo
  12:00  Mochi   🛁 Brush coat               20  🟢 low     ⏳ todo
  12:00  Luna    🎾 Play session             15  🟡 medium  ⏳ todo
  18:30  Mochi   🦮 Evening walk             30  🟡 medium  ⏳ todo

⚠️  Conflict check
------------------------------------------------------------------
  Conflict on 2026-10-08: 'Morning walk' (07:30, 30 min) overlaps 'Flea medication' (07:45) - Mochi and Luna
  Conflict on 2026-10-08: 'Brush coat' (12:00, 20 min) overlaps 'Play session' (12:00) - Mochi and Luna

⭐ Sorted by priority, then time
------------------------------------------------------------------
  Time   Pet     Task                      Min  Priority   Status
  07:30  Mochi   🦮 Morning walk             30  🔴 high    ⏳ todo
  07:45  Luna    💊 Flea medication           5  🔴 high    ⏳ todo
  08:00  Luna    🍖 Breakfast                10  🔴 high    ⏳ todo
  12:00  Luna    🎾 Play session             15  🟡 medium  ⏳ todo
  18:30  Mochi   🦮 Evening walk             30  🟡 medium  ⏳ todo
  12:00  Mochi   🛁 Brush coat               20  🟢 low     ⏳ todo

🐶 Filter: Mochi's tasks only
------------------------------------------------------------------
  Time   Pet     Task                      Min  Priority   Status
  07:30  Mochi   🦮 Morning walk             30  🔴 high    ⏳ todo
  12:00  Mochi   🛁 Brush coat               20  🟢 low     ⏳ todo
  18:30  Mochi   🦮 Evening walk             30  🟡 medium  ⏳ todo

🔁 Completed 'Morning walk'. Next occurrence created for 2026-10-09 at 07:30.

✅ Filter: completed tasks
------------------------------------------------------------------
  Time   Pet     Task                      Min  Priority   Status
  07:30  Mochi   🦮 Morning walk             30  🔴 high    ✅ done

🕒 Next free 45-minute slot after 07:30 today: 08:10

🧠 Daily plan within 60 min budget
------------------------------------------------------------------
  07:45 Flea medication (Luna) - included: high priority, 5 min
  08:00 Breakfast (Luna) - included: high priority, 10 min
  12:00 Play session (Luna) - included: medium priority, 15 min
  18:30 Evening walk (Mochi) - included: medium priority, 30 min
  SKIPPED Brush coat (Mochi) - needs 20 min, only 0 min left
```

## 🧪 Testing PawPal+

```bash
python -m pytest
```

The suite in `tests/test_pawpal.py` covers:

- **Basics**: `mark_complete()` flips status, `add_task()` increases the task count and tags
  the pet name, invalid times and duplicate pet names are rejected.
- **Sorting**: chronological order, numeric (not alphabetical) time comparison,
  priority-then-time ordering, and only the selected day's tasks in the schedule.
- **Filtering**: by pet, by status, and both together.
- **Recurrence**: daily → +1 day, weekly → +7 days, month-end rollover, one-time tasks do not
  recur, completing a task twice does not duplicate it.
- **Conflicts**: exact same time across pets, overlapping durations for one pet, back-to-back
  tasks (no conflict), the same time on different days (no conflict), completed tasks ignored.
- **Planning**: free-slot search (including a fully booked day) and the time-budget plan.
- **Persistence**: JSON save and load round trip.
- **Edge case**: a pet with no tasks produces an empty schedule and no conflicts.

```
============================= test session starts =============================
platform win32 -- Python 3.14.5, pytest-9.1.1, pluggy-1.6.0
collecting ... collected 25 items

tests/test_pawpal.py::test_mark_complete_changes_status PASSED           [  4%]
tests/test_pawpal.py::test_add_task_increases_pet_task_count PASSED      [  8%]
tests/test_pawpal.py::test_add_task_tags_task_with_pet_name PASSED       [ 12%]
tests/test_pawpal.py::test_invalid_time_is_rejected PASSED               [ 16%]
tests/test_pawpal.py::test_duplicate_pet_name_is_rejected PASSED         [ 20%]
tests/test_pawpal.py::test_sort_by_time_returns_chronological_order PASSED [ 24%]
tests/test_pawpal.py::test_sort_by_time_compares_numerically_not_alphabetically PASSED [ 28%]
tests/test_pawpal.py::test_sort_by_priority_then_time PASSED             [ 32%]
tests/test_pawpal.py::test_todays_schedule_only_includes_that_day PASSED [ 36%]
tests/test_pawpal.py::test_pet_with_no_tasks_gives_empty_schedule PASSED [ 40%]
tests/test_pawpal.py::test_filter_by_pet_and_status PASSED               [ 44%]
tests/test_pawpal.py::test_completing_daily_task_creates_next_day_task PASSED [ 48%]
tests/test_pawpal.py::test_completing_weekly_task_creates_task_seven_days_later PASSED [ 52%]
tests/test_pawpal.py::test_recurrence_rolls_over_month_end PASSED        [ 56%]
tests/test_pawpal.py::test_completing_one_time_task_does_not_recur PASSED [ 60%]
tests/test_pawpal.py::test_completing_task_twice_does_not_duplicate_next_occurrence PASSED [ 64%]
tests/test_pawpal.py::test_detects_exact_same_time_across_pets PASSED    [ 68%]
tests/test_pawpal.py::test_detects_overlapping_durations_for_same_pet PASSED [ 72%]
tests/test_pawpal.py::test_back_to_back_tasks_do_not_conflict PASSED     [ 76%]
tests/test_pawpal.py::test_same_time_on_different_days_does_not_conflict PASSED [ 80%]
tests/test_pawpal.py::test_completed_tasks_are_ignored_for_conflicts PASSED [ 84%]
tests/test_pawpal.py::test_next_available_slot_skips_busy_windows PASSED [ 88%]
tests/test_pawpal.py::test_next_available_slot_returns_none_when_day_is_full PASSED [ 92%]
tests/test_pawpal.py::test_daily_plan_respects_time_budget_and_priority PASSED [ 96%]
tests/test_pawpal.py::test_save_and_load_round_trip PASSED               [100%]

============================= 25 passed in 0.13s ==============================
```

**Confidence level: ⭐⭐⭐⭐ (4/5).** All 25 tests pass and cover the main paths and the
important edge cases. One star is held back because the UI is only checked by hand, and
inputs like tasks that run past midnight are not handled yet.

## 💾 Data Persistence

- `Owner.save_to_json(path)` writes the owner, pets, and tasks to `data.json`. Dates are
  stored as ISO strings.
- `Owner.load_from_json(path)` rebuilds everything through `Pet.from_dict()` and
  `Task.from_dict()`.
- `app.py` loads `data.json` on first run if it exists and saves after every change.
  "Reset all data" in the sidebar deletes it. `data.json` is git-ignored.
- Files modified: `pawpal_system.py` (the `to_dict`/`from_dict` methods and the save/load
  methods), `app.py`, and `.gitignore`.

## 📸 Demo Walkthrough

**Main UI features** (`streamlit run app.py`):

- **Sidebar**: set the owner's name and the minutes available for pet care today, or reset
  all data.
- **1. Your pets**: add a pet (name, species, age). Duplicate names show an error.
- **2. Schedule a task**: choose a pet, then enter a description, date, time, duration,
  priority, and how often it repeats (once / daily / weekly).
- **3. Schedule**: pick a day, filter by pet and status, and sort by time or priority. Conflicts
  appear in an `st.warning` box above the table, naming both tasks and pets so the owner
  knows what to move. Choose a pending task and click **Mark done ✅**. A recurring task then
  shows an `st.success` message saying when its next occurrence was added.
- **4. Smart planning**: the **Daily plan** tab shows which tasks fit the time budget, with
  a warning for each skipped task. The **Find a free slot** tab returns the earliest gap of
  the requested length.

**Example workflow:**

1. Add a dog named **Mochi** and a cat named **Luna**.
2. Schedule "Morning walk" for Mochi at 07:30 (30 min, high, daily) and "Flea medication"
   for Luna at 07:45 (5 min, high, weekly).
3. Open **Schedule**. The tasks appear in time order, and a yellow warning says the walk and
   the medication overlap.
4. Mark "Morning walk" done. Its status changes to ✅, and a success message says
   tomorrow's walk was created. Switch the day picker to tomorrow to see it.
5. Lower the time budget in the sidebar and open **Daily plan** to see low-priority tasks get
   skipped, with the reason for each.

**Key scheduler behaviors shown:** time and priority sorting, pet and status filtering,
overlap conflict warnings, automatic daily and weekly recurrence, free-slot search, and
budget-based planning. The CLI version of the same behaviors is in the Sample Output
section above.
