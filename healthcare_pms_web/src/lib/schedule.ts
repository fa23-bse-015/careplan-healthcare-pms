import type { Activity, Dependency, Evm, EvmDetail, ScheduleDates } from "@/lib/types";

const dateOnly = (value: string) => new Date(`${value.slice(0, 10)}T00:00:00.000Z`);
const iso = (value: Date) => value.toISOString().slice(0, 10);
const isWorkday = (value: Date) => value.getUTCDay() !== 0 && value.getUTCDay() !== 6;

function firstWorkday(value: Date) {
  const next = new Date(value);
  while (!isWorkday(next)) next.setUTCDate(next.getUTCDate() + 1);
  return next;
}

export function addWorkdays(start: Date, days: number) {
  if (days < 1) throw new Error("Duration must be at least one working day.");
  const current = new Date(start);
  while (!isWorkday(current)) current.setUTCDate(current.getUTCDate() + 1);
  let remaining = days;
  while (remaining > 1) {
    current.setUTCDate(current.getUTCDate() + 1);
    if (isWorkday(current)) remaining -= 1;
  }
  return current;
}

function nextWorkday(value: Date) {
  const next = new Date(value);
  next.setUTCDate(next.getUTCDate() + 1);
  while (!isWorkday(next)) next.setUTCDate(next.getUTCDate() + 1);
  return next;
}

function workdaysBetween(start: Date, end: Date) {
  if (end <= start) return 0;
  const current = new Date(start);
  let count = 0;
  while (current < end) {
    if (isWorkday(current)) count += 1;
    current.setUTCDate(current.getUTCDate() + 1);
  }
  return count;
}

export function calculateSchedule(activities: Activity[], dependencies: Dependency[], startDate: string, delays = true) {
  const byId = new Map(activities.map((activity) => [Number(activity.id), activity]));
  const incoming = new Map<number, Set<number>>();
  const outgoing = new Map<number, Set<number>>();
  for (const id of byId.keys()) incoming.set(id, new Set());
  for (const { activity_id, predecessor_id } of dependencies) {
    const successor = Number(activity_id); const predecessor = Number(predecessor_id);
    if (successor === predecessor) throw new Error("An activity cannot depend on itself.");
    if (!byId.has(successor) || !byId.has(predecessor)) throw new Error("Every dependency must reference an existing activity.");
    incoming.get(successor)!.add(predecessor);
    if (!outgoing.has(predecessor)) outgoing.set(predecessor, new Set());
    outgoing.get(predecessor)!.add(successor);
  }
  const queue = [...byId.keys()].filter((id) => incoming.get(id)!.size === 0).sort((a, b) => a - b);
  const order: number[] = [];
  const indegree = new Map([...incoming].map(([id, preds]) => [id, preds.size]));
  while (queue.length) {
    const node = queue.shift()!;
    order.push(node);
    for (const successor of [...(outgoing.get(node) ?? [])].sort((a, b) => a - b)) {
      indegree.set(successor, indegree.get(successor)! - 1);
      if (indegree.get(successor) === 0) queue.push(successor);
    }
  }
  if (order.length !== byId.size) throw new Error("Circular dependency detected. Remove a dependency to continue.");

  const start = firstWorkday(dateOnly(startDate));
  const result: Record<number, ScheduleDates> = {};
  for (const id of order) {
    const activity = byId.get(id)!;
    const duration = Number(activity.duration_days);
    if (!Number.isInteger(duration) || duration < 1) throw new Error("Duration must be at least one working day.");
    const predecessors = [...incoming.get(id)!].sort((a, b) => a - b);
    const plannedStart = predecessors.length ? nextWorkday(dateOnly(predecessors.map((pred) => result[pred].planned_finish).sort().at(-1)!)) : start;
    const forecastStart = predecessors.length ? nextWorkday(dateOnly(predecessors.map((pred) => result[pred].forecast_finish).sort().at(-1)!)) : start;
    result[id] = {
      planned_start: iso(plannedStart),
      planned_finish: iso(addWorkdays(plannedStart, duration)),
      forecast_start: iso(forecastStart),
      forecast_finish: iso(addWorkdays(forecastStart, duration + (delays ? Number(activity.delay_days || 0) : 0))),
      predecessors,
    };
  }
  return result;
}

export function plannedProgress(start: string, finish: string, status: string) {
  const startDate = dateOnly(start); const finishDate = dateOnly(finish); const statusDate = dateOnly(status);
  const inclusiveFinish = new Date(finishDate); inclusiveFinish.setUTCDate(inclusiveFinish.getUTCDate() + 1);
  if (statusDate < startDate) return 0;
  if (statusDate >= finishDate) return 100;
  const inclusiveStatus = new Date(statusDate); inclusiveStatus.setUTCDate(inclusiveStatus.getUTCDate() + 1);
  const total = workdaysBetween(startDate, inclusiveFinish);
  return total ? Math.min(100, Math.max(0, (workdaysBetween(startDate, inclusiveStatus) / total) * 100)) : 0;
}

export function calculateEvm(activities: Activity[], expenditures: { activity_id: number; amount: number; spent_on: string }[], schedule: Record<number, ScheduleDates>, statusDate: string, approvedBudget: number): Evm {
  const actualByActivity = new Map<number, number>();
  for (const expense of expenditures) {
    if (expense.spent_on <= statusDate) actualByActivity.set(expense.activity_id, (actualByActivity.get(expense.activity_id) ?? 0) + Number(expense.amount));
  }
  let pv = 0; let ev = 0; let ac = 0;
  const detail: EvmDetail[] = activities.map((activity) => {
    const planned_pct = plannedProgress(schedule[activity.id].planned_start, schedule[activity.id].planned_finish, statusDate);
    const taskPv = Number(activity.budget) * planned_pct / 100;
    const taskEv = Number(activity.budget) * Number(activity.actual_progress) / 100;
    const taskAc = actualByActivity.get(activity.id) ?? 0;
    pv += taskPv; ev += taskEv; ac += taskAc;
    return { activity_id: activity.id, pv: taskPv, ev: taskEv, ac: taskAc, planned_pct };
  });
  const cpi = ac ? ev / ac : null; const spi = pv ? ev / pv : null;
  const warnings: string[] = [];
  if (cpi !== null && cpi < 0.95) warnings.push(`Cost performance warning: CPI ${cpi.toFixed(2)} is below 0.95.`);
  if (spi !== null && spi < 0.95) warnings.push(`Schedule performance warning: SPI ${spi.toFixed(2)} is below 0.95.`);
  if (ev > 0 && ac > ev * 1.1) warnings.push("Actual expenditure is more than 10% above earned value.");
  if (ac > approvedBudget) warnings.push("Actual expenditure exceeds the currently approved budget.");
  return { pv, ev, ac, cpi, spi, cv: ev - ac, sv: ev - pv, detail, warnings };
}
