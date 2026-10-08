# PawPal+ Project Reflection

## 1. System Design

**Core user actions**

1. **Add a pet**: record a pet's name, species, and age so tasks can be attached to it.
2. **Schedule a care task**: give a pet a task (walk, feeding, medication, appointment) with a
   time, duration, priority, and whether it repeats daily or weekly.
3. **See today's schedule**: view the day's tasks in time order, get warned about clashes,
   and mark tasks done (recurring tasks roll forward automatically).

**a. Initial design**

My initial UML (`diagrams/uml_draft.mmd`) had four classes:

- **Task** (dataclass): one activity, with a description, an `HH:MM` time, a duration,
  a priority, a frequency, a due date, and a `completed` flag. Its responsibility is to know
  about itself, for example `mark_complete()`.
- **Pet** (dataclass): name, species, age, and a list of `Task`s. It owns its tasks and
  adds and removes them.
- **Owner**: has a name and a list of `Pet`s. It is the single entry point for reaching all
  the data (`get_all_tasks()`).
- **Scheduler**: holds a reference to an `Owner` and does the "thinking": collecting tasks,
  building today's schedule, sorting, and completing tasks.

Relationships: Owner *owns* many Pets, a Pet *has* many Tasks (composition), and the
Scheduler *reads from* the Owner. I kept the Scheduler separate from the Owner so the
data classes stay simple and all the algorithms live in one place.

**b. Design changes**

Yes. When I reviewed the skeleton, I found that a `Task` had no idea which pet it belonged
to. That caused two problems: (1) a combined schedule couldn't show the pet name next to
each task, and (2) `Scheduler.mark_task_complete(task)` couldn't add the next occurrence of
a recurring task to the right pet. I added a `pet_name` field to `Task` that
`Pet.add_task()` fills in automatically. I chose a name string rather than a full `Pet`
reference so tasks stay plain data that serializes cleanly to JSON.

Other changes during the build:

- `Owner` gained `available_minutes` (a daily time budget) so the scheduler could plan
  around a constraint.
- `Owner.add_pet()` rejects duplicate names, because `get_pet(name)` lookups depend on
  names being unique.
- Tasks validate their time, priority, and frequency when they're created, so bad data fails
  early instead of breaking a sort later.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler considers:

- **Time of day**: everything is ordered by start time.
- **Date**: only tasks due on the selected day appear in that day's schedule.
- **Duration**: used for overlap detection and free-slot search.
- **Priority** (high / medium / low): decides what makes it into the plan when time is short.
- **Owner's available minutes**: the budget for `build_daily_plan()`.
- **Completion status**: finished tasks don't count as conflicts or take up budget.

I ranked **priority** above everything else for planning. Missing a medication is worse
than missing grooming, so the plan fills the budget with high-priority tasks first. Time is
the tie-breaker and the display order, because that is how an owner actually goes through
their day.

**b. Tradeoffs**

**Conflict detection warns but never resolves.** `detect_conflicts()` returns warning
strings and leaves the schedule unchanged. It doesn't move tasks or raise errors. This is
reasonable here because some "conflicts" are fine in real life. An owner can give a cat its
flea drops while the dog eats breakfast, but the program can't know that. Reporting the
overlap and letting the human decide is safer than silently rescheduling medication.

