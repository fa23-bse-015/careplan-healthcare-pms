"use client";

import { Activity, AlertTriangle, ArrowDownRight, ArrowUpRight, CalendarDays, CheckCircle2, Clock3, Coins, ShieldAlert, Sparkles, TrendingUp } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Snapshot } from "@/lib/types";

const money = (amount: number) => new Intl.NumberFormat("en-PK", { style: "currency", currency: "PKR", maximumFractionDigits: 0 }).format(amount);
const dateLabel = (value: string) => new Date(`${value}T00:00:00`).toLocaleDateString("en-PK", { day: "2-digit", month: "short", year: "numeric" });
const percent = (value: number) => `${value.toFixed(1)}%`;

function StatCard({ label, value, helper, icon: Icon, tone = "blue" }: { label: string; value: string; helper: string; icon: typeof Activity; tone?: string }) {
  return <article className={`stat-card tone-${tone}`}><div className="stat-top"><span className="stat-icon"><Icon size={18} /></span><span className="stat-label">{label}</span></div><strong className="stat-value">{value}</strong><span className="stat-helper">{helper}</span></article>;
}

export default function Dashboard({ data, openScope }: { data: Snapshot; openScope: () => void }) {
  const chartData = [
    { name: "Planned value", amount: data.evm.pv },
    { name: "Earned value", amount: data.evm.ev },
    { name: "Actual cost", amount: data.evm.ac },
  ];
  const watchlist = [...data.activities].sort((a, b) => {
    const aDelay = Number(a.delay_days) > 0 ? 0 : 1; const bDelay = Number(b.delay_days) > 0 ? 0 : 1;
    return aDelay - bDelay || (data.schedule[a.id]?.forecast_finish ?? "").localeCompare(data.schedule[b.id]?.forecast_finish ?? "");
  }).slice(0, 5);
  const pendingChange = data.changes.find((change) => change.status === "Pending");
  return <div className="page-stack">
    <section className="welcome-card">
      <div className="welcome-copy"><div className="eyebrow"><Sparkles size={14} /> FIVE-HOSPITAL DELIVERY PROGRAM</div><h2>Project control room</h2><p>One shared view of scope, schedule, budget, quality, and decisions.</p></div>
      <div className="welcome-date"><span>STATUS DATE</span><strong>{dateLabel(data.project.status_date)}</strong><small>{data.project.project_status}</small></div>
      <div className="welcome-decoration" aria-hidden="true"><span /><span /><span /></div>
    </section>

    <section className="stats-grid" aria-label="Project summary">
      <StatCard label="Overall progress" value={percent(data.summary.progress)} helper="Budget-weighted actual work" icon={Activity} tone="blue" />
      <StatCard label="Approved budget" value={money(data.summary.approvedBudget)} helper={`Baseline ${money(data.summary.baselineBudget)}`} icon={Coins} tone="green" />
      <StatCard label="Schedule forecast" value={`${data.summary.revisedWeeks} weeks`} helper={`Target ${dateLabel(data.summary.forecastFinish)}`} icon={CalendarDays} tone="violet" />
      <StatCard label="Open controls" value={`${data.summary.pendingChanges + data.summary.unresolvedCriticalDefects}`} helper={`${data.summary.pendingChanges} changes · ${data.summary.unresolvedCriticalDefects} critical defects`} icon={ShieldAlert} tone="amber" />
    </section>

    <section className="baseline-strip">
      <div><span className="eyebrow">APPROVED PLAN</span><strong>{money(data.summary.approvedBudget)}</strong><small>{data.summary.revisedWeeks} weeks · forecast {dateLabel(data.summary.forecastFinish)}</small></div>
      <span className="strip-divider" />
      <div><span className="eyebrow">BASELINE</span><strong>{money(data.summary.baselineBudget)}</strong><small>{data.project.baseline_duration_weeks} weeks · original plan</small></div>
      <span className={`change-chip ${data.summary.changeCost ? "change-chip-active" : ""}`}><TrendingUp size={15} /> {data.summary.changeCost ? `+${money(data.summary.changeCost)} · +${data.summary.changeWeeks} weeks approved` : "No approved change"}</span>
    </section>

    <section className="content-grid dashboard-grid">
      <article className="panel chart-panel">
        <div className="panel-heading"><div><span className="eyebrow">EARNED VALUE SNAPSHOT</span><h3>Delivery performance</h3></div><span className="live-tag"><span /> LIVE</span></div>
        <div className="metric-row">
          <div><span>Cost performance</span><strong>{data.evm.cpi === null ? "N/A" : data.evm.cpi.toFixed(2)}</strong><small>{data.evm.cpi !== null && data.evm.cpi >= 1 ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />} CPI</small></div>
          <div><span>Schedule performance</span><strong>{data.evm.spi === null ? "N/A" : data.evm.spi.toFixed(2)}</strong><small>{data.evm.spi !== null && data.evm.spi >= 1 ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />} SPI</small></div>
          <div><span>Cost variance</span><strong className={data.evm.cv >= 0 ? "positive-text" : "negative-text"}>{money(data.evm.cv)}</strong><small>{data.evm.cv >= 0 ? "Under earned value" : "Over earned value"}</small></div>
        </div>
        <div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><BarChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }} barSize={34}><CartesianGrid vertical={false} stroke="#e9eef5" /><XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: "#78879b" }} /><YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: "#78879b" }} tickFormatter={(value) => `${(value / 1000000).toFixed(1)}m`} width={38} /><Tooltip formatter={(value) => money(Number(value))} contentStyle={{ border: "1px solid #e7edf4", borderRadius: 12, fontSize: 12 }} /><Bar dataKey="amount" radius={[7, 7, 0, 0]} fill="#327ec0" /></BarChart></ResponsiveContainer></div>
        {data.evm.warnings.length > 0 ? <div className="warning-list">{data.evm.warnings.map((warning) => <p key={warning}><AlertTriangle size={15} /> {warning}</p>)}</div> : <div className="quiet-note"><CheckCircle2 size={15} /> No EVM warning thresholds are crossed.</div>}
      </article>

      <article className="panel watch-panel">
        <div className="panel-heading"><div><span className="eyebrow">DEPENDENCY PATH</span><h3>Schedule watchlist</h3></div><span className="count-badge">{data.summary.delayedActivities} delayed</span></div>
        <div className="activity-list">{watchlist.map((activity) => {
          const dates = data.schedule[activity.id]; const isDelayed = Number(activity.delay_days) > 0;
          return <div className="activity-row" key={activity.id}><span className={`activity-dot ${isDelayed ? "dot-red" : ""}`} /><div className="activity-main"><strong>{activity.name}</strong><small>{activity.code} · {activity.assignee ?? "Unassigned"}</small></div><div className="activity-right"><span className={isDelayed ? "negative-text" : ""}>{dateLabel(dates.forecast_finish)}</span><small>{percent(Number(activity.actual_progress))}</small></div></div>;
        })}</div>
        <div className="watch-footer"><Clock3 size={15} /> Forecast uses Monday–Friday workdays and linked predecessors.</div>
      </article>
    </section>

    <section className="content-grid bottom-grid">
      <article className="panel change-panel"><div className="panel-heading"><div><span className="eyebrow">CHANGE CONTROL</span><h3>Scope decisions</h3></div><span className={`status-pill ${pendingChange ? "status-pending" : "status-approved"}`}>{pendingChange ? "Action needed" : "Up to date"}</span></div>
        {pendingChange ? <><div className="change-feature"><div className="change-feature-icon"><Sparkles size={20} /></div><div><strong>{pendingChange.title}</strong><p>{pendingChange.justification}</p></div></div><div className="change-impact-row"><span><Coins size={15} /> +{money(pendingChange.cost_impact)}</span><span><CalendarDays size={15} /> +{pendingChange.schedule_weeks} weeks</span><span><Activity size={15} /> {data.changeItems.filter((item) => item.change_id === pendingChange.id).length} linked scope items</span></div><button className="button button-secondary" onClick={openScope}>Review scope &amp; changes <span>→</span></button></> : <div className="empty-inline"><CheckCircle2 size={17} /><span>All submitted changes have a decision. Review the approved baseline impact in scope control.</span></div>}
      </article>
      <article className="panel quality-panel"><div className="panel-heading"><div><span className="eyebrow">QUALITY &amp; RISK</span><h3>Items needing attention</h3></div><span className="count-badge count-warm">{data.summary.unresolvedCriticalDefects} critical</span></div>
        <div className="attention-list">{data.defects.filter((defect) => defect.severity === "Critical" && defect.status !== "Resolved").slice(0, 3).map((defect) => <div className="attention-item" key={defect.id}><span className="severity-mark" /><div><strong>{defect.code} · {defect.description}</strong><small>{defect.status} · Assigned to {defect.assignee ?? "Unassigned"}</small></div></div>)}{data.defects.filter((defect) => defect.severity === "Critical" && defect.status !== "Resolved").length === 0 && <div className="empty-inline"><CheckCircle2 size={17} /> No unresolved critical defects.</div>}</div>
        <div className="risk-foot"><span><AlertTriangle size={14} /> {data.risks.filter((risk) => risk.status !== "Closed" && risk.likelihood * risk.impact >= 15).length} high-rated open risks</span><span>{data.qualityChecks.filter((check) => check.outcome === "Fail").length} failed inspections</span></div>
      </article>
    </section>
  </div>;
}
