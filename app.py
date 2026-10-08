from datetime import date, time
from pathlib import Path

import streamlit as st

from pawpal_system import Owner, Pet, Scheduler, Task

DATA_FILE = Path("data.json")
PRIORITY_ICON = {"high": "🔴 high", "medium": "🟡 medium", "low": "🟢 low"}

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")


def save() -> None:
    """Persist the current owner so data survives app restarts."""
    st.session_state.owner.save_to_json(DATA_FILE)


def task_rows(tasks: list[Task]) -> list[dict]:
    """Turn Task objects into rows for st.dataframe."""
    return [
        {
            "Time": t.time,
            "Pet": t.pet_name,
            "Task": t.description,
            "Minutes": t.duration_minutes,
            "Priority": PRIORITY_ICON[t.priority],
            "Repeats": t.frequency,
            "Status": "✅ done" if t.completed else "⏳ todo",
        }
        for t in tasks
    ]


# --- session "memory": create the Owner once, then reuse it on every rerun ---
if "owner" not in st.session_state:
    st.session_state.owner = (
        Owner.load_from_json(DATA_FILE) if DATA_FILE.exists() else Owner("Jordan")
    )
owner: Owner = st.session_state.owner
scheduler = Scheduler(owner)

st.title("🐾 PawPal+")
st.caption("Plan, sort, and track your pets' care tasks.")

# --- owner settings ---
with st.sidebar:
    st.header("Owner")
    new_name = st.text_input("Owner name", value=owner.name)
    new_budget = st.number_input(
        "Minutes available for pet care today", min_value=0, max_value=1440,
        value=owner.available_minutes, step=5,
    )
    if new_name != owner.name or new_budget != owner.available_minutes:
        owner.name, owner.available_minutes = new_name, int(new_budget)
        save()
    st.caption(f"Data is saved automatically to `{DATA_FILE}`.")
    if st.button("Reset all data"):
        st.session_state.owner = Owner("Jordan")
        DATA_FILE.unlink(missing_ok=True)
        st.rerun()

# --- add a pet ---
st.subheader("1. Your pets")
with st.form("add_pet", clear_on_submit=True):
    c1, c2, c3 = st.columns([2, 1, 1])
    pet_name = c1.text_input("Pet name")
    species = c2.selectbox("Species", ["dog", "cat", "bird", "other"])
    age = c3.number_input("Age", min_value=0, max_value=40, value=1)
    if st.form_submit_button("Add pet"):
        if not pet_name.strip():
            st.error("Please enter a pet name.")
        else:
            try:
                owner.add_pet(Pet(pet_name.strip(), species, int(age)))
                save()
                st.success(f"Added {pet_name.strip()}!")
            except ValueError as err:
                st.error(str(err))

if owner.pets:
    st.write(" · ".join(f"**{p.name}** ({p.species}, {p.task_count()} tasks)" for p in owner.pets))
else:
    st.info("No pets yet. Add one above to get started.")
    st.stop()

# --- schedule a task ---
st.subheader("2. Schedule a task")
with st.form("add_task", clear_on_submit=True):
    c1, c2 = st.columns(2)
    task_pet = c1.selectbox("Pet", [p.name for p in owner.pets])
    description = c2.text_input("Task", placeholder="Morning walk")
    c3, c4, c5 = st.columns(3)
    task_date = c3.date_input("Date", value=date.today())
    task_time = c4.time_input("Time", value=time(8, 0), step=300)
    duration = c5.number_input("Duration (min)", min_value=1, max_value=600, value=20)
    c6, c7 = st.columns(2)
    priority = c6.selectbox("Priority", ["high", "medium", "low"], index=1)
    frequency = c7.selectbox("Repeats", ["once", "daily", "weekly"])
    if st.form_submit_button("Add task"):
        if not description.strip():
            st.error("Please describe the task.")
        else:
            owner.get_pet(task_pet).add_task(Task(
                description.strip(), task_time.strftime("%H:%M"), int(duration),
                priority, frequency, task_date,
            ))
            save()
            st.success(f"Scheduled '{description.strip()}' for {task_pet}.")

# --- view the schedule ---
st.subheader("3. Schedule")
c1, c2, c3, c4 = st.columns(4)
view_date = c1.date_input("Day", value=date.today(), key="view_date")
pet_filter = c2.selectbox("Pet", ["All pets"] + [p.name for p in owner.pets])
status_filter = c3.selectbox("Status", ["All", "To do", "Done"])
sort_mode = c4.selectbox("Sort by", ["Time", "Priority"])

tasks = scheduler.todays_schedule(view_date)
tasks = scheduler.filter_tasks(
    tasks,
    pet_name=None if pet_filter == "All pets" else pet_filter,
    completed={"All": None, "To do": False, "Done": True}[status_filter],
)
if sort_mode == "Priority":
    tasks = scheduler.sort_by_priority(tasks)

conflicts = scheduler.detect_conflicts(scheduler.todays_schedule(view_date))
if conflicts:
    st.warning(
        f"**{len(conflicts)} scheduling conflict(s)** — you can't be in two places at once. "
        "Consider moving one of these tasks:\n\n" + "\n".join(f"- {c}" for c in conflicts)
    )

if tasks:
    st.dataframe(task_rows(tasks), hide_index=True, width="stretch")
    pending = [t for t in tasks if not t.completed]
    if pending:
        c1, c2 = st.columns([3, 1])
        labels = {f"{t.time} · {t.pet_name} · {t.description}": t for t in pending}
        choice = c1.selectbox("Mark a task complete", list(labels), label_visibility="collapsed")
        if c2.button("Mark done ✅"):
            next_task = scheduler.mark_task_complete(labels[choice])
            save()
            msg = f"Completed '{labels[choice].description}'."
            if next_task:
                msg += f" Next {next_task.frequency} occurrence added for {next_task.due_date}."
            st.session_state.flash = msg
            st.rerun()
else:
    st.info("No tasks match these filters for this day.")

if msg := st.session_state.pop("flash", None):
    st.success(msg)

# --- smart planning ---
st.subheader("4. Smart planning")
tab_plan, tab_slot = st.tabs(["Daily plan", "Find a free slot"])

with tab_plan:
    planned, skipped = scheduler.build_daily_plan(view_date)
    used = sum(t.duration_minutes for t in planned)
    st.caption(
        f"Picks the highest-priority to-do tasks that fit in your "
        f"{owner.available_minutes}-minute budget ({used} min used)."
    )
    if planned:
        st.dataframe(task_rows(planned), hide_index=True, width="stretch")
    else:
        st.info("Nothing left to plan for this day.")
    for task, reason in skipped:
        st.warning(f"Skipped **{task.description}** ({task.pet_name}): {reason}.")

with tab_slot:
    c1, c2, c3 = st.columns(3)
    need = c1.number_input("Minutes needed", min_value=5, max_value=600, value=30, step=5)
    start = c2.time_input("Earliest", value=time(7, 0), step=900)
    end = c3.time_input("Latest end", value=time(21, 0), step=900)
    slot = scheduler.find_next_available_slot(
        int(need), view_date, start.strftime("%H:%M"), end.strftime("%H:%M")
    )
    if slot:
        st.success(f"Earliest free {need}-minute slot on {view_date}: **{slot}**")
    else:
        st.error("No free slot that long in that window.")