A second tradeoff: **`build_daily_plan()` is greedy.** It walks tasks from high to low
priority and keeps each one that fits the remaining minutes. It does not search for the
combination that uses the most time (that would be a knapsack problem). It can leave a few
minutes unused, but the result is predictable and easy to explain ("skipped: needs 20 min,
only 0 min left"), which matters more to a pet owner than squeezing in one extra low-priority
task.

---

## 3. AI Collaboration

**a. How you used AI**

I used Claude Code in agent mode inside VS Code throughout the project:

- **Design**: turning my list of classes and attributes into a Mermaid class diagram,
  then reviewing the skeleton for missing relationships. That review is how the `pet_name`
  issue came up.
- **Implementation**: generating the dataclasses and the Scheduler methods across
  `pawpal_system.py`, `main.py`, and `app.py` in one pass.
- **Algorithms**: how to sort `"HH:MM"` strings with a `sorted()` lambda key, how to use
  `timedelta` for recurrence, and a lightweight way to detect overlaps.
- **Testing**: brainstorming edge cases such as back-to-back tasks, the same time on
  different days, and month-end rollover.
- **Streamlit**: how `st.session_state` keeps the `Owner` alive across reruns.

The most helpful prompts were specific and grounded in the code, for example "based on my
skeleton, how should the Scheduler retrieve all tasks from the Owner's pets?". Vague
prompts like "make it smarter" were much less useful.

**b. Judgment and verification**

- **Sorting by string vs. by minutes.** The obvious suggestion was
  `sorted(tasks, key=lambda t: t.time)`. That works for zero-padded times, but `"9:30"`
  would sort *after* `"10:00"` because strings compare character by character. I kept a
  small `to_minutes()` helper and wrote a test
  (`test_sort_by_time_compares_numerically_not_alphabetically`) to prove it.
- **Exact-match vs. overlap conflicts.** An exact time match was the simplest option, but
  it misses a 30-minute walk at 07:30 clashing with meds at 07:45. I chose overlap
  detection using durations. I also tested that back-to-back tasks (07:30–08:00, then
  08:00) are *not* flagged.
- **A more "Pythonic" filter.** When I asked how to simplify `filter_tasks()`, the
  suggestion was a single list comprehension with a long compound condition. It was shorter
  but harder to read, so I kept the explicit loop with two `continue` guards.
- I checked every change by running `python main.py` and reading the output, not only by
  trusting the tests. That is how I noticed the first "next free slot" demo printed a
  meaningless `07:00` (nothing was scheduled that early), so I changed the demo to show a
  real gap.
- While writing this reflection I found that completing the same recurring task twice
  created *two* future copies. I added a guard in `mark_task_complete()` and a regression
  test for it.

---

## 4. Testing and Verification

**a. What you tested**

There are 25 pytest tests covering:

- Task completion and adding tasks to a pet.
- Sorting by time (including non-zero-padded times) and by priority-then-time.
- Filtering by pet and by status.
- Daily and weekly recurrence, month-end rollover, one-time tasks not recurring, and no duplicate copies when a task is completed twice.
- Conflict detection: same time, overlapping durations, back-to-back, different days, and
  completed tasks ignored.
- The free-slot search, the time-budget plan, and the JSON save/load round trip.
- Edge cases: a pet with no tasks, invalid times, and duplicate pet names.

These matter because the scheduler's value comes from being *trustworthy*. A recurring
medication that silently fails to roll over, or a sort that puts 10:00 before 9:30, would
make the app worse than a paper list.

**b. Confidence**

I'd rate it **4/5**. All tests pass, and the CLI demo matches what I expect by hand.
If I had more time, I would test next:

- Tasks that cross midnight (e.g., 23:30 for 60 minutes).
- Renaming a pet after tasks are attached (`pet_name` would go stale).
- Automated UI tests for `app.py`.

---

## 5. Reflection

**a. What went well**

I'm most satisfied with the separation between `pawpal_system.py` and the UI. Because every
algorithm lives in `Scheduler`, the CLI demo, the tests, and the Streamlit app all call the
same methods. Wiring up the UI was mostly a matter of choosing Streamlit widgets.

**b. What you would improve**

- Store recurring tasks as a single *rule* and generate occurrences from it, instead of
  creating a new `Task` object each time one is completed.
- Use real `datetime.time` objects for task times instead of strings.
- Let the owner mark certain overlaps as "OK to do together" so warnings are less noisy.

**c. Key takeaway**

AI is very fast at producing code that *looks* right. My job as lead architect was to own
the design decisions (where data lives, which class is responsible for what, which tradeoffs
are acceptable) and to verify the output with tests and by actually running the program.
The best results came when I gave the AI a clear structure to fill in, not when I asked it
to decide the structure for me.
