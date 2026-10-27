"""Task-level Earned Value calculations with explicit zero-denominator handling."""
from __future__ import annotations

from datetime import datetime
from scheduling import planned_progress


def calculate_evm(activities, expenditures, schedule, status_date: str):
    try:
        status = datetime.strptime(status_date, "%Y-%m-%d").date()
    except (TypeError, ValueError) as exc:
        raise ValueError("Status date must use YYYY-MM-DD.") from exc
    expense_by_task = {}
    for row in expenditures:
        amount = float(row["amount"])
        if amount < 0:
            raise ValueError("Actual expenditure cannot be negative.")
        if row["spent_on"] <= status_date:
            key = int(row["activity_id"])
            expense_by_task[key] = expense_by_task.get(key, 0.0) + amount
    pv = ev = ac = 0.0
    detail = []
    for task in activities:
        task_id = int(task["id"])
        budget = float(task["budget"])
        progress = float(task["actual_progress"])
        if budget < 0:
            raise ValueError("Activity cost cannot be negative.")
        if not 0 <= progress <= 100:
            raise ValueError("Completion percentage must be between 0 and 100.")
        dates = schedule[task_id]
        planned_pct = planned_progress(dates["planned_start"], dates["planned_finish"], status)
        task_pv = budget * planned_pct / 100.0
        task_ev = budget * progress / 100.0
        task_ac = expense_by_task.get(task_id, 0.0)
        pv += task_pv
        ev += task_ev
        ac += task_ac
        detail.append({"activity_id": task_id, "pv": task_pv, "ev": task_ev, "ac": task_ac, "planned_pct": planned_pct})
    return {
        "pv": pv,
        "ev": ev,
        "ac": ac,
        "cpi": ev / ac if ac else None,
        "spi": ev / pv if pv else None,
        "cv": ev - ac,
        "sv": ev - pv,
        "detail": detail,
    }


def performance_warnings(metrics, revised_budget, warn_threshold=0.95, cost_variance_threshold=0.10):
    warnings = []
    if metrics["cpi"] is not None and metrics["cpi"] < warn_threshold:
        warnings.append(f"Cost performance warning: CPI {metrics['cpi']:.2f} is below {warn_threshold:.2f}.")
    if metrics["spi"] is not None and metrics["spi"] < warn_threshold:
        warnings.append(f"Schedule performance warning: SPI {metrics['spi']:.2f} is below {warn_threshold:.2f}.")
    if metrics["ev"] > 0 and metrics["ac"] > metrics["ev"] * (1 + cost_variance_threshold):
        warnings.append("Actual expenditure is more than 10% above earned value.")
    if metrics["ac"] > revised_budget:
        warnings.append("Actual expenditure exceeds the currently approved budget.")
    return warnings
