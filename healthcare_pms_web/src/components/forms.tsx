"use client";

import { useState } from "react";
import { X } from "lucide-react";

export type FieldOption = { label: string; value: string | number };
export type FormField = {
  name: string; label: string; type?: "text" | "number" | "date" | "textarea" | "select" | "multi";
  options?: FieldOption[]; placeholder?: string; min?: number; max?: number; step?: number;
  required?: boolean; full?: boolean; hidden?: boolean; defaultValue?: string | number; defaultValues?: (string | number)[]; helper?: string;
};
export type FormSpec = { title: string; description?: string; command: string; submitLabel?: string; fields: FormField[] };
export type CommandHandler = (type: string, payload: Record<string, unknown>) => Promise<void>;

export function FormDialog({ spec, onClose, onSubmit }: { spec: FormSpec; onClose: () => void; onSubmit: CommandHandler }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload: Record<string, unknown> = {};
    for (const field of spec.fields) {
      const raw = form.getAll(field.name);
      if (field.type === "multi") payload[field.name] = raw.filter(Boolean).map(Number);
      else if (field.type === "number") payload[field.name] = raw[0] === "" ? null : Number(raw[0]);
      else payload[field.name] = String(raw[0] ?? "");
    }
    setBusy(true); setError("");
    try { await onSubmit(spec.command, payload); onClose(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "The change could not be saved."); }
    finally { setBusy(false); }
  }
  return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !busy) onClose(); }}>
    <section className="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <div className="modal-header"><div><span className="eyebrow">PROJECT WORKSPACE</span><h2 id="modal-title">{spec.title}</h2>{spec.description && <p>{spec.description}</p>}</div><button className="icon-button" aria-label="Close dialog" type="button" onClick={onClose} disabled={busy}><X size={17} /></button></div>
      <form onSubmit={submit}>
        <div className="form-grid">{spec.fields.map((field) => field.hidden ? <input key={field.name} name={field.name} type="hidden" defaultValue={field.defaultValue} /> : <label className={`form-field ${field.full ? "field-full" : ""}`} key={field.name}>
          <span>{field.label}{field.required === false && <small> · optional</small>}</span>
          {field.type === "textarea" ? <textarea name={field.name} required={field.required !== false} placeholder={field.placeholder} defaultValue={field.defaultValue} rows={4} /> : field.type === "select" || field.type === "multi" ? <select name={field.name} required={field.required !== false && field.type !== "multi"} multiple={field.type === "multi"} defaultValue={field.type === "multi" ? (field.defaultValues ?? []).map(String) : String(field.defaultValue ?? (field.required === false ? "" : field.options?.[0]?.value ?? ""))} size={field.type === "multi" ? Math.min(5, field.options?.length ?? 4) : undefined}><>{field.type !== "multi" && field.required === false && <option value="">None selected</option>}{field.options?.map((option) => <option value={option.value} key={String(option.value)}>{option.label}</option>)}</></select> : <input name={field.name} type={field.type ?? "text"} min={field.min} max={field.max} step={field.step} required={field.required !== false} placeholder={field.placeholder} defaultValue={field.defaultValue} />}
          {field.helper && <small className="field-helper">{field.helper}</small>}
        </label>)}</div>
        {error && <div className="error-banner">{error}</div>}
        <div className="modal-footer"><button type="button" className="button button-quiet" onClick={onClose} disabled={busy}>Cancel</button><button className="button button-primary" type="submit" disabled={busy}>{busy ? "Saving…" : spec.submitLabel ?? "Save changes"}</button></div>
      </form>
    </section>
  </div>;
}
