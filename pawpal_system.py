"""PawPal+ logic layer: Owner, Pet, Task, and Scheduler classes."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}
FREQUENCY_STEP = {"daily": timedelta(days=1), "weekly": timedelta(weeks=1)}


def to_minutes(hhmm: str) -> int:
    """Convert an "HH:MM" string into minutes after midnight."""
    hours, minutes = hhmm.split(":")
    return int(hours) * 60 + int(minutes)


def to_hhmm(minutes: int) -> str:
    """Convert minutes after midnight back into an "HH:MM" string."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


@dataclass
class Task:
    """A single pet care activity scheduled at a specific time."""

    description: str
    time: str  # "HH:MM", 24-hour clock
    duration_minutes: int = 15
    priority: str = "medium"  # low | medium | high
    frequency: str = "once"  # once | daily | weekly
    due_date: date = field(default_factory=date.today)
    completed: bool = False
    pet_name: str = ""  # set by Pet.add_task

    def __post_init__(self) -> None:
        """Validate the time, priority, and frequency fields."""
        datetime.strptime(self.time, "%H:%M")  # raises ValueError if malformed
        if self.priority not in PRIORITY_RANK:
            raise ValueError(f"priority must be one of {list(PRIORITY_RANK)}")
        if self.frequency not in ("once", *FREQUENCY_STEP):
            raise ValueError("frequency must be 'once', 'daily', or 'weekly'")

    @property
    def end_minutes(self) -> int:
        """Minutes after midnight when the task finishes."""
        return to_minutes(self.time) + self.duration_minutes

    def mark_complete(self) -> None:
        """Mark this task as done."""
        self.completed = True

    def next_occurrence(self) -> Task | None:
        """Return a fresh copy due on the next date for recurring tasks, else None."""
        step = FREQUENCY_STEP.get(self.frequency)
        if step is None:
            return None
        return Task(
            description=self.description,
            time=self.time,
            duration_minutes=self.duration_minutes,
            priority=self.priority,
            frequency=self.frequency,
            due_date=self.due_date + step,
            pet_name=self.pet_name,
        )

    def to_dict(self) -> dict:
        """Serialize the task to a JSON-friendly dict."""
        return {
            "description": self.description,
            "time": self.time,
            "duration_minutes": self.duration_minutes,
            "priority": self.priority,
            "frequency": self.frequency,
            "due_date": self.due_date.isoformat(),
            "completed": self.completed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Task:
        """Rebuild a task from a dict produced by to_dict()."""
        data = dict(data)
        data["due_date"] = date.fromisoformat(data["due_date"])
        return cls(**data)


@dataclass
class Pet:
    """A pet and the care tasks that belong to it."""

    name: str
    species: str
    age: int = 0
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Attach a task to this pet and tag it with the pet's name."""
        task.pet_name = self.name
        self.tasks.append(task)

    def remove_task(self, task: Task) -> None:
        """Remove a task from this pet."""
        self.tasks.remove(task)

    def task_count(self) -> int:
        """Return how many tasks this pet has."""
        return len(self.tasks)

    def to_dict(self) -> dict:
        """Serialize the pet and its tasks to a JSON-friendly dict."""
        return {
            "name": self.name,
            "species": self.species,
            "age": self.age,
            "tasks": [t.to_dict() for t in self.tasks],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Pet:
        """Rebuild a pet (and its tasks) from a dict produced by to_dict()."""
        pet = cls(name=data["name"], species=data["species"], age=data.get("age", 0))
        for task_data in data.get("tasks", []):
            pet.add_task(Task.from_dict(task_data))
        return pet


class Owner:
    """A pet owner who manages one or more pets."""

    def __init__(self, name: str, available_minutes: int = 120):
        """Create an owner with a daily time budget for pet care."""
        self.name = name
        self.available_minutes = available_minutes
        self.pets: list[Pet] = []

    def add_pet(self, pet: Pet) -> None:
        """Add a pet; pet names must be unique for this owner."""
        if self.get_pet(pet.name) is not None:
            raise ValueError(f"{self.name} already has a pet named {pet.name}")
        self.pets.append(pet)

    def get_pet(self, name: str) -> Pet | None:
        """Look up a pet by name (case-insensitive)."""
        for pet in self.pets:
            if pet.name.lower() == name.lower():
                return pet
        return None

    def remove_pet(self, name: str) -> None:
        """Remove a pet by name if it exists."""
        self.pets = [p for p in self.pets if p.name.lower() != name.lower()]

    def get_all_tasks(self) -> list[Task]:
        """Return every task across all of this owner's pets."""
        return [task for pet in self.pets for task in pet.tasks]

    def save_to_json(self, path: str | Path = "data.json") -> None:
        """Write the owner, pets, and tasks to a JSON file."""
        data = {
            "name": self.name,
            "available_minutes": self.available_minutes,
            "pets": [p.to_dict() for p in self.pets],
        }
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load_from_json(cls, path: str | Path = "data.json") -> Owner:
        """Load an owner from a JSON file written by save_to_json()."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        owner = cls(data["name"], data.get("available_minutes", 120))
        for pet_data in data.get("pets", []):
            owner.add_pet(Pet.from_dict(pet_data))
        return owner


class Scheduler:
    """The scheduling "brain": retrieves, organizes, and manages tasks across pets."""

    def __init__(self, owner: Owner):
        """Create a scheduler that reads pets and tasks from the given owner."""
        self.owner = owner

    # --- retrieval -------------------------------------------------------

    def get_all_tasks(self) -> list[Task]:
        """Return every task the owner's pets have."""
        return self.owner.get_all_tasks()

    def todays_schedule(self, day: date | None = None) -> list[Task]:
        """Return tasks due on the given day (default today), sorted by time."""
        day = day or date.today()
        return self.sort_by_time([t for t in self.get_all_tasks() if t.due_date == day])

    # --- sorting & filtering --------------------------------------------

    def sort_by_time(self, tasks: list[Task]) -> list[Task]:
        """Return tasks in chronological order by their "HH:MM" start time."""
        return sorted(tasks, key=lambda t: to_minutes(t.time))

    def sort_by_priority(self, tasks: list[Task]) -> list[Task]:
        """Return tasks ordered high -> low priority, breaking ties by start time."""
        return sorted(tasks, key=lambda t: (PRIORITY_RANK[t.priority], to_minutes(t.time)))

    def filter_tasks(
        self,
        tasks: list[Task] | None = None,
        pet_name: str | None = None,
        completed: bool | None = None,
    ) -> list[Task]:
        """Filter tasks by pet name and/or completion status; None means "any"."""
        tasks = self.get_all_tasks() if tasks is None else tasks
        result = []
        for task in tasks:
            if pet_name is not None and task.pet_name.lower() != pet_name.lower():
                continue
            if completed is not None and task.completed != completed:
                continue
            result.append(task)
        return result

    # --- recurrence -----------------------------------------------------

    def mark_task_complete(self, task: Task) -> Task | None:
        """Complete a task; for daily/weekly tasks, add and return the next occurrence."""
        if task.completed:
            return None  # already done; don't spawn a duplicate next occurrence
        task.mark_complete()
        next_task = task.next_occurrence()
        if next_task is not None:
            pet = self.owner.get_pet(task.pet_name)
            if pet is None:
                raise ValueError(f"No pet named {task.pet_name!r} to hold the next occurrence")
            pet.add_task(next_task)
        return next_task

    # --- conflicts ------------------------------------------------------

    def detect_conflicts(self, tasks: list[Task] | None = None) -> list[str]:
        """Return warning messages for tasks on the same day whose time windows overlap.

        Never raises: an empty list means no conflicts. Tasks are sorted by start time,
        so each task only needs to be compared with later tasks that start before it ends.
        """
        tasks = self.get_all_tasks() if tasks is None else tasks
        warnings = []
        by_day: dict[date, list[Task]] = {}
        for task in tasks:
            if not task.completed:
                by_day.setdefault(task.due_date, []).append(task)

        for day in sorted(by_day):
            ordered = self.sort_by_time(by_day[day])
            for i, first in enumerate(ordered):
                for second in ordered[i + 1:]:
                    if to_minutes(second.time) >= first.end_minutes:
                        break  # sorted, so nothing later can overlap `first`
                    who = (
                        f"both for {first.pet_name}"
                        if first.pet_name == second.pet_name
                        else f"{first.pet_name} and {second.pet_name}"
                    )
                    warnings.append(
                        f"Conflict on {day}: '{first.description}' ({first.time}, "
                        f"{first.duration_minutes} min) overlaps '{second.description}' "
                        f"({second.time}) - {who}"
                    )
        return warnings

    # --- planning -------------------------------------------------------

    def find_next_available_slot(
        self,
        duration_minutes: int,
        day: date | None = None,
        day_start: str = "07:00",
        day_end: str = "21:00",
    ) -> str | None:
        """Return the earliest "HH:MM" start where a task of this length fits without overlap."""
        day = day or date.today()
        busy = [t for t in self.todays_schedule(day) if not t.completed]
        candidate = to_minutes(day_start)
        for task in busy:  # already sorted by start time
            if to_minutes(task.time) - candidate >= duration_minutes:
                break
            candidate = max(candidate, task.end_minutes)
        if candidate + duration_minutes > to_minutes(day_end):
            return None
        return to_hhmm(candidate)

    def build_daily_plan(self, day: date | None = None) -> tuple[list[Task], list[tuple[Task, str]]]:
        """Pick today's pending tasks by priority until the owner's time budget runs out.

        Returns (planned tasks sorted by time, [(skipped task, reason), ...]).
        """
        day = day or date.today()
        pending = self.filter_tasks(self.todays_schedule(day), completed=False)
        remaining = self.owner.available_minutes
        planned, skipped = [], []
        for task in self.sort_by_priority(pending):
            if task.duration_minutes <= remaining:
                planned.append(task)
                remaining -= task.duration_minutes
            else:
                skipped.append(
                    (task, f"needs {task.duration_minutes} min, only {remaining} min left")
                )
        return self.sort_by_time(planned), skipped

    def explain_plan(self, day: date | None = None) -> list[str]:
        """Return human-readable lines explaining why each task was planned or skipped."""
        planned, skipped = self.build_daily_plan(day)
        lines = [
            f"{t.time} {t.description} ({t.pet_name}) - included: {t.priority} priority, "
            f"{t.duration_minutes} min"
            for t in planned
        ]
        lines += [f"SKIPPED {t.description} ({t.pet_name}) - {reason}" for t, reason in skipped]
        return lines
