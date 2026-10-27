"""SQLite persistence and business operations for the project management app."""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from scheduling import calculate_schedule, add_workdays, parse_date

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
DEFAULT_DB = (Path(sys.executable).resolve().parent / "smart_healthcare_project.sqlite3") if getattr(sys, "frozen", False) else ROOT / "smart_healthcare_project.sqlite3"


def connect(db_path=DEFAULT_DB):
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize(db_path=DEFAULT_DB, reset=False):
    path = Path(db_path)
    if reset and path.exists():
        path.unlink()
    conn = connect(path)
    with conn:
        conn.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
    if conn.execute("SELECT COUNT(*) FROM project").fetchone()[0] == 0:
        seed_demo(conn)
    return conn


def _insert(conn, sql, values=()):
    return conn.execute(sql, values).lastrowid


def seed_demo(conn):
    """Insert realistic, clearly assumed demonstration data for the case."""
    conn.execute("BEGIN")
    try:
        conn.execute("""INSERT INTO project
            (id,name,objective,stakeholders,in_scope,out_scope,plan_scope,plan_schedule,
             plan_cost,plan_quality,start_date,status_date,baseline_budget,
             baseline_duration_weeks,project_status,closure_record)
            VALUES (1,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            "Smart Healthcare Project Management and Monitoring System",
            "Plan, execute, monitor, and control the development of a shared healthcare software platform for five hospitals.",
            "Hospital management; project manager; backend developers; frontend developers; database developer; quality assurance engineer; hospital users.",
            "Requirements, design, development, integration, testing, and deployment planning for appointments, laboratory reports, doctor schedules, online consultations, and hospital billing.",
            "Operating a hospital information system, clinical care, live medical diagnosis, and patient-facing production operations.",
            "Approved deliverables are limited to project work packages backed by approved requirements. Proposed changes remain pending until approved.",
            "16-week baseline using Monday-Friday working days; predecessor relationships control successor dates.",
            "PKR 5,000,000 original approved baseline; approved change effects are recorded separately.",
            "Inspection checklist, defect severity and status, and risk responses are recorded with the relevant deliverables.",
            "2026-01-05", "2026-02-10", 5_000_000, 16, "In Progress", ""
        ))
        members = [
            ("Project Manager", "Project Manager"),
            ("Backend Developer 1", "Backend Developer"),
            ("Backend Developer 2", "Backend Developer"),
            ("Frontend Developer 1", "Frontend Developer"),
            ("Frontend Developer 2", "Frontend Developer"),
            ("Database Developer", "Database Developer"),
            ("Quality Assurance Engineer", "Quality Assurance Engineer"),
        ]
        for name, role in members:
            _insert(conn, "INSERT INTO team_members(name,role) VALUES (?,?)", (name, role))
        member = {r["role"] + str(r["id"]): r["id"] for r in conn.execute("SELECT * FROM team_members")}
        members_by_name = {r["name"]: r["id"] for r in conn.execute("SELECT * FROM team_members")}

        wbs = {}
        wbs_rows = [
            ("1", None, "Smart healthcare project", "Approved"),
            ("1.1", "1", "Initiation and project planning", "Approved"),
            ("1.2", "1", "Requirements and architecture", "Approved"),
            ("1.3", "1", "Core healthcare platform", "Approved"),
            ("1.4", "1", "Integration and quality assurance", "Approved"),
            ("1.5", "1", "Deployment and training", "Approved"),
        ]
        for code, parent_code, name, status in wbs_rows:
            parent_id = wbs.get(parent_code) if parent_code else None
            wbs[code] = _insert(conn, "INSERT INTO wbs(code,parent_id,name,status) VALUES (?,?,?,?)", (code,parent_id,name,status))

        reqs = [
            ("REQ-01", "Register requirements and obtain approval before scope inclusion.", "Critical", "Approved", None),
            ("REQ-02", "Support appointment scheduling across five hospitals.", "Critical", "Approved", None),
            ("REQ-03", "Manage laboratory report workflows.", "High", "Approved", None),
            ("REQ-04", "Manage doctor schedules and online consultation workflows.", "High", "Approved", None),
            ("REQ-05", "Manage hospital billing workflows.", "High", "Approved", None),
            ("REQ-06", "Integrate patient record management and database services.", "Critical", "Approved", None),
        ]
        for code, text, priority, status, change_id in reqs:
            _insert(conn, "INSERT INTO requirements(code,description,priority,status,source_change_id) VALUES (?,?,?,?,?)", (code,text,priority,status,change_id))

        change_id = _insert(conn, """INSERT INTO change_requests
            (code,title,justification,cost_impact,schedule_weeks,status)
            VALUES (?,?,?,?,?,?)""", (
            "CR-001", "AI preliminary diagnosis and mobile application",
            "Hospital management proposed two additional deliverables after approval of the original baseline. Their combined estimate is PKR 800,000 and three additional weeks.",
            800_000, 3, "Pending"
        ))
        ai_req = _insert(conn, "INSERT INTO requirements(code,description,priority,status,source_change_id) VALUES (?,?,?,?,?)", ("REQ-07", "Provide an AI-based preliminary diagnosis module as a proposed project deliverable.", "High", "Pending", change_id))
        mobile_req = _insert(conn, "INSERT INTO requirements(code,description,priority,status,source_change_id) VALUES (?,?,?,?,?)", ("REQ-08", "Provide a mobile application as a proposed project deliverable.", "High", "Pending", change_id))
        ai_wbs = _insert(conn, "INSERT INTO wbs(code,parent_id,name,status,source_change_id) VALUES (?,?,?,?,?)", ("CR-001.1", wbs["1"], "AI preliminary diagnosis module", "Pending", change_id))
        mobile_wbs = _insert(conn, "INSERT INTO wbs(code,parent_id,name,status,source_change_id) VALUES (?,?,?,?,?)", ("CR-001.2", wbs["1"], "Mobile application", "Pending", change_id))
        conn.execute("""INSERT INTO change_items
            (change_id,requirement_id,wbs_id,requirement_text,priority,wbs_name,activity_name,activity_days,activity_cost,team_member_id)
            VALUES (?,?,?,?,?,?,?,?,?,?)""", (change_id,ai_req,ai_wbs,
            "Provide an AI-based preliminary diagnosis module as a proposed project deliverable.","High",
            "AI preliminary diagnosis module","AI preliminary diagnosis module",8,500_000,members_by_name["Backend Developer 2"]))
        conn.execute("""INSERT INTO change_items
            (change_id,requirement_id,wbs_id,requirement_text,priority,wbs_name,activity_name,activity_days,activity_cost,team_member_id)
            VALUES (?,?,?,?,?,?,?,?,?,?)""", (change_id,mobile_req,mobile_wbs,
            "Provide a mobile application as a proposed project deliverable.","High",
            "Mobile application","Mobile application",7,300_000,members_by_name["Frontend Developer 2"]))

        tasks = [
            ("ACT-01", "Project charter and kickoff", "1.1", "Project Manager", 5, 300_000, 100, 0, 1),
            ("ACT-02", "Requirements and architecture", "1.2", "Backend Developer 1", 8, 500_000, 100, 0, 0),
            ("ACT-03", "Data and API foundation", "1.3", "Database Developer", 10, 800_000, 100, 0, 0),
            ("ACT-04", "Appointment and patient record services", "1.3", "Backend Developer 1", 15, 900_000, 20, 3, 0),
            ("ACT-05", "Laboratory, schedules, consultation, and billing", "1.3", "Backend Developer 2", 15, 800_000, 45, 0, 0),
            ("ACT-06", "Web application", "1.3", "Frontend Developer 1", 15, 950_000, 0, 0, 0),
            ("ACT-07", "Integration and data migration", "1.4", "Database Developer", 7, 400_000, 0, 0, 0),
            ("ACT-08", "Quality assurance and user acceptance", "1.4", "Quality Assurance Engineer", 10, 250_000, 0, 0, 0),
            ("ACT-09", "Deployment and training", "1.5", "Project Manager", 5, 100_000, 0, 0, 1),
        ]
        activity = {}
        for code,name,wbs_code,assignee,duration,cost,progress,delay,milestone in tasks:
            activity[code] = _insert(conn, """INSERT INTO activities
                (code,wbs_id,name,team_member_id,duration_days,budget,actual_progress,delay_days,is_milestone)
                VALUES (?,?,?,?,?,?,?,?,?)""", (code,wbs[wbs_code],name,members_by_name[assignee],duration,cost,progress,delay,milestone))
        edges = [("ACT-02","ACT-01"),("ACT-03","ACT-02"),("ACT-04","ACT-03"),
                 ("ACT-05","ACT-03"),("ACT-06","ACT-04"),("ACT-06","ACT-05"),
                 ("ACT-07","ACT-06"),("ACT-08","ACT-07"),("ACT-09","ACT-08")]
        for successor, predecessor in edges:
            conn.execute("INSERT INTO dependencies(activity_id,predecessor_id) VALUES (?,?)", (activity[successor],activity[predecessor]))

        for code,amount,spent_on,desc in [
            ("ACT-01",300_000,"2026-01-09","Charter and kickoff work"),
            ("ACT-02",500_000,"2026-01-21","Requirements and architecture work"),
            ("ACT-03",820_000,"2026-02-04","Data and API foundation; sample cost variance"),
            ("ACT-04",230_000,"2026-02-10","Appointment and record services to status date"),
            ("ACT-05",355_000,"2026-02-10","Clinical workflow services to status date"),
        ]:
            conn.execute("INSERT INTO expenditures(activity_id,amount,spent_on,description) VALUES (?,?,?,?)", (activity[code],amount,spent_on,desc))

        for code,description,severity,assignee in [
            ("DEF-001","Appointment scheduling permits conflicting bookings under concurrent requests.","Critical","Quality Assurance Engineer"),
            ("DEF-002","Patient record management can associate an update with the wrong patient record.","Critical","Backend Developer 1"),
        ]:
            _insert(conn,"INSERT INTO defects(code,description,severity,assignee_id,status,opened_on) VALUES (?,?,?,?,?,?)",(code,description,severity,members_by_name[assignee],"Open","2026-02-10"))

        checks = [
            ("Appointment conflict and double-booking checks","Appointment scheduling","Fail","2026-02-10","Critical defect DEF-001 remains open."),
            ("Patient identity and record update checks","Patient record management","Fail","2026-02-10","Critical defect DEF-002 remains open."),
            ("Database/API integration smoke inspection","Data and API foundation","Pass","2026-02-10","Sample inspection recorded."),
        ]
        for row in checks:
            _insert(conn,"INSERT INTO quality_checks(item,deliverable,outcome,inspected_on,notes) VALUES (?,?,?,?,?)",row)

        risks = [
            ("RSK-01","Concurrent booking conflicts delay acceptance of appointment scheduling.",4,5,"Prevent: add conflict checks and concurrency tests. Correct: block conflicting writes and retest.","Quality Assurance Engineer"),
            ("RSK-02","Patient identity mapping defect causes an incorrect record update.",3,5,"Prevent: verify identity constraints and migration mappings. Correct: quarantine affected updates and reconcile records.","Database Developer"),
            ("RSK-03","AI module scope raises model validation and clinical approval needs.",4,5,"Prevent: define non-diagnostic boundaries and approval criteria. Correct: suspend the module until review criteria pass.","Project Manager"),
            ("RSK-04","Mobile application increases integration and release workload.",3,4,"Prevent: approve interface contracts and staged integration. Correct: use the approved schedule reserve and reforecast.","Frontend Developer 1"),
        ]
        for code,desc,like,impact,response,owner in risks:
            _insert(conn,"INSERT INTO risks(code,description,likelihood,impact,response,owner_id,status) VALUES (?,?,?,?,?,?,?)",(code,desc,like,impact,response,members_by_name[owner],"Open"))

        # Project dates and milestone dates are generated using the documented workday rule.
        base_schedule = calculate_schedule(
            [dict(id=k, duration_days=row[4], delay_days=0) for k,row in enumerate(tasks, start=1)],
            [(2,1),(3,2),(4,3),(5,3),(6,4),(6,5),(7,6),(8,7),(9,8)], "2026-01-05", delays=False)
        milestones = [
            ("Charter approved", "2026-01-09", "Achieved"),
            ("Requirements complete", "2026-01-21", "Achieved"),
            ("Integrated platform UAT", "2026-04-10", "Planned"),
            ("Baseline deployment", "2026-04-17", "Planned"),
        ]
        for row in milestones:
            _insert(conn,"INSERT INTO milestones(name,due_date,status) VALUES (?,?,?)",row)
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def project_row(conn):
    row = conn.execute("SELECT * FROM project WHERE id=1").fetchone()
    return dict(row) if row else None


def approved_change_totals(conn):
    row = conn.execute("""SELECT COALESCE(SUM(cost_impact),0) cost,
        COALESCE(SUM(schedule_weeks),0) weeks,
        COALESCE(SUM(schedule_weeks*5),0) days
        FROM change_requests WHERE status='Approved'""").fetchone()
    return dict(row)


def project_budget(conn):
    project = project_row(conn)
    return float(project["baseline_budget"]) + float(approved_change_totals(conn)["cost"])


def revised_duration_weeks(conn):
    project = project_row(conn)
    return int(project["baseline_duration_weeks"]) + int(approved_change_totals(conn)["weeks"])


def get_activities(conn):
    return [dict(r) for r in conn.execute("""SELECT a.*, t.name assignee, w.code wbs_code
        FROM activities a LEFT JOIN team_members t ON t.id=a.team_member_id
        LEFT JOIN wbs w ON w.id=a.wbs_id ORDER BY a.id""")]


def get_schedule(conn, delays=True):
    p = project_row(conn)
    tasks = get_activities(conn)
    edges = [tuple(r) for r in conn.execute("SELECT activity_id,predecessor_id FROM dependencies")]
    return calculate_schedule(tasks, edges, p["start_date"], delays=delays)


def validate_dependency_change(conn, activity_id, predecessor_ids):
    aid = int(activity_id)
    proposed = [(aid, int(pred)) for pred in predecessor_ids]
    current = [tuple(r) for r in conn.execute("SELECT activity_id,predecessor_id FROM dependencies WHERE activity_id<>?", (aid,))]
    # Validate target IDs and cycles before changing the database.
    calculate_schedule(get_activities(conn), current + proposed, project_row(conn)["start_date"])
    return True


def create_change_request(conn, title, justification, cost_impact, schedule_weeks, requirement_text, priority="High"):
    title, justification, requirement_text = title.strip(), justification.strip(), requirement_text.strip()
    cost = float(cost_impact)
    weeks = int(schedule_weeks)
    if not title or not justification or not requirement_text:
        raise ValueError("Title, justification, and proposed requirement are required.")
    if cost < 0:
        raise ValueError("Cost impact cannot be negative.")
    if weeks < 1:
        raise ValueError("Schedule impact must be at least one workweek for an activity-based change.")
    next_num = conn.execute("SELECT COALESCE(MAX(id),0)+1 FROM change_requests").fetchone()[0]
    code = f"CR-{next_num:03d}"
    root_wbs = conn.execute("SELECT id FROM wbs WHERE parent_id IS NULL ORDER BY id LIMIT 1").fetchone()
    req_code = f"REQ-{conn.execute('SELECT COALESCE(MAX(id),0)+1 FROM requirements').fetchone()[0]:02d}"
    wbs_code = f"CR-{next_num:03d}.1"
    try:
        with conn:
            cid = _insert(conn,"INSERT INTO change_requests(code,title,justification,cost_impact,schedule_weeks,status) VALUES (?,?,?,?,?,'Pending')",(code,title,justification,cost,weeks))
            req = _insert(conn,"INSERT INTO requirements(code,description,priority,status,source_change_id) VALUES (?,?,?,'Pending',?)",(req_code,requirement_text,priority,cid))
            wbsid = _insert(conn,"INSERT INTO wbs(code,parent_id,name,status,source_change_id) VALUES (?,?,?,'Pending',?)",(wbs_code,root_wbs[0] if root_wbs else None,title,cid))
            member = conn.execute("SELECT id FROM team_members WHERE role='Project Manager' ORDER BY id LIMIT 1").fetchone()
            conn.execute("""INSERT INTO change_items(change_id,requirement_id,wbs_id,requirement_text,priority,wbs_name,
                         activity_name,activity_days,activity_cost,team_member_id)
                         VALUES (?,?,?,?,?,?,?,?,?,?)""",(cid,req,wbsid,requirement_text,priority,title,title,weeks*5,cost,member[0] if member else None))
        return code
    except sqlite3.IntegrityError as exc:
        raise ValueError(f"The change request could not be saved: {exc}") from exc


def approve_change(conn, change_id):
    """Atomically approve and apply one pending request once across scope/cost/schedule."""
    try:
        conn.execute("BEGIN IMMEDIATE")
        change = conn.execute("SELECT * FROM change_requests WHERE id=?", (int(change_id),)).fetchone()
        if not change:
            raise ValueError("Change request was not found.")
        if change["status"] != "Pending" or change["applied_at"]:
            raise ValueError("This change is not pending; its impact cannot be applied twice.")
        items = list(conn.execute("SELECT * FROM change_items WHERE change_id=? ORDER BY id", (change_id,)))
        if not items:
            raise ValueError("A change request needs at least one scope item before approval.")
        item_cost = sum(float(i["activity_cost"]) for i in items)
        item_days = sum(int(i["activity_days"]) for i in items)
        if abs(item_cost - float(change["cost_impact"])) > 0.01 or item_days != int(change["schedule_weeks"]) * 5:
            raise ValueError("Scope item estimates must equal the request totals before approval.")
        for item in items:
            if item["requirement_id"]:
                conn.execute("UPDATE requirements SET status='Approved' WHERE id=? AND source_change_id=?",(item["requirement_id"],change_id))
            if item["wbs_id"]:
                conn.execute("UPDATE wbs SET status='Approved' WHERE id=? AND source_change_id=?",(item["wbs_id"],change_id))

        # Attach the first new activity to all current terminal activities, then
        # sequence the change items so their total workday impact is explicit.
        tasks = get_activities(conn)
        edges = [tuple(r) for r in conn.execute("SELECT activity_id,predecessor_id FROM dependencies")]
        predecessors = {pred for _successor, pred in edges}
        sinks = [int(t["id"]) for t in tasks if int(t["id"]) not in predecessors]
        previous = None
        for index, item in enumerate(items, start=1):
            code = f"{change['code']}-ACT-{index:02d}"
            activity_id = _insert(conn,"""INSERT INTO activities(code,wbs_id,name,team_member_id,duration_days,budget,
                actual_progress,delay_days,is_milestone,source_change_id,source_item_id)
                VALUES (?,?,?,?,?,?,0,0,0,?,?)""",(code,item["wbs_id"],item["activity_name"],item["team_member_id"],
                item["activity_days"],item["activity_cost"],change_id,item["id"]))
            preds = [previous] if previous else sinks
            for pred in preds:
                if pred != activity_id:
                    conn.execute("INSERT INTO dependencies(activity_id,predecessor_id) VALUES (?,?)",(activity_id,pred))
            previous = activity_id
        conn.execute("UPDATE change_requests SET status='Approved',applied_at=? WHERE id=? AND status='Pending'",(datetime.now().isoformat(timespec="seconds"),change_id))
        conn.commit()
        return {"cost": item_cost, "days": item_days, "weeks": item_days / 5}
    except Exception:
        conn.rollback()
        raise


def reject_change(conn, change_id):
    with conn:
        row = conn.execute("SELECT status,applied_at FROM change_requests WHERE id=?",(int(change_id),)).fetchone()
        if not row:
            raise ValueError("Change request was not found.")
        if row["status"] != "Pending" or row["applied_at"]:
            raise ValueError("Only a pending, unapplied request can be rejected.")
        conn.execute("UPDATE change_requests SET status='Rejected' WHERE id=?",(change_id,))
        conn.execute("UPDATE requirements SET status='Rejected' WHERE source_change_id=? AND status='Pending'",(change_id,))
        conn.execute("UPDATE wbs SET status='Rejected' WHERE source_change_id=? AND status='Pending'",(change_id,))


def dashboard_data(conn):
    activities = get_activities(conn)
    approved = [dict(r) for r in conn.execute("SELECT * FROM requirements WHERE status='Approved'")]
    total_budget = sum(float(a["budget"]) for a in activities)
    weighted_progress = sum(float(a["budget"]) * float(a["actual_progress"]) / 100 for a in activities)
    progress = weighted_progress / total_budget * 100 if total_budget else 0.0
    schedule = get_schedule(conn, delays=True)
    p = project_row(conn)
    critical = conn.execute("SELECT COUNT(*) FROM defects WHERE severity='Critical' AND status<>'Resolved'").fetchone()[0]
    delayed = [a for a in activities if int(a["delay_days"]) > 0]
    pending_changes = conn.execute("SELECT COUNT(*) FROM change_requests WHERE status='Pending'").fetchone()[0]
    return {
        "progress": progress,
        "approved_budget": project_budget(conn),
        "baseline_budget": float(p["baseline_budget"]),
        "activity_budget": total_budget,
        "pending_changes": pending_changes,
        "delayed_activities": len(delayed),
        "unresolved_critical_defects": int(critical),
        "approved_requirements": len(approved),
        "schedule": schedule,
    }
