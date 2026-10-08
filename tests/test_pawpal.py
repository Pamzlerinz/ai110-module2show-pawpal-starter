"""Automated tests for the PawPal+ logic layer."""

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pawpal_system import Owner, Pet, Scheduler, Task  # noqa: E402

DAY = date(2026, 1, 15)


@pytest.fixture
def owner():
    """An owner with two pets and no tasks."""
    owner = Owner("Jordan", available_minutes=60)
    owner.add_pet(Pet("Mochi", "dog"))
    owner.add_pet(Pet("Luna", "cat"))
    return owner


@pytest.fixture
def scheduler(owner):
    return Scheduler(owner)


# --- basic behavior -------------------------------------------------------

def test_mark_complete_changes_status():
    task = Task("Walk", "08:00", due_date=DAY)
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


def test_add_task_increases_pet_task_count():
    pet = Pet("Mochi", "dog")
    assert pet.task_count() == 0
    pet.add_task(Task("Walk", "08:00", due_date=DAY))
    assert pet.task_count() == 1


def test_add_task_tags_task_with_pet_name():
    pet = Pet("Mochi", "dog")
    task = Task("Walk", "08:00", due_date=DAY)
    pet.add_task(task)
    assert task.pet_name == "Mochi"


def test_invalid_time_is_rejected():
    with pytest.raises(ValueError):
        Task("Walk", "25:99")


def test_duplicate_pet_name_is_rejected(owner):
    with pytest.raises(ValueError):
        owner.add_pet(Pet("mochi", "dog"))


# --- sorting --------------------------------------------------------------

def test_sort_by_time_returns_chronological_order(owner, scheduler):
    mochi = owner.get_pet("Mochi")
    for t in ["18:30", "07:05", "12:00", "09:45"]:
        mochi.add_task(Task(f"Task {t}", t, due_date=DAY))
    times = [t.time for t in scheduler.sort_by_time(scheduler.get_all_tasks())]
    assert times == ["07:05", "09:45", "12:00", "18:30"]


def test_sort_by_time_compares_numerically_not_alphabetically(scheduler):
    tasks = [Task("Late", "10:00", due_date=DAY), Task("Early", "9:30", due_date=DAY)]
    assert [t.description for t in scheduler.sort_by_time(tasks)] == ["Early", "Late"]


def test_sort_by_priority_then_time(scheduler):
    tasks = [
        Task("Low early", "07:00", priority="low", due_date=DAY),
        Task("High late", "17:00", priority="high", due_date=DAY),
        Task("High early", "08:00", priority="high", due_date=DAY),
        Task("Medium", "06:00", priority="medium", due_date=DAY),
    ]
    order = [t.description for t in scheduler.sort_by_priority(tasks)]
    assert order == ["High early", "High late", "Medium", "Low early"]


def test_todays_schedule_only_includes_that_day(owner, scheduler):
    mochi = owner.get_pet("Mochi")
    mochi.add_task(Task("Today", "08:00", due_date=DAY))
    mochi.add_task(Task("Tomorrow", "07:00", due_date=DAY + timedelta(days=1)))
    assert [t.description for t in scheduler.todays_schedule(DAY)] == ["Today"]


def test_pet_with_no_tasks_gives_empty_schedule(scheduler):
    assert scheduler.todays_schedule(DAY) == []
    assert scheduler.detect_conflicts() == []


# --- filtering ------------------------------------------------------------

def test_filter_by_pet_and_status(owner, scheduler):
    owner.get_pet("Mochi").add_task(Task("Walk", "08:00", due_date=DAY))
    done = Task("Feed", "09:00", due_date=DAY)
    owner.get_pet("Luna").add_task(done)
    done.mark_complete()

    assert [t.description for t in scheduler.filter_tasks(pet_name="luna")] == ["Feed"]
    assert [t.description for t in scheduler.filter_tasks(completed=False)] == ["Walk"]
    assert scheduler.filter_tasks(pet_name="Mochi", completed=True) == []


# --- recurrence -----------------------------------------------------------

def test_completing_daily_task_creates_next_day_task(owner, scheduler):
    mochi = owner.get_pet("Mochi")
    walk = Task("Walk", "08:00", frequency="daily", due_date=DAY)
    mochi.add_task(walk)

    next_walk = scheduler.mark_task_complete(walk)

    assert walk.completed is True
    assert next_walk.due_date == DAY + timedelta(days=1)
    assert next_walk.completed is False
    assert next_walk.time == "08:00"
    assert next_walk in mochi.tasks
    assert mochi.task_count() == 2


def test_completing_weekly_task_creates_task_seven_days_later(owner, scheduler):
    luna = owner.get_pet("Luna")
    meds = Task("Flea meds", "07:45", frequency="weekly", due_date=DAY)
    luna.add_task(meds)
    assert scheduler.mark_task_complete(meds).due_date == DAY + timedelta(days=7)


