PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS project (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    name TEXT NOT NULL,
    objective TEXT NOT NULL,
    stakeholders TEXT NOT NULL,
    in_scope TEXT NOT NULL,
    out_scope TEXT NOT NULL,
    plan_scope TEXT NOT NULL,
    plan_schedule TEXT NOT NULL,
    plan_cost TEXT NOT NULL,
    plan_quality TEXT NOT NULL,
    start_date TEXT NOT NULL,
    status_date TEXT NOT NULL,
    baseline_budget REAL NOT NULL CHECK (baseline_budget >= 0),
    baseline_duration_weeks INTEGER NOT NULL CHECK (baseline_duration_weeks > 0),
    project_status TEXT NOT NULL,
    closure_record TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS team_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS requirements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    priority TEXT NOT NULL CHECK (priority IN ('Critical','High','Medium','Low')),
    status TEXT NOT NULL CHECK (status IN ('Pending','Approved','Rejected')),
    source_change_id INTEGER REFERENCES change_requests(id),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS wbs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    parent_id INTEGER REFERENCES wbs(id),
    name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('Approved','Pending','Rejected')),
    source_change_id INTEGER REFERENCES change_requests(id)
);

CREATE TABLE IF NOT EXISTS change_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    justification TEXT NOT NULL,
    cost_impact REAL NOT NULL CHECK (cost_impact >= 0),
    schedule_weeks INTEGER NOT NULL CHECK (schedule_weeks >= 0),
    status TEXT NOT NULL CHECK (status IN ('Pending','Approved','Rejected')),
    applied_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS change_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    change_id INTEGER NOT NULL REFERENCES change_requests(id) ON DELETE CASCADE,
    requirement_id INTEGER REFERENCES requirements(id),
    wbs_id INTEGER REFERENCES wbs(id),
    requirement_text TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'High',
    wbs_name TEXT NOT NULL,
    activity_name TEXT NOT NULL,
    activity_days INTEGER NOT NULL CHECK (activity_days > 0),
    activity_cost REAL NOT NULL CHECK (activity_cost >= 0),
    team_member_id INTEGER REFERENCES team_members(id)
);

CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    wbs_id INTEGER REFERENCES wbs(id),
    name TEXT NOT NULL,
    team_member_id INTEGER REFERENCES team_members(id),
    duration_days INTEGER NOT NULL CHECK (duration_days > 0),
    budget REAL NOT NULL CHECK (budget >= 0),
    actual_progress REAL NOT NULL DEFAULT 0 CHECK (actual_progress BETWEEN 0 AND 100),
    delay_days INTEGER NOT NULL DEFAULT 0 CHECK (delay_days >= 0),
    is_milestone INTEGER NOT NULL DEFAULT 0 CHECK (is_milestone IN (0,1)),
    source_change_id INTEGER REFERENCES change_requests(id),
    source_item_id INTEGER UNIQUE REFERENCES change_items(id)
);

CREATE TABLE IF NOT EXISTS dependencies (
    activity_id INTEGER NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    predecessor_id INTEGER NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    PRIMARY KEY (activity_id, predecessor_id),
    CHECK (activity_id <> predecessor_id)
);

CREATE TABLE IF NOT EXISTS expenditures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id INTEGER NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    amount REAL NOT NULL CHECK (amount >= 0),
    spent_on TEXT NOT NULL,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS defects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('Critical','High','Medium','Low')),
    assignee_id INTEGER REFERENCES team_members(id),
    status TEXT NOT NULL CHECK (status IN ('Open','In Progress','Resolved')),
    opened_on TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS quality_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item TEXT NOT NULL,
    deliverable TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN ('Not Run','Pass','Fail')),
    inspected_on TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS risks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    likelihood INTEGER NOT NULL CHECK (likelihood BETWEEN 1 AND 5),
    impact INTEGER NOT NULL CHECK (impact BETWEEN 1 AND 5),
    response TEXT NOT NULL,
    owner_id INTEGER REFERENCES team_members(id),
    status TEXT NOT NULL DEFAULT 'Open' CHECK (status IN ('Open','Monitoring','Closed'))
);

CREATE TABLE IF NOT EXISTS milestones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    due_date TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('Planned','Achieved','At Risk'))
);

CREATE TABLE IF NOT EXISTS closure_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recorded_on TEXT NOT NULL,
    summary TEXT NOT NULL,
    lessons_learned TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_activities_change ON activities(source_change_id);
CREATE INDEX IF NOT EXISTS idx_requirements_status ON requirements(status);
CREATE INDEX IF NOT EXISTS idx_change_status ON change_requests(status);
CREATE INDEX IF NOT EXISTS idx_expenditures_date ON expenditures(spent_on);
