"""Smart Healthcare Project Management and Monitoring System desktop app."""
from __future__ import annotations

import argparse
import csv
import sqlite3
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from database import (DEFAULT_DB, initialize, connect, project_row, project_budget,
    revised_duration_weeks, approved_change_totals, get_activities, get_schedule,
    dashboard_data, approve_change, reject_change, create_change_request,
    validate_dependency_change)
from evm import calculate_evm, performance_warnings
from scheduling import parse_date, add_workdays, planned_progress

NAVY = "#17365D"
BLUE = "#2F75B5"
PALE = "#EAF1F8"
INK = "#1D2939"
MUTED = "#667085"
GREEN = "#198754"
AMBER = "#B54708"
RED = "#B42318"
WHITE = "#FFFFFF"
BG = "#F4F7FB"


def money(value):
    return f"PKR {float(value):,.0f}"


def percent(value):
    return f"{float(value):.1f}%"


def ratio(value):
    return "N/A" if value is None else f"{value:.2f}"


class HealthcarePMS(tk.Tk):
    def __init__(self, db_path=DEFAULT_DB):
        super().__init__()
        self.title("Smart Healthcare Project Management System")
        self.geometry("1240x670")
        self.minsize(980, 560)
        try:
            self.state("zoomed")
        except tk.TclError:
            pass
        self.configure(bg=BG)
        self.db_path = Path(db_path)
        self.conn = initialize(self.db_path)
        self._style()
        self._build_shell()
        self.refresh_all()
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10), foreground=INK)
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=WHITE, relief="flat")
        style.configure("TLabel", background=BG, foreground=INK)
        style.configure("Muted.TLabel", foreground=MUTED, font=("Segoe UI", 9))
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 18), foreground=NAVY)
        style.configure("Section.TLabel", font=("Segoe UI Semibold", 12), foreground=NAVY)
        style.configure("CardValue.TLabel", font=("Segoe UI Semibold", 20), foreground=NAVY, background=WHITE)
        style.configure("CardLabel.TLabel", font=("Segoe UI", 9), foreground=MUTED, background=WHITE)
        style.configure("TButton", padding=(12, 7), background=PALE, foreground=NAVY, borderwidth=0)
        style.map("TButton", background=[("active", "#D8E6F3")])
        style.configure("Primary.TButton", background=NAVY, foreground=WHITE, font=("Segoe UI Semibold", 9))
        style.map("Primary.TButton", background=[("active", BLUE)], foreground=[("active", WHITE)])
        style.configure("Danger.TButton", background="#FEE4E2", foreground=RED)
        style.configure("Treeview", rowheight=28, background=WHITE, fieldbackground=WHITE, borderwidth=0)
        style.configure("Treeview.Heading", background=PALE, foreground=NAVY, font=("Segoe UI Semibold", 9), padding=(6, 7))
        style.map("Treeview", background=[("selected", "#CFE0F1")], foreground=[("selected", NAVY)])
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", padding=(16, 9), background="#E7EDF5", foreground=MUTED, font=("Segoe UI Semibold", 9))
        style.map("TNotebook.Tab", background=[("selected", WHITE)], foreground=[("selected", NAVY)])
        style.configure("TEntry", padding=6)
        style.configure("TCombobox", padding=5)
        style.configure("TProgressbar", troughcolor="#E4EAF1", background=BLUE)

    def _build_shell(self):
        header = tk.Frame(self, bg=NAVY, height=76)
        header.pack(fill="x")
        header.pack_propagate(False)
        brand = tk.Frame(header, bg=NAVY)
        brand.pack(side="left", padx=24, pady=13)
        tk.Label(brand, text="SPM", bg=BLUE, fg=WHITE, font=("Segoe UI Semibold", 13), padx=10, pady=7).pack(side="left", padx=(0, 13))
        title_box = tk.Frame(brand, bg=NAVY)
        title_box.pack(side="left")
        tk.Label(title_box, text="Smart Healthcare Project Management", bg=NAVY, fg=WHITE, font=("Segoe UI Semibold", 16)).pack(anchor="w")
        tk.Label(title_box, text="Project planning  /  control  /  evidence", bg=NAVY, fg="#C7D5E5", font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 0))
        self.header_state = tk.Label(header, text="", bg=NAVY, fg="#D6E1ED", font=("Segoe UI", 9))
        self.header_state.pack(side="right", padx=25)

        content = ttk.Frame(self, padding=(20, 17, 20, 10))
        content.pack(fill="both", expand=True)
        top = ttk.Frame(content)
        top.pack(fill="x", pady=(0, 12))
        ttk.Label(top, text="Project control room", style="Title.TLabel").pack(side="left")
        ttk.Label(top, text="Shared SQLite records update across every module", style="Muted.TLabel").pack(side="right", pady=(8, 0))
        self.tabs = ttk.Notebook(content)
        self.tabs.pack(fill="both", expand=True)
        self.dashboard_tab = ttk.Frame(self.tabs, padding=14)
        self.initiation_tab = ttk.Frame(self.tabs, padding=14)
        self.scope_tab = ttk.Frame(self.tabs, padding=14)
        self.schedule_tab = ttk.Frame(self.tabs, padding=14)
        self.cost_tab = ttk.Frame(self.tabs, padding=14)
        self.quality_tab = ttk.Frame(self.tabs, padding=14)
        self.reports_tab = ttk.Frame(self.tabs, padding=14)
        for frame, name in [(self.dashboard_tab,"Dashboard"),(self.initiation_tab,"Initiation"),
            (self.scope_tab,"Scope & WBS"),(self.schedule_tab,"Schedule"),(self.cost_tab,"Cost & EVM"),
            (self.quality_tab,"Quality & Risk"),(self.reports_tab,"Reports")]:
            self.tabs.add(frame, text=name)
        self._build_dashboard()
        self._build_initiation()
        self._build_scope()
        self._build_schedule()
        self._build_cost()
        self._build_quality()
        self._build_reports()
        footer = ttk.Frame(content)
        footer.pack(fill="x", pady=(8, 0))
        ttk.Label(footer, text="Baseline and approved changes are tracked independently", style="Muted.TLabel").pack(side="left")
        self.status_label = ttk.Label(footer, text="Ready", style="Muted.TLabel")
        self.status_label.pack(side="right")

    def _card(self, parent, label, value="—", note=""):
        frame = ttk.Frame(parent, style="Card.TFrame", padding=(15, 12))
        ttk.Label(frame, text=label.upper(), style="CardLabel.TLabel").pack(anchor="w")
        value_label = ttk.Label(frame, text=value, style="CardValue.TLabel")
        value_label.pack(anchor="w", pady=(6, 2))
        note_label = ttk.Label(frame, text=note, style="CardLabel.TLabel")
        note_label.pack(anchor="w")
        return frame, value_label, note_label

    def _tree(self, parent, columns, headings, widths=None, height=9):
        box = ttk.Frame(parent, style="Card.TFrame", padding=1)
        tree = ttk.Treeview(box, columns=columns, show="headings", height=height, selectmode="browse")
        for i, col in enumerate(columns):
            tree.heading(col, text=headings[i])
            tree.column(col, width=(widths[i] if widths else 130), anchor="w", stretch=True)
        vs = ttk.Scrollbar(box, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vs.set)
        tree.pack(side="left", fill="both", expand=True)
        vs.pack(side="right", fill="y")
        return box, tree

    def _build_dashboard(self):
        ttk.Label(self.dashboard_tab, text="At a glance", style="Section.TLabel").pack(anchor="w", pady=(0, 10))
        cards = ttk.Frame(self.dashboard_tab)
        cards.pack(fill="x")
        self.dash_cards = []
        for index, label in enumerate(["Overall progress", "Approved budget", "Pending changes", "Delayed activities", "Critical defects"]):
            card, value, note = self._card(cards, label)
            card.pack(side="left", fill="x", expand=True, padx=(0, 9))
            self.dash_cards.append((value, note))
            if index == 0:
                self.progress = ttk.Progressbar(card, maximum=100, mode="determinate", length=180)
                self.progress.pack(fill="x", pady=(7, 0))
        baseline_strip = ttk.Frame(self.dashboard_tab)
        baseline_strip.pack(fill="x", pady=(8, 9))
        ttk.Label(baseline_strip, text="BASELINE / APPROVED PLAN", style="Muted.TLabel").pack(side="left", padx=(2, 10))
        self.baseline_label = ttk.Label(baseline_strip, text="", style="Muted.TLabel", wraplength=1050)
        self.baseline_label.pack(side="left", fill="x", expand=True)
        lower = ttk.Frame(self.dashboard_tab)
        lower.pack(fill="both", expand=True)
        task_box = ttk.Frame(lower, style="Card.TFrame", padding=10)
        task_box.pack(side="left", fill="both", expand=True, padx=(0, 9))
        ttk.Label(task_box, text="Schedule watchlist", style="Section.TLabel").pack(anchor="w", pady=(2, 7))
        self.dash_task_frame, self.dash_tasks = self._tree(task_box,
            ("code","name","owner","finish","progress","flag"),
            ("ID","Activity","Owner","Forecast finish","Complete","Status"),
            (75,300,175,120,90,100),7)
        self.dash_task_frame.pack(fill="both", expand=True)
        change_box = ttk.Frame(lower, style="Card.TFrame", padding=10)
        change_box.pack(side="left", fill="both", expand=True, padx=(9, 0))
        ttk.Label(change_box, text="Change and quality controls", style="Section.TLabel").pack(anchor="w", pady=(2, 7))
        self.dash_change = ttk.Label(change_box, text="", background=WHITE, justify="left", wraplength=210)
        self.dash_change.pack(anchor="w", fill="x", pady=2)
        ttk.Button(change_box, text="Review scope and changes", command=lambda:self.tabs.select(self.scope_tab)).pack(anchor="w", pady=(10, 0))

    def _build_initiation(self):
        ttk.Label(self.initiation_tab, text="Project charter and management plan", style="Section.TLabel").pack(anchor="w", pady=(0, 8))
        self.project_views=ttk.Notebook(self.initiation_tab)
        self.project_views.pack(fill="both",expand=True)
        charter_view=ttk.Frame(self.project_views,padding=5)
        team_view=ttk.Frame(self.project_views,padding=5)
        closure_view=ttk.Frame(self.project_views,padding=5)
        self.project_views.add(charter_view,text="Charter & Project Plan")
        self.project_views.add(team_view,text="Team & Milestones")
        self.project_views.add(closure_view,text="Status & Closure")
        form = ttk.Frame(charter_view, style="Card.TFrame", padding=12)
        form.pack(fill="x")
        self.charter_vars = {}
        fields = [
            ("objective","Objectives and success condition"),("stakeholders","Stakeholders"),
            ("in_scope","Project scope boundaries - included"),("out_scope","Project scope boundaries - excluded"),
            ("plan_scope","Plan - scope control"),("plan_schedule","Plan - schedule"),
            ("plan_cost","Plan - cost"),("plan_quality","Plan - quality"),
        ]
        for ix, (key,label) in enumerate(fields):
            row,col=divmod(ix,2)
            cell=ttk.Frame(form, style="Card.TFrame")
            cell.grid(row=row,column=col,sticky="nsew",padx=7,pady=5)
            ttk.Label(cell,text=label,style="Muted.TLabel").pack(anchor="w")
            text=tk.Text(cell,height=2,width=58,wrap="word",font=("Segoe UI",9),relief="solid",bd=1,highlightthickness=0)
            text.pack(fill="x",pady=(3,0))
            self.charter_vars[key]=text
        form.columnconfigure(0,weight=1); form.columnconfigure(1,weight=1)
        meta=ttk.Frame(charter_view)
        meta.pack(fill="x",pady=(8,0))
        self.project_meta_label=ttk.Label(meta,text="",style="Muted.TLabel",wraplength=850,justify="left")
        self.project_meta_label.pack(side="left")
        ttk.Button(meta,text="Save charter and plan",style="Primary.TButton",command=self._save_project).pack(side="right")
        panels=ttk.Frame(team_view)
        panels.pack(fill="both",expand=True)
        team_box=ttk.Frame(panels,style="Card.TFrame",padding=10)
        team_box.pack(side="left",fill="both",expand=True,padx=(0,7))
        ttk.Label(team_box,text="Project team responsibilities",style="Section.TLabel").pack(anchor="w",pady=(1,8))
        self.team_frame,self.team_tree=self._tree(team_box,("name","role"),("Team member","Responsibility"),(350,400),8)
        self.team_frame.pack(fill="both",expand=True)
        milestone_box=ttk.Frame(panels,style="Card.TFrame",padding=10)
        milestone_box.pack(side="left",fill="both",expand=True,padx=(7,0))
        ttk.Label(milestone_box,text="Milestones",style="Section.TLabel").pack(anchor="w",pady=(1,8))
        self.milestone_frame,self.milestone_tree=self._tree(milestone_box,("name","due","status"),("Milestone","Due","Status"),(155,95,85),8)
        self.milestone_frame.pack(fill="both",expand=True)
        mb=ttk.Frame(milestone_box,style="Card.TFrame"); mb.pack(fill="x",pady=(8,0))
        ttk.Button(mb,text="Add milestone",command=self._add_milestone).pack(side="left")
        ttk.Button(mb,text="Record closure",command=self._add_closure).pack(side="right")
        closure=ttk.Frame(closure_view,style="Card.TFrame",padding=16)
        closure.pack(fill="both",expand=True)
        ttk.Label(closure,text="Project status and closure records",style="Section.TLabel").pack(anchor="w")
        self.closure_summary=ttk.Label(closure,text="",background=WHITE,justify="left",wraplength=1050)
        self.closure_summary.pack(fill="both",expand=True,anchor="nw",pady=(12,8))
        ttk.Button(closure,text="Record project closure",command=self._add_closure).pack(anchor="w")

    def _build_scope(self):
        self.scope_views=ttk.Notebook(self.scope_tab)
        self.scope_views.pack(fill="both",expand=True)
        self.scope_main_tab=ttk.Frame(self.scope_views,padding=5)
        self.scope_change_tab=ttk.Frame(self.scope_views,padding=5)
        self.scope_views.add(self.scope_main_tab,text="Requirements & WBS")
        self.scope_views.add(self.scope_change_tab,text="Change Control")
        top=ttk.Frame(self.scope_main_tab); top.pack(fill="both",expand=True)
        req_box=ttk.Frame(top,style="Card.TFrame",padding=10)
        req_box.pack(side="left",fill="both",expand=True,padx=(0,8))
        ttk.Label(req_box,text="Requirements",style="Section.TLabel").pack(anchor="w",pady=(1,7))
        self.req_frame,self.req_tree=self._tree(req_box,("code","priority","status","description"),("Code","Priority","Approval","Requirement"),(80,100,100,480),5)
        self.req_frame.pack(fill="both",expand=True)
        rb=ttk.Frame(req_box,style="Card.TFrame"); rb.pack(fill="x",pady=(8,0))
        ttk.Button(rb,text="Add requirement",command=self._add_requirement).pack(side="left")
        ttk.Button(rb,text="Edit selected",command=self._edit_requirement).pack(side="left",padx=6)
        ttk.Button(rb,text="Approve",style="Primary.TButton",command=lambda:self._requirement_status("Approved")).pack(side="left",padx=6)
        ttk.Button(rb,text="Reject",style="Danger.TButton",command=lambda:self._requirement_status("Rejected")).pack(side="left")
        wbs_box=ttk.Frame(top,style="Card.TFrame",padding=10)
        wbs_box.pack(side="left",fill="both",expand=True,padx=(8,0))
        ttk.Label(wbs_box,text="Approved scope WBS and proposed items",style="Section.TLabel").pack(anchor="w",pady=(1,7))
        self.wbs_frame,self.wbs_tree=self._tree(wbs_box,("code","status","name"),("WBS","Scope status","Deliverable / work package"),(65,75,170),5)
        self.wbs_frame.pack(fill="both",expand=True)
        ttk.Button(wbs_box,text="Add work package under selected node",command=self._add_wbs).pack(anchor="w",pady=(8,0))
        change_box=ttk.Frame(self.scope_change_tab,style="Card.TFrame",padding=12)
        change_box.pack(fill="both",expand=True)
        ch_head=ttk.Frame(change_box,style="Card.TFrame"); ch_head.pack(fill="x")
        ttk.Label(ch_head,text="Change control",style="Section.TLabel").pack(side="left")
        ttk.Label(ch_head,text="Approval applies scope, work packages, cost, and schedule in one transaction",style="Muted.TLabel").pack(side="right")
        self.change_frame,self.change_tree=self._tree(change_box,("code","title","cost","weeks","status"),("Request","Proposed change","Cost impact","Schedule","Status"),(100,650,150,120,130),5)
        self.change_frame.pack(fill="both",expand=True,pady=(8,7))
        self.change_tree.bind("<<TreeviewSelect>>",lambda _e:self._show_change_detail())
        self.change_detail=ttk.Label(change_box,text="Select a change request to view its justification and scope estimate breakdown.",style="Muted.TLabel",wraplength=1150,justify="left")
        self.change_detail.pack(fill="x",pady=(2,8))
        cb=ttk.Frame(change_box,style="Card.TFrame"); cb.pack(fill="x")
        ttk.Button(cb,text="Propose change",command=self._add_change).pack(side="left")
        ttk.Button(cb,text="Approve selected change",style="Primary.TButton",command=self._approve_change).pack(side="left",padx=7)
        ttk.Button(cb,text="Reject selected change",style="Danger.TButton",command=self._reject_change).pack(side="left")

    def _build_schedule(self):
        ttk.Label(self.schedule_tab,text="Dependency-based activity schedule",style="Section.TLabel").pack(anchor="w",pady=(0,7))
        self.schedule_summary=ttk.Label(self.schedule_tab,text="",style="Muted.TLabel")
        self.schedule_summary.pack(anchor="w",pady=(0,9))
        controls=ttk.Frame(self.schedule_tab); controls.pack(fill="x",pady=(0,8))
        ttk.Button(controls,text="Add activity",command=self._add_activity).pack(side="left")
        ttk.Button(controls,text="Update progress / delay",command=self._update_activity).pack(side="left",padx=6)
        ttk.Button(controls,text="Set dependencies",command=self._edit_dependencies).pack(side="left")
        ttk.Label(controls,text="Working-day rule: Monday-Friday; successors begin the next workday after their latest predecessor.",style="Muted.TLabel").pack(side="right")
        split=ttk.Panedwindow(self.schedule_tab,orient="vertical")
        split.pack(fill="both",expand=True)
        task_box=ttk.Frame(split,style="Card.TFrame",padding=6)
        gantt_box=ttk.Frame(split,style="Card.TFrame",padding=6)
        split.add(task_box,weight=3); split.add(gantt_box,weight=2)
        self.activity_frame,self.activity_tree=self._tree(task_box,("code","name","owner","days","start","finish","forecast","progress","delay"),("ID","Activity","Assigned member","Days","Planned start","Planned finish","Forecast finish","Actual","Delay"),(75,275,170,65,105,105,105,75,70),8)
        self.activity_frame.pack(fill="both",expand=True)
        ttk.Label(gantt_box,text="Gantt-style view - pale bars show baseline; navy bars show forecast",style="Muted.TLabel").pack(anchor="w",pady=(2,5))
        self.gantt=tk.Canvas(gantt_box,background=WHITE,highlightthickness=0,height=220)
        self.gantt.pack(fill="both",expand=True)
        self.gantt.bind("<Configure>",lambda _e:self._draw_gantt())

    def _build_cost(self):
        ttk.Label(self.cost_tab,text="Cost management and earned value",style="Section.TLabel").pack(anchor="w",pady=(0,8))
        self.evm_cards=[]
        row=ttk.Frame(self.cost_tab); row.pack(fill="x")
        for label in ["Planned value (PV)","Earned value (EV)","Actual cost (AC)","Cost index (CPI)","Schedule index (SPI)"]:
            card,val,note=self._card(row,label)
            card.pack(side="left",fill="x",expand=True,padx=(0,8))
            self.evm_cards.append((val,note))
        top=ttk.Frame(self.cost_tab); top.pack(fill="x",pady=11)
        self.evm_budget_label=ttk.Label(top,text="",style="Muted.TLabel")
        self.evm_budget_label.pack(side="left")
        ttk.Label(top,text="Status date",style="Muted.TLabel").pack(side="left",padx=(25,5))
        self.status_date_var=tk.StringVar()
        ttk.Entry(top,textvariable=self.status_date_var,width=13).pack(side="left")
        ttk.Button(top,text="Update date",command=self._save_status_date).pack(side="left",padx=5)
        ttk.Button(top,text="Record expenditure",style="Primary.TButton",command=self._add_expenditure).pack(side="right")
        self.warning_label=ttk.Label(self.cost_tab,text="",wraplength=1050,justify="left")
        self.warning_label.pack(fill="x",pady=(0,9))
        ttk.Label(self.cost_tab,text="Activity estimates and EVM detail",style="Section.TLabel").pack(anchor="w",pady=(0,6))
        self.cost_frame,self.cost_tree=self._tree(self.cost_tab,("code","name","budget","planned_pct","actual_pct","actual_cost","variance"),("Activity","Name","BAC","Planned %","Actual %","AC","EV - AC"),(85,400,130,100,100,130,115),13)
        self.cost_frame.pack(fill="both",expand=True)

    def _build_quality(self):
        ttk.Label(self.quality_tab,text="Defects, quality checks, and prioritized risks",style="Section.TLabel").pack(anchor="w",pady=(0,9))
        self.quality_views=ttk.Notebook(self.quality_tab)
        self.quality_views.pack(fill="both",expand=True)
        defects_view=ttk.Frame(self.quality_views,padding=5)
        risks_view=ttk.Frame(self.quality_views,padding=5)
        self.quality_views.add(defects_view,text="Defects & Quality Checklist")
        self.quality_views.add(risks_view,text="Risk Matrix & PDPC")
        left=ttk.Frame(defects_view,style="Card.TFrame",padding=10)
        left.pack(fill="both",expand=True)
        ttk.Label(left,text="Defect tracking",style="Section.TLabel").pack(anchor="w",pady=(0,6))
        self.defect_frame,self.defect_tree=self._tree(left,("code","severity","status","assignee","description"),("ID","Severity","Status","Assignee","Description"),(85,100,120,200,700),2)
        self.defect_frame.pack(fill="x",expand=False)
        db=ttk.Frame(left,style="Card.TFrame"); db.pack(fill="x",pady=(5,6))
        ttk.Button(db,text="Add defect",command=self._add_defect).pack(side="left")
        ttk.Button(db,text="Update status",command=self._update_defect).pack(side="left",padx=6)
        ttk.Label(left,text="Deliverable quality checklist",style="Section.TLabel").pack(anchor="w",pady=(0,6))
        self.quality_frame,self.quality_tree=self._tree(left,("item","deliverable","outcome","date","notes"),("Inspection","Deliverable","Outcome","Date","Notes"),(320,280,110,135,500),3)
        self.quality_frame.pack(fill="x",expand=False)
        ttk.Button(left,text="Record inspection",command=self._add_inspection).pack(anchor="w",pady=(7,0))
        right=ttk.Frame(risks_view,style="Card.TFrame",padding=10)
        right.pack(fill="both",expand=True)
        ttk.Label(right,text="Likelihood × impact matrix (1-5 scales); score = likelihood × impact",style="Muted.TLabel").pack(anchor="w",pady=(0,4))
        self.risk_matrix=tk.Canvas(right,height=125,background=WHITE,highlightthickness=0)
        self.risk_matrix.pack(fill="x",pady=(0,6))
        self.risk_matrix.bind("<Configure>",lambda _e:self._draw_risk_matrix())
        self.risk_frame,self.risk_tree=self._tree(right,("code","score","rank","risk","owner"),("Risk","L×I","Rank","Risk / issue","Owner"),(85,70,105,690,190),2)
        self.risk_frame.pack(fill="x",expand=False)
        self.risk_tree.bind("<<TreeviewSelect>>",lambda _e:self._show_risk_response())
        rb=ttk.Frame(right,style="Card.TFrame"); rb.pack(fill="x",pady=(7,4))
        ttk.Button(rb,text="Add risk",command=self._add_risk).pack(side="left")
        self.risk_response_label=ttk.Label(right,text="Select a risk to view the potential problem and its preventive and corrective actions.",style="Muted.TLabel",wraplength=1050,justify="left")
        self.risk_response_label.pack(fill="x",anchor="w",pady=(5,0))

    def _build_reports(self):
        ttk.Label(self.reports_tab,text="Integrated status report",style="Section.TLabel").pack(anchor="w",pady=(0,9))
        report=ttk.Frame(self.reports_tab,style="Card.TFrame",padding=8)
        report.pack(fill="x")
        self.report_summary=ttk.Label(report,text="",background=WHITE,justify="left",wraplength=1100,font=("Segoe UI",10))
        self.report_summary.pack(anchor="w",fill="x")
        actions=ttk.Frame(self.reports_tab); actions.pack(fill="x",pady=4)
        ttk.Button(actions,text="Export project summary CSV",style="Primary.TButton",command=self._export_csv).pack(side="left")
        ttk.Button(actions,text="Open application data folder",command=self._open_data_folder).pack(side="left",padx=8)
        ttk.Label(self.reports_tab,text="CSV export contains project, scope, schedule, EVM, quality, and risk details.",style="Muted.TLabel",wraplength=1040).pack(anchor="w",pady=(2,6))
        self.trace_frame,self.trace_tree=self._tree(self.reports_tab,("module","requirement","evidence"),("Question-paper module","Requirement","Application evidence"),(300,440,560),6)
        self.trace_frame.pack(fill="both",expand=True)

    def _selected_id(self, tree):
        selected=tree.selection()
        if not selected:
            raise ValueError("Select a row first.")
        return int(tree.item(selected[0],"tags")[0])

    def _dialog(self,title,fields,initial=None,combos=None):
        initial=initial or {}; combos=combos or {}
        win=tk.Toplevel(self); win.title(title); win.configure(bg=BG); win.transient(self); win.grab_set()
        win.resizable(True,True)
        body=ttk.Frame(win,padding=16); body.pack(fill="both",expand=True)
        vars_={}
        for i,(key,label) in enumerate(fields):
            ttk.Label(body,text=label).grid(row=i,column=0,sticky="nw",padx=(0,12),pady=6)
            if key in combos:
                var=tk.StringVar(value=str(initial.get(key,combos[key][0] if combos[key] else "")))
                widget=ttk.Combobox(body,textvariable=var,values=combos[key],state="readonly",width=55)
                widget.grid(row=i,column=1,sticky="ew",pady=6)
            elif key.startswith("_multi_"):
                var=tk.Text(body,width=58,height=4,wrap="word",font=("Segoe UI",9))
                var.grid(row=i,column=1,sticky="ew",pady=6)
                if initial.get(key): var.insert("1.0",str(initial[key]))
            else:
                var=tk.StringVar(value=str(initial.get(key,"")))
                ttk.Entry(body,textvariable=var,width=58).grid(row=i,column=1,sticky="ew",pady=6)
            vars_[key]=var
        body.columnconfigure(1,weight=1)
        result={"values":None}
        def submit():
            vals={}
            for k,v in vars_.items():
                vals[k]=v.get("1.0","end").strip() if k.startswith("_multi_") else v.get().strip()
            result["values"]=vals
            win.destroy()
        buttons=ttk.Frame(body); buttons.grid(row=len(fields),column=0,columnspan=2,sticky="e",pady=(12,0))
        ttk.Button(buttons,text="Cancel",command=win.destroy).pack(side="right",padx=(8,0))
        ttk.Button(buttons,text="Save",style="Primary.TButton",command=submit).pack(side="right")
        win.bind("<Return>",lambda _e:submit())
        self.wait_window(win)
        return result["values"]

    def _safe(self, action, success=None):
        try:
            value=action()
            if success: self.status_label.configure(text=success)
            self.refresh_all()
            return value
        except (ValueError,sqlite3.Error,KeyError) as exc:
            messagebox.showerror("Unable to complete action",str(exc),parent=self)
        except Exception as exc:
            messagebox.showerror("Unexpected application error",f"The operation was rolled back. Details: {exc}",parent=self)
        return None

    def refresh_all(self):
        self.refresh_dashboard(); self.refresh_initiation(); self.refresh_scope(); self.refresh_schedule(); self.refresh_cost(); self.refresh_quality(); self.refresh_reports()

    def refresh_dashboard(self):
        data=dashboard_data(self.conn); p=project_row(self.conn); totals=approved_change_totals(self.conn)
        cards=self.dash_cards
        cards[0][0].configure(text=percent(data["progress"])); cards[0][1].configure(text="Budget-weighted actual progress")
        cards[1][0].configure(text=money(data["approved_budget"])); cards[1][1].configure(text=f"Baseline {money(data['baseline_budget'])}")
        cards[2][0].configure(text=str(data["pending_changes"])); cards[2][1].configure(text="Awaiting approval")
        cards[3][0].configure(text=str(data["delayed_activities"])); cards[3][1].configure(text="Dependency path is evaluated")
        cards[4][0].configure(text=str(data["unresolved_critical_defects"])); cards[4][1].configure(text="Unresolved critical defects")
        self.progress["value"]=data["progress"]
        revised_weeks=revised_duration_weeks(self.conn)
        baseline_due=add_workdays(parse_date(p["start_date"]),int(p["baseline_duration_weeks"])*5)
        revised_due=add_workdays(parse_date(p["start_date"]),revised_weeks*5)
        change_effects = (f"Approved change effects | +{money(totals['cost'])} | +{totals['weeks']} weeks"
                          if totals["cost"] or totals["weeks"] else "Approved change effects | None")
        self.baseline_label.configure(text=(f"Original approved baseline  •  {money(p['baseline_budget'])}  •  {p['baseline_duration_weeks']} weeks  •  {baseline_due:%d %b %Y}\n"
             f"{change_effects}\n"
             f"Current approved plan  •  {money(data['approved_budget'])}  •  {revised_weeks} weeks  •  {revised_due:%d %b %Y}"))
        self.header_state.configure(text=f"{p['project_status']}  •  Status date {p['status_date']}")
        for item in self.dash_tasks.get_children(): self.dash_tasks.delete(item)
        activities=get_activities(self.conn); schedule=data["schedule"]; status=parse_date(p["status_date"])
        for a in activities:
            d=schedule[a["id"]]
            plan=planned_progress(d["planned_start"],d["planned_finish"],status)
            flag="Delayed" if a["delay_days"]>0 or (status>=d["planned_start"] and status<d["planned_finish"] and a["actual_progress"]+5<plan) else "On track"
            if flag=="Delayed" or a["is_milestone"]:
                self.dash_tasks.insert("","end",values=(a["code"],a["name"],a["assignee"] or "Unassigned",d["forecast_finish"].strftime("%d %b %Y"),percent(a["actual_progress"]),flag),tags=("delay" if flag=="Delayed" else "normal",))
        self.dash_tasks.tag_configure("delay",foreground=RED)
        changes=list(self.conn.execute("SELECT code,title,status,cost_impact,schedule_weeks FROM change_requests ORDER BY id DESC"))
        critical=list(self.conn.execute("SELECT code,description,status FROM defects WHERE severity='Critical' AND status<>'Resolved' ORDER BY id"))
        change_text="\n".join([f"{r['code']} {r['status']} | {money(r['cost_impact'])}, +{r['schedule_weeks']}w" for r in changes]) or "No change requests recorded."
        defect_codes=", ".join(r["code"] for r in critical) or "None"
        self.dash_change.configure(text=f"{change_text}\nCritical defects: {defect_codes}")

    def refresh_initiation(self):
        p=project_row(self.conn)
        for key,widget in self.charter_vars.items():
            widget.delete("1.0","end"); widget.insert("1.0",p.get(key,""))
        base_deadline=add_workdays(parse_date(p["start_date"]),int(p["baseline_duration_weeks"])*5)
        revised_deadline=add_workdays(parse_date(p["start_date"]),revised_duration_weeks(self.conn)*5)
        self.project_meta_label.configure(text=f"Start {p['start_date']}  •  Status date {p['status_date']}  •  Original budget {money(p['baseline_budget'])}\nBaseline {p['baseline_duration_weeks']} weeks to {base_deadline}  •  Current plan {revised_duration_weeks(self.conn)} weeks to {revised_deadline}  •  {p['project_status']}")
        self._fill(self.team_tree,self.conn.execute("SELECT * FROM team_members ORDER BY id"),lambda r:(r["name"],r["role"]))
        self._fill(self.milestone_tree,self.conn.execute("SELECT id,name,due_date,status FROM milestones ORDER BY due_date"),lambda r:(r["name"],r["due_date"],r["status"]))
        closes=list(self.conn.execute("SELECT recorded_on,summary,lessons_learned FROM closure_records ORDER BY id DESC LIMIT 4"))
        txt="The project is in progress; a closure record will be added when the project closes.\n\n" if not closes else "Recent closure records:\n\n"
        for r in closes: txt+=f"{r['recorded_on']}  •  {r['summary']}\nLessons: {r['lessons_learned']}\n\n"
        self.closure_summary.configure(text=txt)

    def _fill(self,tree,rows,mapper):
        for item in tree.get_children(): tree.delete(item)
        for row in rows:
            rid=row["id"]
            tree.insert("","end",values=mapper(row),tags=(str(rid),))

    def refresh_scope(self):
        self._fill(self.req_tree,self.conn.execute("SELECT * FROM requirements ORDER BY id"),lambda r:(r["code"],r["priority"],r["status"],r["description"]))
        self._fill(self.wbs_tree,self.conn.execute("SELECT * FROM wbs ORDER BY id"),lambda r:(r["code"],r["status"],r["name"]))
        self._fill(self.change_tree,self.conn.execute("SELECT * FROM change_requests ORDER BY id DESC"),lambda r:(r["code"],r["title"],money(r["cost_impact"]),f"+{r['schedule_weeks']} weeks",r["status"]))
        changes=self.change_tree.get_children()
        if changes:
            self.change_tree.selection_set(changes[0])
            self._show_change_detail()

    def _show_change_detail(self):
        selected=self.change_tree.selection()
        if not selected:return
        change_id=int(self.change_tree.item(selected[0],"tags")[0])
        change=self.conn.execute("SELECT * FROM change_requests WHERE id=?",(change_id,)).fetchone()
        items=list(self.conn.execute("SELECT * FROM change_items WHERE change_id=? ORDER BY id",(change_id,)))
        breakdown="; ".join(f"{item['wbs_name']}: {item['activity_days']} workdays, {money(item['activity_cost'])}" for item in items)
        self.change_detail.configure(text=f"Justification: {change['justification']}\nScope and estimate breakdown: {breakdown or 'No scope items recorded.'}")

    def refresh_schedule(self):
        activities=get_activities(self.conn); sch=get_schedule(self.conn,True); p=project_row(self.conn)
        revised_due=add_workdays(parse_date(p["start_date"]),revised_duration_weeks(self.conn)*5)
        completion=max([d["forecast_finish"] for d in sch.values()],default=parse_date(p["start_date"]))
        variance=(completion-revised_due).days
        self.schedule_summary.configure(text=f"Forecast completion {completion:%d %b %Y}  •  Current approved deadline {revised_due:%d %b %Y}  •  Calendar-day variance {variance:+d}  •  Change activities extend work by their approved working days")
        for item in self.activity_tree.get_children(): self.activity_tree.delete(item)
        status=parse_date(p["status_date"])
        for a in activities:
            d=sch[a["id"]]
            plan=planned_progress(d["planned_start"],d["planned_finish"],status)
            delayed=int(a["delay_days"])>0 or (status>=d["planned_start"] and status<d["planned_finish"] and a["actual_progress"]+5<plan)
            vals=(a["code"],a["name"],a["assignee"] or "Unassigned",a["duration_days"],d["planned_start"].strftime("%d %b %y"),d["planned_finish"].strftime("%d %b %y"),d["forecast_finish"].strftime("%d %b %y"),percent(a["actual_progress"]),f"{a['delay_days']} wd")
            self.activity_tree.insert("","end",values=vals,tags=(str(a["id"]),"delay" if delayed else "normal"))
        self.activity_tree.tag_configure("delay",foreground=RED)
        self._draw_gantt()

    def _draw_gantt(self):
        if not hasattr(self,"gantt") or not self.gantt.winfo_exists(): return
        c=self.gantt; c.delete("all")
        if not hasattr(self,"conn"): return
        try:
            tasks=get_activities(self.conn); sch=get_schedule(self.conn,True); p=project_row(self.conn)
            if not tasks: return
            width=max(c.winfo_width(),600); height=max(c.winfo_height(),170)
            left=205; right=width-20; plot=right-left
            p=project_row(self.conn)
            baseline_due=add_workdays(parse_date(p["start_date"]),int(p["baseline_duration_weeks"])*5)
            revised_due=add_workdays(parse_date(p["start_date"]),revised_duration_weeks(self.conn)*5)
            dates=[v["planned_start"] for v in sch.values()]+[v["forecast_finish"] for v in sch.values()]+[baseline_due,revised_due]
            start=min(dates); end=max(dates)+__import__('datetime').timedelta(days=1)
            span=max((end-start).days,1)
            def x(day): return left+(day-start).days/span*plot
            # Month boundaries and dates.
            cursor=date(start.year,start.month,1)
            if cursor<start: cursor=date(start.year+(start.month//12),(start.month%12)+1,1)
            while cursor<=end:
                px=x(cursor); c.create_line(px,23,px,height-10,fill="#E5EAF0",dash=(2,3))
                c.create_text(px+3,12,text=cursor.strftime("%b %Y"),anchor="w",fill=MUTED,font=("Segoe UI",8))
                cursor=date(cursor.year+(cursor.month//12),(cursor.month%12)+1,1)
            for due,color,label in [(baseline_due,"#98A2B3","Baseline"),(revised_due,RED,"Approved target")]:
                px=x(due); c.create_line(px,22,px,height-10,fill=color,width=2,dash=(4,3))
                c.create_text(px-3,24,text=label,anchor="ne",fill=color,font=("Segoe UI Semibold",8))
            y0=45; row_h=max(21,min(30,(height-55)/max(len(tasks),1)))
            for index,a in enumerate(tasks):
                d=sch[a["id"]]; y=y0+index*row_h
                if y+row_h>height: break
                c.create_text(left-7,y+row_h/2,text=a["code"],anchor="e",fill=INK,font=("Segoe UI",8))
                x1=x(d["planned_start"]); x2=x(d["planned_finish"]+__import__('datetime').timedelta(days=1))
                fx1=x(d["forecast_start"]); fx2=x(d["forecast_finish"]+__import__('datetime').timedelta(days=1))
                c.create_rectangle(x1,y+4,x2,y+row_h-4,fill="#D7E4F0",outline="")
                c.create_rectangle(fx1,y+8,fx2,y+row_h-8,fill=NAVY if not a["delay_days"] else AMBER,outline="")
        except Exception:
            return

    def refresh_cost(self):
        p=project_row(self.conn); tasks=get_activities(self.conn); sch=get_schedule(self.conn,True)
        expenses=[dict(r) for r in self.conn.execute("SELECT * FROM expenditures")]
        m=calculate_evm(tasks,expenses,sch,p["status_date"])
        vals=[money(m["pv"]),money(m["ev"]),money(m["ac"]),ratio(m["cpi"]),ratio(m["spi"])]
        notes=["Budgeted work by status date","Budgeted value of actual completion","Expenditure on or before status date","EV ÷ AC","EV ÷ PV"]
        for (value,note),v,n in zip(self.evm_cards,vals,notes): value.configure(text=v); note.configure(text=n)
        self.evm_budget_label.configure(text=f"Original budget: {money(p['baseline_budget'])}  •  Current approved budget: {money(project_budget(self.conn))}  •  Activity estimate total: {money(sum(float(t['budget']) for t in tasks))}")
        self.status_date_var.set(p["status_date"])
        warnings=performance_warnings(m,project_budget(self.conn))
        self.warning_label.configure(text="Warnings: " + ("  |  ".join(warnings) if warnings else "No threshold warnings. CPI / SPI warning threshold is below 0.95; actual cost warning is more than 10% above earned value."),foreground=AMBER if warnings else GREEN)
        for item in self.cost_tree.get_children(): self.cost_tree.delete(item)
        detail={d["activity_id"]:d for d in m["detail"]}
        for a in tasks:
            d=detail[a["id"]]; variance=d["ev"]-d["ac"]
            self.cost_tree.insert("","end",values=(a["code"],a["name"],money(a["budget"]),percent(d["planned_pct"]),percent(a["actual_progress"]),money(d["ac"]),money(variance)),tags=(str(a["id"]),))

    def refresh_quality(self):
        self._fill(self.defect_tree,self.conn.execute("""SELECT d.*,t.name assignee FROM defects d LEFT JOIN team_members t ON t.id=d.assignee_id ORDER BY CASE severity WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 ELSE 3 END,id"""),lambda r:(r["code"],r["severity"],r["status"],r["assignee"] or "Unassigned",r["description"]))
        self._fill(self.quality_tree,self.conn.execute("SELECT * FROM quality_checks ORDER BY inspected_on DESC,id DESC"),lambda r:(r["item"],r["deliverable"],r["outcome"],r["inspected_on"],r["notes"]))
        rows=list(self.conn.execute("""SELECT r.*,t.name owner FROM risks r LEFT JOIN team_members t ON t.id=r.owner_id ORDER BY likelihood*impact DESC,id"""))
        self._fill(self.risk_tree,rows,lambda r:(r["code"],f"{r['likelihood']}×{r['impact']}","Critical" if r['likelihood']*r['impact']>=20 else "High" if r['likelihood']*r['impact']>=12 else "Moderate",r["description"],r["owner"] or "Unassigned"))
        self._draw_risk_matrix(rows)
        children=self.risk_tree.get_children()
        if children:
            self.risk_tree.selection_set(children[0])
            self._show_risk_response()

    def _show_risk_response(self):
        selected=self.risk_tree.selection()
        if not selected:return
        code=self.risk_tree.item(selected[0],"values")[0]
        row=self.conn.execute("SELECT description,response FROM risks WHERE code=?",(code,)).fetchone()
        if not row:return
        response=row["response"]
        prevention,separator,correction=response.partition("Correct:")
        if not separator:prevention,separator,correction=response.partition("Corrective:")
        prevention=prevention.replace("Prevent:","Preventive action:").strip()
        correction=correction.strip()
        self.risk_response_label.configure(text=f"{prevention}  |  Corrective action: {correction if separator else 'No corrective action recorded.'}")

    def _draw_risk_matrix(self, rows=None):
        if not hasattr(self,"risk_matrix") or not self.risk_matrix.winfo_exists():return
        if rows is None:
            rows=list(self.conn.execute("SELECT code,likelihood,impact FROM risks"))
        c=self.risk_matrix; c.delete("all")
        w=max(c.winfo_width(),350); x0=42; y0=21; canvas_height=max(c.winfo_height(),150); size=min((w-65)/5,(canvas_height-50)/5,43); h=5*size
        c.create_text(x0+2.5*size,y0+h+24,text="Likelihood  →",fill=MUTED,font=("Segoe UI",8))
        c.create_text(10,y0+h/2,text="Impact",angle=90,fill=MUTED,font=("Segoe UI",8))
        colors={"low":"#E6F4EA","medium":"#FFF1C2","high":"#FDDCAB","critical":"#F9C7C5"}
        for impact in range(5,0,-1):
            for likelihood in range(1,6):
                score=impact*likelihood
                band="critical" if score>=20 else "high" if score>=12 else "medium" if score>=6 else "low"
                x=x0+(likelihood-1)*size; y=y0+(5-impact)*size
                c.create_rectangle(x,y,x+size,y+size,fill=colors[band],outline=WHITE,width=2)
                c.create_text(x+size/2,y+size/2,text=str(score),fill="#475467",font=("Segoe UI",8))
        c.create_text(x0-10,y0+0.5*size,text="5",anchor="e",fill=MUTED,font=("Segoe UI",8))
        c.create_text(x0-10,y0+4.5*size,text="1",anchor="e",fill=MUTED,font=("Segoe UI",8))
        for row in rows:
            if not isinstance(row,dict): row=dict(row)
            like=int(row["likelihood"]); impact=int(row["impact"])
            x=x0+(like-0.5)*size; y=y0+(5-impact+0.5)*size
            c.create_oval(x-9,y-9,x+9,y+9,fill=NAVY,outline=WHITE,width=2)
            c.create_text(x,y,text=str(row["code"])[-2:],fill=WHITE,font=("Segoe UI Semibold",7))
        for i in range(5): c.create_text(x0+(i+.5)*size,y0+h+8,text=str(i+1),fill=MUTED,font=("Segoe UI",8))

    def refresh_reports(self):
        p=project_row(self.conn); d=dashboard_data(self.conn); tasks=get_activities(self.conn); s=get_schedule(self.conn,True)
        evm=calculate_evm(tasks,[dict(r) for r in self.conn.execute("SELECT * FROM expenditures")],s,p["status_date"])
        completion=max([v["forecast_finish"] for v in s.values()],default=parse_date(p["start_date"]))
        self.report_summary.configure(text=(f"Project: {p['name']}\nStatus: {p['project_status']}  •  Status date: {p['status_date']}  •  Forecast completion: {completion:%d %b %Y}\n"
            f"Scope: {d['approved_requirements']} approved requirements  •  {len(tasks)} scheduled activities  •  {d['progress']:.1f}% budget-weighted completion\n"
            f"Budget: original baseline {money(p['baseline_budget'])}; current approved budget {money(project_budget(self.conn))}; PV {money(evm['pv'])}; EV {money(evm['ev'])}; AC {money(evm['ac'])}; CPI {ratio(evm['cpi'])}; SPI {ratio(evm['spi'])}\n"
            f"Controls: {d['pending_changes']} pending changes  •  {d['delayed_activities']} delayed activities  •  {d['unresolved_critical_defects']} unresolved critical defects"))
        rows=[
            ("1. Project Initiation and Integration Management","Charter, project plan, status, milestones, responsibilities, closure records","Charter/plan editor; team table; milestones and closure controls"),
            ("2. Scope Management and WBS","Requirements, approval, hierarchy, change control, unapproved scope exclusion","Approval-gated requirements; WBS status; atomic change approval"),
            ("3. Schedule and Resource Management","Assigned activities, duration, dependencies, dates, delays, Gantt timeline","Workday DAG scheduler; successor forecast; Gantt view"),
            ("4. Cost Management and Earned Value Analysis","Estimates, actual cost, PV/EV/AC/CPI/SPI and thresholds","Activity budget, expense records, task-level EVM and warning banner"),
            ("5. Quality Management and Risk Control","Defects, checklist, likelihood-impact matrix, PDPC responses","Severity and status tracking; inspection records; ranked risks with responses"),
            ("6. System Integration, Validation, and Reporting","Persistent integrated data, validation, dashboard and report","Single SQLite database; input checks; live dashboard; CSV status report"),
        ]
        for item in self.trace_tree.get_children(): self.trace_tree.delete(item)
        for row in rows:self.trace_tree.insert("","end",values=row)

    def _save_project(self):
        def action():
            values={k:v.get("1.0","end").strip() for k,v in self.charter_vars.items()}
            if any(not v for v in values.values()): raise ValueError("Complete all charter and plan fields before saving.")
            with self.conn:
                self.conn.execute("""UPDATE project SET objective=?,stakeholders=?,in_scope=?,out_scope=?,plan_scope=?,plan_schedule=?,plan_cost=?,plan_quality=? WHERE id=1""",
                    tuple(values[k] for k in ["objective","stakeholders","in_scope","out_scope","plan_scope","plan_schedule","plan_cost","plan_quality"]))
        self._safe(action,"Charter and management plan saved")

    def _add_milestone(self):
        vals=self._dialog("Add project milestone",[("name","Milestone name"),("due","Due date YYYY-MM-DD"),("status","Status")],combos={"status":["Planned","At Risk","Achieved"]})
        if not vals:return
        def action():
            parse_date(vals["due"])
            if not vals["name"]:raise ValueError("Milestone name is required.")
            with self.conn:self.conn.execute("INSERT INTO milestones(name,due_date,status) VALUES (?,?,?)",(vals["name"],vals["due"],vals["status"]))
        self._safe(action,"Milestone recorded")

    def _add_closure(self):
        vals=self._dialog("Record project closure",[("date","Recorded date YYYY-MM-DD"),("_multi_summary","Closure summary"),("_multi_lessons","Lessons learned")],initial={"date":date.today().isoformat()})
        if not vals:return
        def action():
            parse_date(vals["date"])
            if not vals["_multi_summary"] or not vals["_multi_lessons"]:raise ValueError("Both closure summary and lessons learned are required.")
            with self.conn:
                self.conn.execute("INSERT INTO closure_records(recorded_on,summary,lessons_learned) VALUES (?,?,?)",(vals["date"],vals["_multi_summary"],vals["_multi_lessons"]))
                self.conn.execute("UPDATE project SET project_status='Closed',closure_record=? WHERE id=1",(vals["_multi_summary"],))
        self._safe(action,"Closure record saved")

    def _add_requirement(self):
        vals=self._dialog("Add requirement",[("description","Requirement description"),("priority","Priority")],combos={"priority":["Critical","High","Medium","Low"]})
        if not vals:return
        def action():
            if not vals["description"]:raise ValueError("Requirement description is required.")
            code=f"REQ-{self.conn.execute('SELECT COALESCE(MAX(id),0)+1 FROM requirements').fetchone()[0]:02d}"
            with self.conn:self.conn.execute("INSERT INTO requirements(code,description,priority,status) VALUES (?,?,?,'Pending')",(code,vals["description"],vals["priority"]))
        self._safe(action,"Requirement added as Pending")

    def _edit_requirement(self):
        try: rid=self._selected_id(self.req_tree)
        except ValueError as exc:messagebox.showinfo("Select requirement",str(exc),parent=self);return
        row=self.conn.execute("SELECT * FROM requirements WHERE id=?",(rid,)).fetchone()
        vals=self._dialog("Edit requirement",[("description","Requirement description"),("priority","Priority")],initial={"description":row["description"],"priority":row["priority"]},combos={"priority":["Critical","High","Medium","Low"]})
        if not vals:return
        def action():
            if not vals["description"]:raise ValueError("Requirement description is required.")
            with self.conn:self.conn.execute("UPDATE requirements SET description=?,priority=? WHERE id=? AND status<>'Approved'",(vals["description"],vals["priority"],rid))
            if self.conn.execute("SELECT changes()").fetchone()[0]==0:raise ValueError("Approved requirements are locked; create a change request for scope revisions.")
        self._safe(action,"Requirement updated")

    def _requirement_status(self,status):
        try: rid=self._selected_id(self.req_tree)
        except ValueError as exc:messagebox.showinfo("Select requirement",str(exc),parent=self);return
        def action():
            row=self.conn.execute("SELECT * FROM requirements WHERE id=?",(rid,)).fetchone()
            if not row:raise ValueError("Requirement was not found.")
            if row["source_change_id"]:
                change=self.conn.execute("SELECT status FROM change_requests WHERE id=?",(row["source_change_id"],)).fetchone()
                if change and change["status"]=="Pending":raise ValueError("This requirement belongs to a pending change. Approve or reject the change request to apply it consistently.")
            if row["status"]!="Pending":raise ValueError("Only pending requirements can be approved or rejected.")
            with self.conn:self.conn.execute("UPDATE requirements SET status=? WHERE id=?",(status,rid))
        self._safe(action,f"Requirement {status.lower()}")

    def _add_wbs(self):
        try: parent_id=self._selected_id(self.wbs_tree)
        except ValueError as exc:messagebox.showinfo("Select WBS parent",str(exc),parent=self);return
        reqs=list(self.conn.execute("SELECT code,description FROM requirements WHERE status='Approved' ORDER BY code"))
        if not reqs:messagebox.showinfo("No approved requirement","Approve a requirement before adding an approved work package.",parent=self);return
        req_options=[f"{r['code']} | {r['description']}" for r in reqs]
        vals=self._dialog("Add approved WBS work package",[("name","Deliverable / work package"),("requirement","Associated approved requirement")],combos={"requirement":req_options})
        if not vals:return
        def action():
            if not vals["name"]:raise ValueError("Work package name is required.")
            parent=self.conn.execute("SELECT code,status FROM wbs WHERE id=?",(parent_id,)).fetchone()
            if not parent or parent["status"]!="Approved":raise ValueError("A work package can only be added under an approved WBS parent.")
            base=parent["code"] if parent else "1"
            child_codes=[r["code"] for r in self.conn.execute("SELECT code FROM wbs WHERE parent_id=?",(parent_id,))]
            ordinals=[]
            for child_code in child_codes:
                suffix=child_code[len(base)+1:] if child_code.startswith(base+".") else ""
                if suffix.isdigit():ordinals.append(int(suffix))
            ordinal=max(ordinals,default=0)+1
            code=f"{base}.{ordinal}"
            with self.conn:self.conn.execute("INSERT INTO wbs(code,parent_id,name,status) VALUES (?,?,?,'Approved')",(code,parent_id,vals["name"]))
        self._safe(action,"Approved work package added")

    def _add_change(self):
        vals=self._dialog("Propose scope change",[("title","Change title"),("justification","Business justification"),("cost","Total cost impact (PKR)"),("weeks","Schedule impact (workweeks)"),("requirement","Proposed requirement")],initial={"cost":"0","weeks":"1"})
        if not vals:return
        def action():
            try:cost=float(vals["cost"]); weeks=int(vals["weeks"])
            except ValueError as exc:raise ValueError("Cost must be numeric and schedule impact must be a whole number of workweeks.") from exc
            return create_change_request(self.conn,vals["title"],vals["justification"],cost,weeks,vals["requirement"])
        result=self._safe(action,"Change request saved as Pending")
        if result:messagebox.showinfo("Change request recorded",f"{result} is pending. It is excluded from approved scope and the current budget and deadline until approval.",parent=self)

    def _approve_change(self):
        try:cid=self._selected_id(self.change_tree)
        except ValueError as exc:messagebox.showinfo("Select change",str(exc),parent=self);return
        row=self.conn.execute("SELECT * FROM change_requests WHERE id=?",(cid,)).fetchone()
        if not row:return
        if not messagebox.askyesno("Approve project change",f"Approve {row['code']}? This applies the linked requirement and WBS items and adds {money(row['cost_impact'])} and {row['schedule_weeks']} weeks once.",parent=self):return
        result=self._safe(lambda:approve_change(self.conn,cid),"Approved scope, budget, and schedule updated")
        if result:messagebox.showinfo("Change applied once",f"{row['code']} approved.\n\nApproved budget: {money(project_budget(self.conn))}\nRevised duration: {revised_duration_weeks(self.conn)} weeks\nScope, activity cost, and schedule rows were updated together.",parent=self)

    def _reject_change(self):
        try:cid=self._selected_id(self.change_tree)
        except ValueError as exc:messagebox.showinfo("Select change",str(exc),parent=self);return
        self._safe(lambda:reject_change(self.conn,cid),"Change request rejected; no baseline impact applied")

    def _add_activity(self):
        members=[r["name"] for r in self.conn.execute("SELECT name FROM team_members ORDER BY id")]
        vals=self._dialog("Add scheduled activity",[("name","Activity name"),("owner","Assigned team member"),("days","Duration (working days)"),("budget","Activity cost estimate (PKR)"),("predecessors","Predecessor activity codes (comma separated; optional)")],combos={"owner":members})
        if not vals:return
        def action():
            try:days=int(vals["days"]);budget=float(vals["budget"])
            except ValueError as exc:raise ValueError("Duration must be a whole number and cost must be numeric.") from exc
            if days<1:raise ValueError("Duration must be at least one working day.")
            if budget<0:raise ValueError("Activity cost cannot be negative.")
            if not vals["name"]:raise ValueError("Activity name is required.")
            planned_total=sum(float(x["budget"]) for x in get_activities(self.conn))
            if planned_total+budget>project_budget(self.conn):
                raise ValueError("Activity estimates would exceed the approved budget. Record the added scope through a change request first.")
            owner=self.conn.execute("SELECT id FROM team_members WHERE name=?",(vals["owner"],)).fetchone()
            wbs=self.conn.execute("SELECT id FROM wbs WHERE status='Approved' ORDER BY id LIMIT 1").fetchone()
            code=f"ACT-{self.conn.execute('SELECT COALESCE(MAX(id),0)+1 FROM activities').fetchone()[0]:02d}"
            preds=[]
            for token in vals["predecessors"].split(","):
                token=token.strip()
                if token:
                    r=self.conn.execute("SELECT id FROM activities WHERE code=?",(token,)).fetchone()
                    if not r:raise ValueError(f"Unknown predecessor code: {token}")
                    preds.append(r[0])
            with self.conn:
                cur=self.conn.execute("INSERT INTO activities(code,wbs_id,name,team_member_id,duration_days,budget) VALUES (?,?,?,?,?,?)",(code,wbs[0] if wbs else None,vals["name"],owner[0],days,budget))
                aid=cur.lastrowid
                for pred in preds:self.conn.execute("INSERT INTO dependencies(activity_id,predecessor_id) VALUES (?,?)",(aid,pred))
                calculate_schedule(get_activities(self.conn),[tuple(r) for r in self.conn.execute("SELECT activity_id,predecessor_id FROM dependencies")],project_row(self.conn)["start_date"])
        self._safe(action,"Activity added to shared schedule")

    def _update_activity(self):
        try:aid=self._selected_id(self.activity_tree)
        except ValueError as exc:messagebox.showinfo("Select activity",str(exc),parent=self);return
        row=self.conn.execute("SELECT * FROM activities WHERE id=?",(aid,)).fetchone()
        vals=self._dialog("Update activity status",[("progress","Actual completion (%)"),("delay","Added delay (working days)"),("days","Original duration (working days)")],initial={"progress":row["actual_progress"],"delay":row["delay_days"],"days":row["duration_days"]})
        if not vals:return
        def action():
            try:pct=float(vals["progress"]);delay=int(vals["delay"]);days=int(vals["days"])
            except ValueError as exc:raise ValueError("Progress must be numeric; delay and duration must be whole numbers.") from exc
            if not 0<=pct<=100:raise ValueError("Completion percentage must be between 0 and 100.")
            if delay<0 or days<1:raise ValueError("Delay cannot be negative and duration must be positive.")
            with self.conn:self.conn.execute("UPDATE activities SET actual_progress=?,delay_days=?,duration_days=? WHERE id=?",(pct,delay,days,aid))
        self._safe(action,"Activity status updated; dependent forecasts refreshed")

    def _edit_dependencies(self):
        try:aid=self._selected_id(self.activity_tree)
        except ValueError as exc:messagebox.showinfo("Select activity",str(exc),parent=self);return
        row=self.conn.execute("SELECT * FROM activities WHERE id=?",(aid,)).fetchone()
        all_tasks=get_activities(self.conn); options=[f"{a['code']} | {a['name']}" for a in all_tasks if a["id"]!=aid]
        current=[self.conn.execute("SELECT code FROM activities WHERE id=?",(r[0],)).fetchone()[0] for r in self.conn.execute("SELECT predecessor_id FROM dependencies WHERE activity_id=?",(aid,))]
        vals=self._dialog("Set activity predecessors",[("predecessors","Predecessor activity codes, comma separated")],initial={"predecessors":", ".join(current)})
        if not vals:return
        def action():
            preds=[]
            for code in filter(None,[x.strip() for x in vals["predecessors"].split(",")]):
                pred=self.conn.execute("SELECT id FROM activities WHERE code=?",(code,)).fetchone()
                if not pred:raise ValueError(f"Unknown activity code {code}. Available: {', '.join(a['code'] for a in all_tasks if a['id']!=aid)}")
                preds.append(pred[0])
            validate_dependency_change(self.conn,aid,preds)
            with self.conn:
                self.conn.execute("DELETE FROM dependencies WHERE activity_id=?",(aid,))
                for pred in preds:self.conn.execute("INSERT INTO dependencies(activity_id,predecessor_id) VALUES (?,?)",(aid,pred))
        self._safe(action,"Dependencies saved; circular links are not permitted")

    def _save_status_date(self):
        value=self.status_date_var.get().strip()
        def action():
            parse_date(value)
            with self.conn:self.conn.execute("UPDATE project SET status_date=? WHERE id=1",(value,))
        self._safe(action,"EVM status date updated")

    def _add_expenditure(self):
        acts=get_activities(self.conn); options=[f"{a['code']} | {a['name']}" for a in acts]
        vals=self._dialog("Record actual expenditure",[("activity","Activity"),("amount","Amount in PKR"),("date","Date YYYY-MM-DD"),("description","Description")],initial={"date":project_row(self.conn)["status_date"]},combos={"activity":options})
        if not vals:return
        def action():
            try:amount=float(vals["amount"])
            except ValueError as exc:raise ValueError("Expenditure must be numeric.") from exc
            if amount<0:raise ValueError("Expenditure cannot be negative.")
            parse_date(vals["date"])
            if not vals["description"]:raise ValueError("Description is required.")
            code=vals["activity"].split(" | ",1)[0]
            aid=self.conn.execute("SELECT id FROM activities WHERE code=?",(code,)).fetchone()[0]
            with self.conn:self.conn.execute("INSERT INTO expenditures(activity_id,amount,spent_on,description) VALUES (?,?,?,?)",(aid,amount,vals["date"],vals["description"]))
        self._safe(action,"Expenditure recorded")

    def _add_defect(self):
        members=[r["name"] for r in self.conn.execute("SELECT name FROM team_members ORDER BY id")]
        vals=self._dialog("Record defect",[("description","Defect description"),("severity","Severity"),("assignee","Assigned team member")],initial={"assignee":"Quality Assurance Engineer"},combos={"severity":["Critical","High","Medium","Low"],"assignee":members})
        if not vals:return
        def action():
            if not vals["description"]:raise ValueError("Defect description is required.")
            code=f"DEF-{self.conn.execute('SELECT COALESCE(MAX(id),0)+1 FROM defects').fetchone()[0]:03d}"
            aid=self.conn.execute("SELECT id FROM team_members WHERE name=?",(vals["assignee"],)).fetchone()[0]
            with self.conn:self.conn.execute("INSERT INTO defects(code,description,severity,assignee_id,status,opened_on) VALUES (?,?,?,?,'Open',?)",(code,vals["description"],vals["severity"],aid,date.today().isoformat()))
        self._safe(action,"Defect recorded")

    def _update_defect(self):
        try:did=self._selected_id(self.defect_tree)
        except ValueError as exc:messagebox.showinfo("Select defect",str(exc),parent=self);return
        vals=self._dialog("Update defect status",[("status","Resolution status")],combos={"status":["Open","In Progress","Resolved"]})
        if not vals:return
        def action():
            with self.conn:self.conn.execute("UPDATE defects SET status=? WHERE id=?",(vals["status"],did))
        self._safe(action,"Defect status updated")

    def _add_inspection(self):
        vals=self._dialog("Record quality inspection",[("item","Checklist item"),("deliverable","Deliverable"),("outcome","Test outcome"),("date","Date YYYY-MM-DD"),("notes","Notes")],initial={"date":project_row(self.conn)["status_date"]},combos={"outcome":["Not Run","Pass","Fail"]})
        if not vals:return
        def action():
            if not vals["item"] or not vals["deliverable"]:raise ValueError("Checklist item and deliverable are required.")
            parse_date(vals["date"])
            with self.conn:self.conn.execute("INSERT INTO quality_checks(item,deliverable,outcome,inspected_on,notes) VALUES (?,?,?,?,?)",(vals["item"],vals["deliverable"],vals["outcome"],vals["date"],vals["notes"]))
        self._safe(action,"Inspection result recorded")

    def _add_risk(self):
        members=[r["name"] for r in self.conn.execute("SELECT name FROM team_members ORDER BY id")]
        vals=self._dialog("Add project risk",[("description","Risk description"),("likelihood","Likelihood 1-5"),("impact","Impact 1-5"),("owner","Risk owner"),("_multi_response","Preventive and corrective actions")],combos={"likelihood":["1","2","3","4","5"],"impact":["1","2","3","4","5"],"owner":members})
        if not vals:return
        def action():
            if not vals["description"] or not vals["_multi_response"]:raise ValueError("Risk description and response actions are required.")
            like=int(vals["likelihood"]);impact=int(vals["impact"])
            if not 1<=like<=5 or not 1<=impact<=5:raise ValueError("Likelihood and impact must be integers from 1 to 5.")
            code=f"RSK-{self.conn.execute('SELECT COALESCE(MAX(id),0)+1 FROM risks').fetchone()[0]:02d}"
            owner=self.conn.execute("SELECT id FROM team_members WHERE name=?",(vals["owner"],)).fetchone()
            with self.conn:self.conn.execute("INSERT INTO risks(code,description,likelihood,impact,response,owner_id) VALUES (?,?,?,?,?,?)",(code,vals["description"],like,impact,vals["_multi_response"],owner[0] if owner else None))
        self._safe(action,"Risk recorded and ranked")

    def _export_csv(self):
        path=filedialog.asksaveasfilename(parent=self,title="Save integrated status report",defaultextension=".csv",filetypes=[("CSV files","*.csv")],initialfile="project_status_report.csv")
        if not path:return
        try:
            p=project_row(self.conn); d=dashboard_data(self.conn); tasks=get_activities(self.conn); s=get_schedule(self.conn,True)
            m=calculate_evm(tasks,[dict(r) for r in self.conn.execute("SELECT * FROM expenditures")],s,p["status_date"])
            with open(path,"w",newline="",encoding="utf-8-sig") as f:
                out=csv.writer(f)
                out.writerow(["Smart Healthcare Project Management System - Integrated Status Report"])
                out.writerow(["Project",p["name"]]);out.writerow(["Status",p["project_status"]]);out.writerow(["Status date",p["status_date"]])
                out.writerow(["Original baseline budget PKR",p["baseline_budget"]]);out.writerow(["Current approved budget PKR",project_budget(self.conn)])
                out.writerow(["Baseline duration weeks",p["baseline_duration_weeks"]]);out.writerow(["Revised duration weeks",revised_duration_weeks(self.conn)])
                out.writerow(["Overall budget-weighted progress percent",d["progress"]]);out.writerow(["PV PKR",m["pv"]]);out.writerow(["EV PKR",m["ev"]]);out.writerow(["AC PKR",m["ac"]]);out.writerow(["CPI",ratio(m["cpi"])]);out.writerow(["SPI",ratio(m["spi"])])
                out.writerow([]);out.writerow(["Activities"]);out.writerow(["Code","Name","Assignee","Duration workdays","Planned start","Planned finish","Forecast finish","Budget PKR","Actual progress percent","Delay workdays"])
                for a in tasks:
                    x=s[a["id"]];out.writerow([a["code"],a["name"],a["assignee"],a["duration_days"],x["planned_start"],x["planned_finish"],x["forecast_finish"],a["budget"],a["actual_progress"],a["delay_days"]])
                out.writerow([]);out.writerow(["Requirements"]);out.writerow(["Code","Description","Priority","Approval"])
                for r in self.conn.execute("SELECT code,description,priority,status FROM requirements ORDER BY id"):out.writerow(tuple(r))
                out.writerow([]);out.writerow(["Change requests"]);out.writerow(["Code","Title","Cost impact PKR","Schedule impact weeks","Status"])
                for r in self.conn.execute("SELECT code,title,cost_impact,schedule_weeks,status FROM change_requests ORDER BY id"):out.writerow(tuple(r))
                out.writerow([]);out.writerow(["Defects"]);out.writerow(["Code","Severity","Status","Description"])
                for r in self.conn.execute("SELECT code,severity,status,description FROM defects ORDER BY id"):out.writerow(tuple(r))
                out.writerow([]);out.writerow(["Risks"]);out.writerow(["Code","Likelihood","Impact","Score","Description","Response"])
                for r in self.conn.execute("SELECT code,likelihood,impact,likelihood*impact,description,response FROM risks ORDER BY likelihood*impact DESC"):out.writerow(tuple(r))
            messagebox.showinfo("Report exported",f"Saved integrated CSV report to:\n{path}",parent=self)
        except Exception as exc:messagebox.showerror("Export failed",str(exc),parent=self)

    def _open_data_folder(self):
        import os
        os.startfile(str(self.db_path.resolve().parent))

    def _close(self):
        try:self.conn.close()
        finally:self.destroy()


def main():
    parser=argparse.ArgumentParser(description="Smart Healthcare Project Management System")
    parser.add_argument("--db",default=str(DEFAULT_DB),help="SQLite database file path")
    args=parser.parse_args()
    app=HealthcarePMS(args.db)
    app.mainloop()


if __name__=="__main__":
    main()
