"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, BarChart3, CalendarDays, CheckSquare, ChevronRight, ClipboardList, FileText, HeartPulse, LayoutDashboard, LogOut, Menu, Plus, RefreshCw, Settings2, ShieldCheck, SlidersHorizontal, Stethoscope, WalletCards, X } from "lucide-react";
import Dashboard from "@/components/dashboard";
import { FormDialog, type CommandHandler, type FormSpec } from "@/components/forms";
import { CostView, InitiationView, QualityView, ReportsView, ScheduleView, ScopeView } from "@/components/project-modules";
import type { Snapshot } from "@/lib/types";

type Section = "Overview" | "Initiation" | "Scope & WBS" | "Schedule" | "Cost & EVM" | "Quality & Risk" | "Reports";
const nav: { name: Section; icon: typeof Activity }[] = [
  { name: "Overview", icon: LayoutDashboard }, { name: "Initiation", icon: ClipboardList },
  { name: "Scope & WBS", icon: CheckSquare }, { name: "Schedule", icon: CalendarDays },
  { name: "Cost & EVM", icon: WalletCards }, { name: "Quality & Risk", icon: ShieldCheck },
  { name: "Reports", icon: BarChart3 },
];
const shortNav: { name: Section | "More"; label: string; icon: typeof Activity }[] = [
  { name: "Overview", label: "Home", icon: LayoutDashboard }, { name: "Scope & WBS", label: "Scope", icon: CheckSquare },
  { name: "Schedule", label: "Plan", icon: CalendarDays }, { name: "Quality & Risk", label: "Quality", icon: ShieldCheck },
  { name: "More", label: "More", icon: Menu },
];

