"""Dependency-aware project schedule calculations using Monday-Friday workdays."""
from __future__ import annotations

from collections import defaultdict, deque
from datetime import date, datetime, timedelta


def parse_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError) as exc:
        raise ValueError("Dates must use YYYY-MM-DD and be real calendar dates.") from exc


def add_workdays(start: date, days: int) -> date:
    """Return the inclusive finish date for `days` Monday-Friday workdays."""
    if days < 1:
        raise ValueError("Duration must be at least one working day.")
    current = start
    remaining = days
    while current.weekday() >= 5:
        current += timedelta(days=1)
    while remaining > 1:
        current += timedelta(days=1)
        if current.weekday() < 5:
            remaining -= 1
    return current


def next_workday(day: date) -> date:
    candidate = day + timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)
    return candidate


def workdays_between(start: date, end: date) -> int:
    """Count workdays in [start, end), used to measure elapsed planned effort."""
    if end <= start:
        return 0
    count = 0
    current = start
    while current < end:
        if current.weekday() < 5:
            count += 1
        current += timedelta(days=1)
    return count


def calculate_schedule(activities, dependencies, project_start: str, delays=True):
    """Topologically schedule activities, rejecting missing, self, or circular links.

    Each activity is a dict with id, duration_days, and optional delay_days. An
    activity without predecessors may start at the project start. A delayed
    activity consumes its own added working days; successors move only when
    their dependency path requires it. Unrelated work keeps its own dates.
    """
    start = parse_date(project_start)
    by_id = {int(a["id"]): a for a in activities}
    incoming = {key: set() for key in by_id}
    outgoing = defaultdict(set)
    for activity_id, predecessor_id in dependencies:
        activity_id, predecessor_id = int(activity_id), int(predecessor_id)
        if activity_id == predecessor_id:
            raise ValueError("An activity cannot depend on itself.")
        if activity_id not in by_id or predecessor_id not in by_id:
            raise ValueError("Every dependency must reference an existing activity.")
        incoming[activity_id].add(predecessor_id)
        outgoing[predecessor_id].add(activity_id)
    queue = deque(sorted(k for k, preds in incoming.items() if not preds))
    order = []
    remaining_in = {k: len(v) for k, v in incoming.items()}
    while queue:
        node = queue.popleft()
        order.append(node)
        for successor in sorted(outgoing[node]):
            remaining_in[successor] -= 1
            if remaining_in[successor] == 0:
                queue.append(successor)
    if len(order) != len(by_id):
        raise ValueError("Circular dependency detected. Remove a dependency to continue.")

    result = {}
    for key in order:
        item = by_id[key]
        duration = int(item["duration_days"])
        if duration < 1:
            raise ValueError("Duration must be at least one working day.")
        forecast_duration = duration + (int(item.get("delay_days", 0)) if delays else 0)
        if forecast_duration < 1:
            raise ValueError("Forecast duration must be positive.")
        planned_predecessors = [result[p]["planned_finish"] for p in incoming[key]]
        forecast_predecessors = [result[p]["forecast_finish"] for p in incoming[key]]
        planned_start = next_workday(max(planned_predecessors)) if planned_predecessors else start
        forecast_start = next_workday(max(forecast_predecessors)) if forecast_predecessors else start
        planned_finish = add_workdays(planned_start, duration)
        forecast_finish = add_workdays(forecast_start, forecast_duration)
        result[key] = {
            "planned_start": planned_start,
            "planned_finish": planned_finish,
            "forecast_start": forecast_start,
            "forecast_finish": forecast_finish,
            "predecessors": sorted(incoming[key]),
        }
    return result


def planned_progress(start_date: date, finish_date: date, status_date: date) -> float:
    """Linear budget-weighted progress across scheduled workdays, inclusive finish."""
    total = workdays_between(start_date, finish_date + timedelta(days=1))
    if status_date < start_date:
        return 0.0
    if status_date >= finish_date:
        return 100.0
    elapsed = workdays_between(start_date, status_date + timedelta(days=1))
    return min(100.0, max(0.0, elapsed / total * 100.0))
