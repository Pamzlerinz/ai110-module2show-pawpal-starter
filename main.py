"""CLI demo for PawPal+: builds sample data and exercises the Scheduler."""

import sys
from datetime import date

from pawpal_system import Owner, Pet, Scheduler, Task

sys.stdout.reconfigure(encoding="utf-8")  # so emoji print on Windows terminals

PRIORITY_ICON = {"high": "🔴", "medium": "🟡", "low": "🟢"}


def task_icon(description: str) -> str:
    """Pick an emoji based on keywords in the task description."""
    text = description.lower()
    for keyword, icon in [("walk", "🦮"), ("feed", "🍖"), ("breakfast", "🍖"),
                          ("dinner", "🍖"), ("med", "💊"), ("vet", "🏥"),
                          ("groom", "🛁"), ("brush", "🛁"), ("play", "🎾")]:
        if keyword in text:
            return icon
    return "🐾"


def print_tasks(title: str, tasks: list[Task]) -> None:
    """Print tasks as an aligned table with status and priority indicators."""
    print(f"\n{title}")
    print("-" * 66)
    if not tasks:
        print("  (no tasks)")
        return
    print(f"  {'Time':<6} {'Pet':<7} {'Task':<24} {'Min':>4}  {'Priority':<10} Status")
    for t in tasks:
        status = "✅ done" if t.completed else "⏳ todo"
        task = f"{task_icon(t.description)} {t.description}"
        print(f"  {t.time:<6} {t.pet_name:<7} {task:<24} {t.duration_minutes:>4}  "
              f"{PRIORITY_ICON[t.priority]} {t.priority:<7} {status}")


def main() -> None:
    today = date.today()
    owner = Owner("Jordan", available_minutes=60)
    mochi = Pet("Mochi", "dog", age=3)
    luna = Pet("Luna", "cat", age=5)
    owner.add_pet(mochi)
    owner.add_pet(luna)

    # Added deliberately out of chronological order.
    mochi.add_task(Task("Evening walk", "18:30", 30, "medium", "daily", today))
    mochi.add_task(Task("Morning walk", "07:30", 30, "high", "daily", today))
    luna.add_task(Task("Breakfast", "08:00", 10, "high", "daily", today))
    luna.add_task(Task("Flea medication", "07:45", 5, "high", "weekly", today))
    mochi.add_task(Task("Brush coat", "12:00", 20, "low", "once", today))
    luna.add_task(Task("Play session", "12:00", 15, "medium", "once", today))  # conflict!

    scheduler = Scheduler(owner)

    print(f"🐾 PawPal+ — Today's Schedule for {owner.name} ({today})")
    print_tasks("📅 All tasks, sorted by time", scheduler.todays_schedule(today))

    print("\n⚠️  Conflict check")
    print("-" * 66)
    for warning in scheduler.detect_conflicts() or ["No conflicts found."]:
        print(f"  {warning}")

    print_tasks("⭐ Sorted by priority, then time",
                scheduler.sort_by_priority(scheduler.todays_schedule(today)))

    mochi_tasks = scheduler.filter_tasks(pet_name="Mochi")
    print_tasks("🐶 Filter: Mochi's tasks only", scheduler.sort_by_time(mochi_tasks))

    # Complete a daily task -> the next day's occurrence is created automatically.
    morning_walk = mochi.tasks[1]
    next_walk = scheduler.mark_task_complete(morning_walk)
    print(f"\n🔁 Completed '{morning_walk.description}'. "
          f"Next occurrence created for {next_walk.due_date} at {next_walk.time}.")

    print_tasks("✅ Filter: completed tasks", scheduler.filter_tasks(completed=True))

    slot = scheduler.find_next_available_slot(45, today, day_start="07:30")
    print(f"\n🕒 Next free 45-minute slot after 07:30 today: {slot}")

    print(f"\n🧠 Daily plan within {owner.available_minutes} min budget")
    print("-" * 66)
    for line in scheduler.explain_plan(today):
        print(f"  {line}")


if __name__ == "__main__":
    main()
