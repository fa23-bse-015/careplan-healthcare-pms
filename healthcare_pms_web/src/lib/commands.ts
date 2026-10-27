import type { Client, Transaction } from "@libsql/client";
import { execute, getDb, queryRows } from "@/lib/db";
import { calculateSchedule } from "@/lib/schedule";
import type { Activity, Dependency, Project } from "@/lib/types";

type Command = { type: string; payload: Record<string, unknown> };
type Tx = Transaction;

function text(payload: Record<string, unknown>, key: string, label = key, min = 1) {
  const value = String(payload[key] ?? "").trim();
  if (value.length < min || value.length > 4000) throw new Error(`${label} is required and must be under 4,000 characters.`);
  return value;
}
function number(payload: Record<string, unknown>, key: string, label = key, min = 0, max = Number.MAX_SAFE_INTEGER, integer = false) {
  const value = Number(payload[key]);
  if (!Number.isFinite(value) || value < min || value > max || (integer && !Number.isInteger(value))) throw new Error(`${label} must be ${integer ? "a whole number" : "a number"} between ${min} and ${max}.`);
  return value;
}
function optionalId(payload: Record<string, unknown>, key: string) {
  const value = payload[key];
  return value === null || value === undefined || value === "" ? null : number(payload, key, key, 1, Number.MAX_SAFE_INTEGER, true);
}
function validDate(value: string, label: string) {
  const parsed = /^\d{4}-\d{2}-\d{2}$/.test(value) ? new Date(`${value}T00:00:00.000Z`) : null;
  if (!parsed || Number.isNaN(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== value) throw new Error(`${label} must be a valid YYYY-MM-DD date.`);
  return value;
}
async function nextId(db: Pick<Client, "execute">, table: string) {
  const allowed = new Set(["requirements", "change_requests", "activities", "defects", "risks"]);
  if (!allowed.has(table)) throw new Error("Unsupported record type.");
  const result = await db.execute(`SELECT COALESCE(MAX(id),0)+1 AS next_id FROM ${table}`);
  return Number(result.rows[0]?.next_id ?? 1);
}
async function inTransaction<T>(db: Client, callback: (tx: Tx) => Promise<T>): Promise<T> {
  const tx = await db.transaction("write");
  try {
    const result = await callback(tx);
    await tx.commit();
    return result;
  } catch (error) {
    await tx.rollback();
    throw error;
  }
}

export async function runCommand(command: Command) {
  const db = await getDb();
  const p = command.payload ?? {};
  switch (command.type) {
    case "project.save": {
      const fields = ["name", "objective", "stakeholders", "in_scope", "out_scope", "plan_scope", "plan_schedule", "plan_cost", "plan_quality", "start_date", "status_date", "project_status"] as const;
      const values = fields.map((field) => text(p, field, field.replaceAll("_", " "), field === "name" ? 2 : 0));
      validDate(values[9], "Project start date"); validDate(values[10], "Status date");
      const budget = number(p, "baseline_budget", "Baseline budget", 0, 10_000_000_000);
      const weeks = number(p, "baseline_duration_weeks", "Baseline duration", 1, 520, true);
      await execute(db, `UPDATE project SET ${fields.map((field) => `${field}=?`).join(", ")}, baseline_budget=?, baseline_duration_weeks=? WHERE id=1`, [...values, budget, weeks]);
      return { message: "Project charter and plan saved." };
    }
    case "team.add": {
      await execute(db, "INSERT INTO team_members(name,role) VALUES (?,?)", [text(p, "name", "Team member name", 2), text(p, "role", "Role", 2)]);
      return { message: "Team member added." };
    }
    case "milestone.add": {
      const due = validDate(text(p, "due_date", "Due date"), "Due date");
      const status = text(p, "status");
      if (!["Planned", "Achieved", "At Risk"].includes(status)) throw new Error("Choose a valid milestone status.");
      await execute(db, "INSERT INTO milestones(name,due_date,status) VALUES (?,?,?)", [text(p, "name", "Milestone"), due, status]);
      return { message: "Milestone added." };
    }
    case "milestone.update": {
      const id = number(p, "id", "Milestone", 1, Number.MAX_SAFE_INTEGER, true);
      const status = text(p, "status");
      if (!["Planned", "Achieved", "At Risk"].includes(status)) throw new Error("Choose a valid milestone status.");
      await execute(db, "UPDATE milestones SET status=? WHERE id=?", [status, id]);
      return { message: "Milestone status updated." };
    }
    case "closure.add": {
      const date = validDate(text(p, "recorded_on", "Record date"), "Record date");
      const summary = text(p, "summary", "Closure summary");
      const lessons = text(p, "lessons_learned", "Lessons learned");
      await inTransaction(db, async (tx) => {
        await execute(tx, "INSERT INTO closure_records(recorded_on,summary,lessons_learned) VALUES (?,?,?)", [date, summary, lessons]);
        await execute(tx, "UPDATE project SET closure_record=? WHERE id=1", [summary]);
      });
      return { message: "Closure record saved." };
    }
    case "requirement.add": {
      const id = await nextId(db, "requirements");
      const priority = text(p, "priority");
      if (!["Critical", "High", "Medium", "Low"].includes(priority)) throw new Error("Choose a valid requirement priority.");
      await execute(db, "INSERT INTO requirements(code,description,priority,status) VALUES (?,?,?,'Pending')", [`REQ-${String(id).padStart(2, "0")}`, text(p, "description", "Requirement"), priority]);
      return { message: "Requirement added as Pending." };
    }
    case "requirement.update": {
      const id = number(p, "id", "Requirement", 1, Number.MAX_SAFE_INTEGER, true);
      const priority = text(p, "priority");
      if (!["Critical", "High", "Medium", "Low"].includes(priority)) throw new Error("Choose a valid requirement priority.");
      await execute(db, "UPDATE requirements SET description=?, priority=? WHERE id=?", [text(p, "description", "Requirement"), priority, id]);
      return { message: "Requirement updated." };
    }
    case "requirement.status": {
      const id = number(p, "id", "Requirement", 1, Number.MAX_SAFE_INTEGER, true);
      const status = text(p, "status");
      if (!["Approved", "Rejected"].includes(status)) throw new Error("Choose Approved or Rejected.");
      const result = await execute(db, "UPDATE requirements SET status=? WHERE id=? AND status='Pending' AND source_change_id IS NULL", [status, id]);
      if (!result.rowsAffected) throw new Error("Only a pending stand-alone requirement can be approved or rejected here.");
      return { message: `Requirement ${status.toLowerCase()}.` };
    }
    case "wbs.add": {
      const parentId = optionalId(p, "parent_id");
      const parent = parentId ? (await queryRows<{ id: number; code: string }>(db, "SELECT id,code FROM wbs WHERE id=?", [parentId]))[0] : undefined;
      if (parentId && !parent) throw new Error("Select an existing parent WBS item.");
      const siblings = await queryRows<{ count: number }>(db, "SELECT COUNT(*) AS count FROM wbs WHERE parent_id IS ?", [parentId]);
      const code = parent ? `${parent.code}.${Number(siblings[0].count) + 1}` : `1.${Number(siblings[0].count) + 1}`;
      await execute(db, "INSERT INTO wbs(code,parent_id,name,status) VALUES (?,?,?,'Approved')", [code, parentId, text(p, "name", "Work package")]);
      return { message: `Work package ${code} added.` };
    }
    case "change.propose": {
      const weeks = number(p, "schedule_weeks", "Schedule impact", 1, 520, true);
      const cost = number(p, "cost_impact", "Cost impact", 0, 10_000_000_000);
      const title = text(p, "title", "Change title");
      const justification = text(p, "justification", "Justification");
      const requirement = text(p, "requirement_text", "Proposed requirement");
      const priority = text(p, "priority");
      if (!["Critical", "High", "Medium", "Low"].includes(priority)) throw new Error("Choose a valid requirement priority.");
      const ownerId = optionalId(p, "team_member_id");
      const root = (await queryRows<{ id: number }>(db, "SELECT id FROM wbs WHERE parent_id IS NULL ORDER BY id LIMIT 1"))[0];
      if (!root) throw new Error("Add a root WBS item before proposing a change.");
      const codeId = await inTransaction(db, async (tx) => {
        const codeId = await nextId(tx as unknown as Client, "change_requests");
        await execute(tx, "INSERT INTO change_requests(code,title,justification,cost_impact,schedule_weeks,status) VALUES (?,?,?,?,?,'Pending')", [`CR-${String(codeId).padStart(3, "0")}`, title, justification, cost, weeks]);
        const changeId = Number((await queryRows<{ id: number }>(tx, "SELECT id FROM change_requests WHERE code=?", [`CR-${String(codeId).padStart(3, "0")}`]))[0].id);
        const reqId = await nextId(tx as unknown as Client, "requirements");
        const wbsId = Number((await queryRows<{ id: number }>(tx, "SELECT COALESCE(MAX(id),0)+1 AS id FROM wbs"))[0].id);
        const reqCode = `REQ-${String(reqId).padStart(2, "0")}`;
        const wbsCode = `CR-${String(codeId).padStart(3, "0")}.1`;
        await execute(tx, "INSERT INTO requirements(code,description,priority,status,source_change_id) VALUES (?,?,?,'Pending',?)", [reqCode, requirement, priority, changeId]);
        await execute(tx, "INSERT INTO wbs(code,parent_id,name,status,source_change_id) VALUES (?,?,?,'Pending',?)", [wbsCode, root.id, title, changeId]);
        await execute(tx, "INSERT INTO change_items(change_id,requirement_id,wbs_id,requirement_text,priority,wbs_name,activity_name,activity_days,activity_cost,team_member_id) VALUES (?,?,?,?,?,?,?,?,?,?)", [changeId, reqId, wbsId, requirement, priority, title, text(p, "activity_name", "Activity name"), weeks * 5, cost, ownerId]);
        return codeId;
      });
      return { message: `CR-${String(codeId).padStart(3, "0")} submitted for approval.` };
    }
    case "change.approve": {
      const id = number(p, "id", "Change request", 1, Number.MAX_SAFE_INTEGER, true);
      await inTransaction(db, async (tx) => {
        const change = (await queryRows<{ id: number; code: string; status: string; applied_at: string | null; cost_impact: number; schedule_weeks: number }>(tx, "SELECT * FROM change_requests WHERE id=?", [id]))[0];
        if (!change) throw new Error("Change request was not found.");
        if (change.status !== "Pending" || change.applied_at) throw new Error("This change is not pending; its impact cannot be applied twice.");
        const items = await queryRows<{ id: number; requirement_id: number | null; wbs_id: number | null; activity_name: string; activity_days: number; activity_cost: number; team_member_id: number | null }>(tx, "SELECT * FROM change_items WHERE change_id=? ORDER BY id", [id]);
        if (!items.length) throw new Error("A change request needs at least one linked scope item.");
        const itemCost = items.reduce((sum, item) => sum + Number(item.activity_cost), 0);
        const itemDays = items.reduce((sum, item) => sum + Number(item.activity_days), 0);
        if (Math.abs(itemCost - Number(change.cost_impact)) > 0.01 || itemDays !== Number(change.schedule_weeks) * 5) throw new Error("Linked scope estimates must reconcile to the requested cost and schedule impact.");
        for (const item of items) {
          if (item.requirement_id) await execute(tx, "UPDATE requirements SET status='Approved' WHERE id=? AND source_change_id=?", [item.requirement_id, id]);
          if (item.wbs_id) await execute(tx, "UPDATE wbs SET status='Approved' WHERE id=? AND source_change_id=?", [item.wbs_id, id]);
        }
        const tasks = await queryRows<Activity>(tx, "SELECT * FROM activities ORDER BY id");
        const edges = await queryRows<Dependency>(tx, "SELECT * FROM dependencies");
        const allPredecessors = new Set(edges.map((edge) => Number(edge.predecessor_id)));
        const sinks = tasks.map((task) => Number(task.id)).filter((taskId) => !allPredecessors.has(taskId));
        let previous: number | null = null;
        for (const [index, item] of items.entries()) {
          const result = await execute(tx, "INSERT INTO activities(code,wbs_id,name,team_member_id,duration_days,budget,actual_progress,delay_days,is_milestone,source_change_id,source_item_id) VALUES (?,?,?,?,?,?,0,0,0,?,?)", [`${change.code}-ACT-${String(index + 1).padStart(2, "0")}`, item.wbs_id, item.activity_name, item.team_member_id, item.activity_days, item.activity_cost, id, item.id]);
          const activityId = Number(result.lastInsertRowid);
          const predecessors = previous === null ? sinks : [previous];
          for (const predecessor of predecessors) if (predecessor !== activityId) await execute(tx, "INSERT INTO dependencies(activity_id,predecessor_id) VALUES (?,?)", [activityId, predecessor]);
          previous = activityId;
        }
        await execute(tx, "UPDATE change_requests SET status='Approved', applied_at=datetime('now') WHERE id=? AND status='Pending'", [id]);
      });
      return { message: "Change approved. Its linked requirements, WBS work, activities, budget, and schedule are now reflected." };
    }
    case "change.reject": {
      const id = number(p, "id", "Change request", 1, Number.MAX_SAFE_INTEGER, true);
      await inTransaction(db, async (tx) => {
        const change = (await queryRows<{ status: string; applied_at: string | null }>(tx, "SELECT status,applied_at FROM change_requests WHERE id=?", [id]))[0];
        if (!change) throw new Error("Change request was not found.");
        if (change.status !== "Pending" || change.applied_at) throw new Error("Only a pending, unapplied request can be rejected.");
        await execute(tx, "UPDATE change_requests SET status='Rejected' WHERE id=?", [id]);
        await execute(tx, "UPDATE requirements SET status='Rejected' WHERE source_change_id=? AND status='Pending'", [id]);
        await execute(tx, "UPDATE wbs SET status='Rejected' WHERE source_change_id=? AND status='Pending'", [id]);
      });
      return { message: "Change rejected; approved baseline and scope were not changed." };
    }
    case "activity.add": {
      const name = text(p, "name", "Activity name");
      const days = number(p, "duration_days", "Duration", 1, 5000, true);
      const budget = number(p, "budget", "Budget", 0, 10_000_000_000);
      const ownerId = optionalId(p, "team_member_id"); const wbsId = optionalId(p, "wbs_id");
      const predecessorIds = Array.isArray(p.predecessor_ids) ? p.predecessor_ids.map((id) => Number(id)) : [];
      if (predecessorIds.some((id) => !Number.isInteger(id) || id < 1)) throw new Error("Dependencies must reference valid activities.");
      await inTransaction(db, async (tx) => {
        const existing = await queryRows<Activity>(tx, "SELECT * FROM activities ORDER BY id");
        const dependencies = await queryRows<Dependency>(tx, "SELECT * FROM dependencies");
        const id = Math.max(0, ...existing.map((activity) => Number(activity.id))) + 1;
        const hypothetical = [...existing, { id, duration_days: days, delay_days: 0 } as Activity];
        const proposedEdges = [...dependencies, ...predecessorIds.map((predecessor_id) => ({ activity_id: id, predecessor_id }))];
        const project = (await queryRows<Project>(tx, "SELECT * FROM project WHERE id=1"))[0];
        calculateSchedule(hypothetical, proposedEdges, project.start_date);
        const code = `ACT-${String(id).padStart(2, "0")}`;
        const inserted = await execute(tx, "INSERT INTO activities(code,wbs_id,name,team_member_id,duration_days,budget) VALUES (?,?,?,?,?,?)", [code, wbsId, name, ownerId, days, budget]);
        const actualId = Number(inserted.lastInsertRowid);
        for (const predecessor of predecessorIds) await execute(tx, "INSERT INTO dependencies(activity_id,predecessor_id) VALUES (?,?)", [actualId, predecessor]);
      });
      return { message: "Activity added and dependency graph validated." };
    }
    case "activity.update": {
      const id = number(p, "id", "Activity", 1, Number.MAX_SAFE_INTEGER, true);
      const progress = number(p, "actual_progress", "Progress", 0, 100);
      const delay = number(p, "delay_days", "Delay", 0, 5000, true);
      await execute(db, "UPDATE activities SET actual_progress=?, delay_days=? WHERE id=?", [progress, delay, id]);
      return { message: "Activity progress and delay saved." };
    }
    case "activity.dependencies": {
      const id = number(p, "id", "Activity", 1, Number.MAX_SAFE_INTEGER, true);
      const predecessorIds = Array.isArray(p.predecessor_ids) ? [...new Set(p.predecessor_ids.map((value) => Number(value)))] : [];
      if (predecessorIds.some((value) => !Number.isInteger(value) || value < 1)) throw new Error("Dependencies must reference valid activities.");
      const activities = await queryRows<Activity>(db, "SELECT * FROM activities ORDER BY id");
      const current = await queryRows<Dependency>(db, "SELECT * FROM dependencies WHERE activity_id<>?", [id]);
      const projected = [...current, ...predecessorIds.map((predecessor_id) => ({ activity_id: id, predecessor_id }))];
      const project = (await queryRows<Project>(db, "SELECT * FROM project WHERE id=1"))[0];
      calculateSchedule(activities, projected, project.start_date);
      await inTransaction(db, async (tx) => {
        await execute(tx, "DELETE FROM dependencies WHERE activity_id=?", [id]);
        for (const predecessor of predecessorIds) await execute(tx, "INSERT INTO dependencies(activity_id,predecessor_id) VALUES (?,?)", [id, predecessor]);
      });
      return { message: "Dependencies updated; no self-link or schedule cycle was found." };
    }
    case "expenditure.add": {
      const activityId = number(p, "activity_id", "Activity", 1, Number.MAX_SAFE_INTEGER, true);
      const amount = number(p, "amount", "Amount", 0, 10_000_000_000);
      const date = validDate(text(p, "spent_on", "Expense date"), "Expense date");
      await execute(db, "INSERT INTO expenditures(activity_id,amount,spent_on,description) VALUES (?,?,?,?)", [activityId, amount, date, text(p, "description", "Expense description")]);
      return { message: "Expenditure recorded." };
    }
    case "defect.add": {
      const id = await nextId(db, "defects"); const severity = text(p, "severity");
      if (!["Critical", "High", "Medium", "Low"].includes(severity)) throw new Error("Choose a valid defect severity.");
      const assigneeId = optionalId(p, "assignee_id");
      await execute(db, "INSERT INTO defects(code,description,severity,assignee_id,status,opened_on) VALUES (?,?,?,?,'Open',?)", [`DEF-${String(id).padStart(3, "0")}`, text(p, "description", "Defect description"), severity, assigneeId, validDate(text(p, "opened_on", "Opened date"), "Opened date")]);
      return { message: "Defect added." };
    }
    case "defect.status": {
      const id = number(p, "id", "Defect", 1, Number.MAX_SAFE_INTEGER, true); const status = text(p, "status");
      if (!["Open", "In Progress", "Resolved"].includes(status)) throw new Error("Choose a valid defect status.");
      await execute(db, "UPDATE defects SET status=? WHERE id=?", [status, id]);
      return { message: "Defect status updated." };
    }
    case "quality.add": {
      const outcome = text(p, "outcome");
      if (!["Not Run", "Pass", "Fail"].includes(outcome)) throw new Error("Choose a valid inspection outcome.");
      await execute(db, "INSERT INTO quality_checks(item,deliverable,outcome,inspected_on,notes) VALUES (?,?,?,?,?)", [text(p, "item", "Check name"), text(p, "deliverable", "Deliverable"), outcome, validDate(text(p, "inspected_on", "Inspection date"), "Inspection date"), String(p.notes ?? "").trim()]);
      return { message: "Quality inspection recorded." };
    }
    case "risk.add": {
      const id = await nextId(db, "risks"); const likelihood = number(p, "likelihood", "Likelihood", 1, 5, true); const impact = number(p, "impact", "Impact", 1, 5, true);
      await execute(db, "INSERT INTO risks(code,description,likelihood,impact,response,owner_id,status) VALUES (?,?,?,?,?,?,'Open')", [`RSK-${String(id).padStart(2, "0")}`, text(p, "description", "Risk description"), likelihood, impact, text(p, "response", "Response"), optionalId(p, "owner_id")]);
      return { message: "Risk added." };
    }
    case "risk.status": {
      const id = number(p, "id", "Risk", 1, Number.MAX_SAFE_INTEGER, true); const status = text(p, "status");
      if (!["Open", "Monitoring", "Closed"].includes(status)) throw new Error("Choose a valid risk status.");
      await execute(db, "UPDATE risks SET status=? WHERE id=?", [status, id]);
      return { message: "Risk status updated." };
    }
    default: throw new Error("Unknown action. Refresh the page and try again.");
  }
}
