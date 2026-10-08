# PawPal+ Project Reflection

## 1. System Design
 
**Core user actions**
 
1. **Add a pet**: record a pet's name, species, and age so tasks can be attached to it.
2. **Schedule a care task**: give a pet a task (walk, feeding, medication, appointment) with a
   time, duration, priority, and whether it repeats daily or weekly.
3. **See today's schedule**: view the day's tasks in time order, get warned about clashes,
   and mark tasks done (recurring tasks roll forward automatically).
**a. Initial design**
 
The initial UML (`diagrams/uml_draft.mmd`), which the agent drafted from the project brief,
had four classes:
 
- **Task** (dataclass): one activity, with a description, an `HH:MM` time, a duration,
  a priority, a frequency, a due date, and a `completed` flag. It knows about itself,
  for example `mark_complete()`.
- **Pet** (dataclass): name, species, age, and a list of `Task`s. It owns its tasks and
  adds and removes them.
- **Owner**: a name and a list of `Pet`s. It is the single entry point for reaching all
  the data (`get_all_tasks()`).
- **Scheduler**: holds a reference to an `Owner` and does the "thinking": collecting tasks,
  building today's schedule, sorting, and completing tasks.
Relationships: an Owner *owns* many Pets, a Pet *has* many Tasks (composition), and the
Scheduler *reads from* the Owner. Keeping the Scheduler separate from the Owner means the
data classes stay simple and all the algorithms live in one place, which made sense to me
when I read through the design.
 
**b. Design changes**
 
Yes. Between the skeleton and the final version, the design changed in a few ways:
 
- **`Task` gained a `pet_name` field.** In the skeleton, a task didn't know which pet it
  belonged to, so the combined schedule couldn't show the pet's name, and completing a
  recurring task couldn't add the next occurrence to the right pet. `Pet.add_task()` now
  fills in `pet_name` automatically. It's a name string rather than a full `Pet` reference
  so tasks save cleanly to JSON.
- **`Owner` gained `available_minutes`**, a daily time budget the scheduler plans around.
- **`Owner.add_pet()` rejects duplicate names**, because looking a pet up by name only
  works if names are unique.
- **Tasks validate their time, priority, and frequency when created**, so bad data fails
  right away instead of breaking a sort later.
These changes were made by the agent during the build. Comparing `uml_draft.mmd` with
`uml_final.mmd` shows them.
 
---

## 2. Scheduling Logic and Tradeoffs
 
**a. Constraints and priorities**
 
The scheduler considers:
 
- **Time of day**: everything is ordered by start time.
- **Date**: only tasks due on the selected day appear in that day's schedule.
- **Duration**: used to detect overlaps and to find free time slots.
- **Priority** (high / medium / low): decides what makes it into the plan when time is short.
- **Owner's available minutes**: the time budget for `build_daily_plan()`.
- **Completion status**: finished tasks don't count as conflicts or use up the budget.
Priority matters most when building the plan: high-priority tasks fill the budget first.
That makes sense for pets, because missing a medication is worse than missing a grooming
session. Time is the tie-breaker and the display order, because that's how an owner
actually goes through their day.
 
**b. Tradeoffs**
 
**Conflict detection warns but doesn't fix anything.** `detect_conflicts()` returns warning
messages and leaves the schedule as it is. It doesn't move tasks around. That's reasonable
because some overlaps are fine in real life (an owner can give the cat flea drops while the
dog eats breakfast), and the program can't know which ones. Letting the owner decide is
safer than the app silently moving a medication.
 
**The daily plan is "greedy."** `build_daily_plan()` goes through tasks from high to low
priority and keeps each one that still fits in the remaining minutes. It doesn't search
every combination to use the time as fully as possible, so it can leave a few minutes
unused. In exchange, the result is predictable and easy to explain (for example,
"skipped: needs 20 min, only 0 min left").
 
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
 
The project has 25 pytest tests (written by the agent), covering:
 
- Completing tasks and adding tasks to a pet.
- Sorting by time (including times like `9:30` without a leading zero) and by priority.
- Filtering by pet and by done/not-done status.
- Daily and weekly recurrence, rolling over at the end of a month, one-time tasks not
  repeating, and no duplicate copies when a task is completed twice.
- Conflict detection: same time, overlapping durations, back-to-back tasks, different days,
  and ignoring completed tasks.
- Finding a free time slot, the time-budget plan, and saving/loading JSON.
- Edge cases: a pet with no tasks, invalid times, and duplicate pet names.
These matter because a scheduler is only useful if you can trust it. A recurring medication
that doesn't roll over, or a sort that puts 10:00 before 9:30, would make the app worse than
a paper list.
 
**b. Confidence**
 
I'd rate it **4/5**. All 25 tests pass, and when I ran the app myself it worked as expected.
I'm not giving it a 5 because I relied on the agent's tests rather than writing my own.
Things I'd test next:
 
- Tasks that cross midnight (for example, a 60-minute task at 23:30 and another at 00:15
  the next day).
- Renaming a pet after tasks are attached (each task's `pet_name` would be out of date).
- Automated tests for the Streamlit UI in `app.py`.

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
