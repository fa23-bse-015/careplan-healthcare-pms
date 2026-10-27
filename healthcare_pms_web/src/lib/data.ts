import { getDb, queryRows } from "@/lib/db";
import { calculateEvm, calculateSchedule } from "@/lib/schedule";
import type { Activity, ChangeItem, ChangeRequest, ClosureRecord, Defect, Dependency, Expenditure, Milestone, Project, QualityCheck, Requirement, Risk, TeamMember, WbsItem } from "@/lib/types";

export async function getSnapshot() {
  const db = await getDb();
  const [projects, team, requirements, wbs, changes, changeItems, activities, dependencies, expenditures, defects, qualityChecks, risks, milestones, closures] = await Promise.all([
    queryRows<Project>(db, "SELECT * FROM project WHERE id=1"),
    queryRows<TeamMember>(db, "SELECT * FROM team_members ORDER BY id"),
    queryRows<Requirement>(db, "SELECT * FROM requirements ORDER BY id"),
    queryRows<WbsItem>(db, "SELECT * FROM wbs ORDER BY id"),
    queryRows<ChangeRequest>(db, "SELECT * FROM change_requests ORDER BY id DESC"),
    queryRows<ChangeItem>(db, "SELECT * FROM change_items ORDER BY id"),
    queryRows<Activity>(db, "SELECT a.*, t.name AS assignee, w.code AS wbs_code FROM activities a LEFT JOIN team_members t ON t.id=a.team_member_id LEFT JOIN wbs w ON w.id=a.wbs_id ORDER BY a.id"),
    queryRows<Dependency>(db, "SELECT * FROM dependencies ORDER BY activity_id, predecessor_id"),
    queryRows<Expenditure>(db, "SELECT e.*, a.code AS activity_code, a.name AS activity_name FROM expenditures e JOIN activities a ON a.id=e.activity_id ORDER BY e.spent_on DESC, e.id DESC"),
    queryRows<Defect>(db, "SELECT d.*, t.name AS assignee FROM defects d LEFT JOIN team_members t ON t.id=d.assignee_id ORDER BY CASE d.severity WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 ELSE 4 END, d.id"),
    queryRows<QualityCheck>(db, "SELECT * FROM quality_checks ORDER BY inspected_on DESC, id DESC"),
    queryRows<Risk>(db, "SELECT r.*, t.name AS owner FROM risks r LEFT JOIN team_members t ON t.id=r.owner_id ORDER BY r.likelihood*r.impact DESC, r.id"),
    queryRows<Milestone>(db, "SELECT * FROM milestones ORDER BY due_date, id"),
    queryRows<ClosureRecord>(db, "SELECT * FROM closure_records ORDER BY recorded_on DESC, id DESC"),
  ]);
  const project = projects[0];
  if (!project) throw new Error("Project seed data is missing.");

  const schedule = calculateSchedule(activities, dependencies, project.start_date, true);
  const changeCost = changes.filter((change) => change.status === "Approved").reduce((sum, change) => sum + Number(change.cost_impact), 0);
  const changeWeeks = changes.filter((change) => change.status === "Approved").reduce((sum, change) => sum + Number(change.schedule_weeks), 0);
  const approvedBudget = Number(project.baseline_budget) + changeCost;
  const activityBudget = activities.reduce((sum, activity) => sum + Number(activity.budget), 0);
  const progress = activityBudget ? activities.reduce((sum, activity) => sum + Number(activity.budget) * Number(activity.actual_progress) / 100, 0) / activityBudget * 100 : 0;
  const evm = calculateEvm(activities, expenditures, schedule, project.status_date, approvedBudget);
  const forecastFinish = Object.values(schedule).map((item) => item.forecast_finish).sort().at(-1) ?? project.start_date;
  return {
    project, team, requirements, wbs, changes, changeItems, activities, dependencies, expenditures, defects, qualityChecks, risks, milestones, closures, schedule, evm,
    summary: {
      progress, approvedBudget, baselineBudget: Number(project.baseline_budget), activityBudget,
      pendingChanges: changes.filter((change) => change.status === "Pending").length,
      delayedActivities: activities.filter((activity) => Number(activity.delay_days) > 0).length,
      unresolvedCriticalDefects: defects.filter((defect) => defect.severity === "Critical" && defect.status !== "Resolved").length,
      approvedRequirements: requirements.filter((requirement) => requirement.status === "Approved").length,
      forecastFinish, revisedWeeks: Number(project.baseline_duration_weeks) + changeWeeks, changeCost, changeWeeks,
    },
  };
}