export default function Workspace() {
  const [checked, setChecked] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);
  const [password, setPassword] = useState("");
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [active, setActive] = useState<Section>("Overview");
  const [form, setForm] = useState<FormSpec | null>(null);
  const [mobileMore, setMobileMore] = useState(false);
  const [busy, setBusy] = useState(false);
  const [pageError, setPageError] = useState("");
  const [loginError, setLoginError] = useState("");
  const [toast, setToast] = useState("");

  const refresh = useCallback(async () => {
    setBusy(true); setPageError("");
    try {
      const response = await fetch("/api/state", { cache: "no-store" });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error ?? "The project data could not be loaded.");
      setSnapshot(result as Snapshot);
    } catch (error) { setPageError(error instanceof Error ? error.message : "The project data could not be loaded."); }
    finally { setBusy(false); }
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/auth", { cache: "no-store" }).then((response) => response.json()).then(async (result) => {
      if (cancelled) return;
      setAuthenticated(Boolean(result.authenticated)); setChecked(true);
      if (result.authenticated) await refresh();
    }).catch(() => { if (!cancelled) { setChecked(true); setLoginError("Could not connect to the app service."); } });
    return () => { cancelled = true; };
  }, [refresh]);

  const command: CommandHandler = useCallback(async (type, payload) => {
    const response = await fetch("/api/command", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ type, payload }) });
    const result = await response.json();
    if (!response.ok) {
      if (response.status === 401) { setAuthenticated(false); setSnapshot(null); }
      throw new Error(result.error ?? "The change could not be saved.");
    }
    setToast(result.message ?? "Saved successfully.");
    window.setTimeout(() => setToast(""), 3200);
    await refresh();
  }, [refresh]);

  async function signIn(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setLoginError(""); setBusy(true);
    try {
      const response = await fetch("/api/auth", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ password }) });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error ?? "Sign in failed.");
      setAuthenticated(true); setPassword(""); await refresh();
    } catch (error) { setLoginError(error instanceof Error ? error.message : "Sign in failed."); }
    finally { setBusy(false); }
  }
  async function signOut() {
    await fetch("/api/auth", { method: "DELETE" }); setAuthenticated(false); setSnapshot(null); setActive("Overview");
  }

  const pageTitle = useMemo(() => nav.find((item) => item.name === active)?.name ?? "Overview", [active]);
  if (!checked) return <div className="loading-state"><div className="loading-mark"><span className="loading-spinner" />Connecting to CarePlan…</div></div>;
  if (!authenticated) return <main className="login-screen"><section className="login-card"><div className="brand"><span className="brand-mark">+</span><span className="brand-copy"><strong>CarePlan</strong><small>Healthcare project control</small></span></div><h1>Welcome back</h1><p>Enter the workspace password configured for this project. Project records are available to signed-in workspace users.</p><form onSubmit={signIn}><label>Workspace password<input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required autoFocus /></label>{loginError && <div className="error-banner">{loginError}</div>}<button className="button button-primary" type="submit" disabled={busy}>{busy ? "Checking…" : "Continue to workspace"}<ChevronRight size={15} /></button></form><p className="login-foot">A project-management demo with synthetic healthcare workflow data.</p></section></main>;

  if (!snapshot) return <div className="loading-state"><div className="loading-mark"><span className="loading-spinner" />{pageError ? <><span>{pageError}</span><button className="button button-secondary" onClick={refresh}><RefreshCw size={14} /> Retry connection</button></> : <span>Loading project workspace…</span>}</div></div>;

  function openForm(spec: FormSpec) { setForm(spec); }
  const title = snapshot.project.name;
  return <div className="app-frame">
    <aside className="sidebar">
      <div className="brand"><span className="brand-mark">+</span><span className="brand-copy"><strong>CarePlan</strong><small>Project delivery suite</small></span></div>
      <div className="nav-caption">WORKSPACE</div><nav className="nav-list" aria-label="Workspace navigation">{nav.map(({ name, icon: Icon }) => <button key={name} className={`nav-item ${active === name ? "active" : ""}`} onClick={() => setActive(name)} aria-current={active === name ? "page" : undefined}><Icon size={17} /><span>{name}</span></button>)}</nav>
      <div className="sidebar-bottom"><div className="sidebar-card"><span className="eyebrow">CONNECTED PROGRAM</span><strong>Smart Healthcare · 5 hospitals</strong><p>Planning, monitoring, and delivery evidence in one place.</p></div><div className="sidebar-user"><span className="avatar">PM</span><span><strong>Project workspace</strong><small>Administrator session</small></span><button className="logout-mini" aria-label="Sign out" title="Sign out" onClick={signOut}><LogOut size={15} /></button></div></div>
    </aside>

    <div className="main-shell">
      <header className="topbar"><div className="crumbs"><span className="mobile-brand"><span className="brand-mark">+</span><strong>CarePlan</strong></span><span className="crumb-secondary">Workspace</span><ChevronRight className="crumb-secondary" size={13} /><span className="crumb-dot" /><strong>{pageTitle}</strong></div><div className="top-actions"><span className="connection-pill"><i /> <span>Database connected</span></span><button className="icon-button" title="Refresh project data" aria-label="Refresh project data" onClick={refresh} disabled={busy}><RefreshCw size={15} /></button><button className="icon-button" title="Sign out" aria-label="Sign out" onClick={signOut}><LogOut size={15} /></button></div></header>
      <main className="page-content">
        {pageError && <div className="error-banner page-error">{pageError} <button className="button button-small button-quiet" onClick={refresh}>Retry</button></div>}
        {active === "Overview" && <><div className="page-heading"><div><span className="eyebrow">OVERVIEW</span><h1>Good planning starts with a clear view.</h1><p>Monitor the five-hospital software program and resolve the next delivery decision.</p></div><div className="heading-actions"><button className="button button-secondary" onClick={() => setActive("Reports")}><FileText size={15} /> Project report</button></div></div><Dashboard data={snapshot} openScope={() => setActive("Scope & WBS")} /></>}
        {active === "Initiation" && <InitiationView data={snapshot} openForm={openForm} onCommand={command} />}
        {active === "Scope & WBS" && <ScopeView data={snapshot} openForm={openForm} onCommand={command} />}
        {active === "Schedule" && <ScheduleView data={snapshot} openForm={openForm} onCommand={command} />}
        {active === "Cost & EVM" && <CostView data={snapshot} openForm={openForm} onCommand={command} />}
        {active === "Quality & Risk" && <QualityView data={snapshot} openForm={openForm} onCommand={command} />}
        {active === "Reports" && <ReportsView data={snapshot} />}
      </main>
    </div>

    <nav className="mobile-bottom-nav" aria-label="Mobile navigation">{shortNav.map(({ name, label, icon: Icon }) => <button key={name} className={`mobile-nav-item ${name === active || (name === "More" && mobileMore) ? "active" : ""}`} onClick={() => name === "More" ? setMobileMore(!mobileMore) : (setMobileMore(false), setActive(name))}><Icon /><span>{label}</span></button>)}</nav>
    {mobileMore && <div className="mobile-more">{nav.filter((item) => !["Overview", "Scope & WBS", "Schedule", "Quality & Risk"].includes(item.name)).map(({ name, icon: Icon }) => <button key={name} className={`nav-item ${active === name ? "active" : ""}`} onClick={() => { setActive(name); setMobileMore(false); }}><Icon size={16} />{name}</button>)}</div>}
    {toast && <div className="toast" role="status"><span className="toast-check"><CheckSquare size={15} /></span>{toast}<button onClick={() => setToast("")} aria-label="Dismiss notification"><X size={14} /></button></div>}
    {form && <FormDialog spec={form} onClose={() => setForm(null)} onSubmit={command} />}
  </div>;
}