def test_recurrence_rolls_over_month_end(owner, scheduler):
    mochi = owner.get_pet("Mochi")
    walk = Task("Walk", "08:00", frequency="daily", due_date=date(2026, 1, 31))
    mochi.add_task(walk)
    assert scheduler.mark_task_complete(walk).due_date == date(2026, 2, 1)


def test_completing_one_time_task_does_not_recur(owner, scheduler):
    mochi = owner.get_pet("Mochi")
    vet = Task("Vet visit", "10:00", frequency="once", due_date=DAY)
    mochi.add_task(vet)
    assert scheduler.mark_task_complete(vet) is None
    assert mochi.task_count() == 1


# --- conflict detection ---------------------------------------------------

def test_detects_exact_same_time_across_pets(owner, scheduler):
    owner.get_pet("Mochi").add_task(Task("Walk", "12:00", 20, due_date=DAY))
    owner.get_pet("Luna").add_task(Task("Play", "12:00", 15, due_date=DAY))
    warnings = scheduler.detect_conflicts()
    assert len(warnings) == 1
    assert "Walk" in warnings[0] and "Play" in warnings[0]


def test_detects_overlapping_durations_for_same_pet(owner, scheduler):
    mochi = owner.get_pet("Mochi")
    mochi.add_task(Task("Walk", "07:30", 30, due_date=DAY))
    mochi.add_task(Task("Breakfast", "07:45", 10, due_date=DAY))
    assert len(scheduler.detect_conflicts()) == 1


def test_back_to_back_tasks_do_not_conflict(owner, scheduler):
    mochi = owner.get_pet("Mochi")
    mochi.add_task(Task("Walk", "07:30", 30, due_date=DAY))
    mochi.add_task(Task("Breakfast", "08:00", 10, due_date=DAY))
    assert scheduler.detect_conflicts() == []


def test_same_time_on_different_days_does_not_conflict(owner, scheduler):
    mochi = owner.get_pet("Mochi")
    mochi.add_task(Task("Walk", "08:00", due_date=DAY))
    mochi.add_task(Task("Walk", "08:00", due_date=DAY + timedelta(days=1)))
    assert scheduler.detect_conflicts() == []


def test_completed_tasks_are_ignored_for_conflicts(owner, scheduler):
    mochi = owner.get_pet("Mochi")
    walk = Task("Walk", "08:00", 30, due_date=DAY)
    mochi.add_task(walk)
    mochi.add_task(Task("Feed", "08:10", due_date=DAY))
    walk.mark_complete()
    assert scheduler.detect_conflicts() == []


# --- planning -------------------------------------------------------------

def test_next_available_slot_skips_busy_windows(owner, scheduler):
    mochi = owner.get_pet("Mochi")
    mochi.add_task(Task("Walk", "07:00", 30, due_date=DAY))
    mochi.add_task(Task("Feed", "07:40", 10, due_date=DAY))
    # 07:30-07:40 is only 10 min, so a 20-min task must wait until 07:50.
    assert scheduler.find_next_available_slot(20, DAY, day_start="07:00") == "07:50"


def test_next_available_slot_returns_none_when_day_is_full(owner, scheduler):
    owner.get_pet("Mochi").add_task(Task("Long outing", "07:00", 600, due_date=DAY))
    assert scheduler.find_next_available_slot(60, DAY, "07:00", "17:00") is None


def test_daily_plan_respects_time_budget_and_priority(owner, scheduler):
    mochi = owner.get_pet("Mochi")
    mochi.add_task(Task("Grooming", "09:00", 40, priority="low", due_date=DAY))
    mochi.add_task(Task("Walk", "18:00", 30, priority="high", due_date=DAY))
    mochi.add_task(Task("Meds", "08:00", 20, priority="high", due_date=DAY))

    planned, skipped = scheduler.build_daily_plan(DAY)  # budget is 60 minutes

    assert [t.description for t in planned] == ["Meds", "Walk"]  # time-ordered
    assert [t.description for t, _ in skipped] == ["Grooming"]


# --- persistence ----------------------------------------------------------

def test_save_and_load_round_trip(owner, tmp_path):
    owner.get_pet("Mochi").add_task(
        Task("Walk", "08:00", 30, "high", "daily", DAY, completed=True)
    )
    path = tmp_path / "data.json"
    owner.save_to_json(path)

    loaded = Owner.load_from_json(path)
    task = loaded.get_pet("Mochi").tasks[0]
    assert loaded.name == "Jordan"
    assert [p.name for p in loaded.pets] == ["Mochi", "Luna"]
    assert (task.description, task.due_date, task.completed, task.pet_name) == (
        "Walk", DAY, True, "Mochi"
    )
