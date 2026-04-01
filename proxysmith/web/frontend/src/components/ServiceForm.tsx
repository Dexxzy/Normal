import React, { useState } from "react";
import type { ServiceConfig, AuthMode } from "../types";

interface Props {
  service: ServiceConfig;
  index: number;
  onUpdate: (index: number, svc: ServiceConfig) => void;
  onRemove: (index: number) => void;
}

export function ServiceForm({ service, index, onUpdate, onRemove }: Props) {
  const [open, setOpen] = useState(index === 0);

  const set = <K extends keyof ServiceConfig>(key: K, value: ServiceConfig[K]) =>
    onUpdate(index, { ...service, [key]: value });

  const chips: { label: string; color: string }[] = [];
  if (service.websocket) chips.push({ label: "ws", color: "text-blue-400 bg-blue-400/10" });
  if (service.auth !== "none") chips.push({ label: service.auth, color: "text-amber-400 bg-amber-400/10" });
  if (service.rate_limit) chips.push({ label: service.rate_limit, color: "text-purple-400 bg-purple-400/10" });
  if (service.max_upload) chips.push({ label: service.max_upload, color: "text-green-400 bg-green-400/10" });
  if (service.cors) chips.push({ label: "cors", color: "text-pink-400 bg-pink-400/10" });

  return (
    <div className="service-card mb-2 animate-fade-in">
      <button
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-surface-3 transition-colors"
        onClick={() => setOpen(o => !o)}
      >
        <span className="text-xs mono text-ink-4 w-5 text-center flex-shrink-0">{index + 1}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-ink-1">
              {service.name || <span className="text-ink-4 font-normal italic">unnamed</span>}
            </span>
            {service.host && service.port && (
              <span className="mono text-xs text-ink-4">{service.host}:{service.port}</span>
            )}
            {chips.map((c) => (
              <span key={c.label} className={`pill ${c.color}`}>{c.label}</span>
            ))}
          </div>
          {service.subdomain && (
            <div className="mono text-xs text-ink-4 mt-0.5">
              {service.subdomain}.<span className="text-ink-5">domain</span>
            </div>
          )}
        </div>
        <span className="text-ink-5 text-sm flex-shrink-0">{open ? "▴" : "▾"}</span>
      </button>

      {open && (
        <div className="px-4 pb-4 pt-3 border-t border-surface-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-ink-3 mb-1.5">name</label>
              <input className="input-field mono" value={service.name}
                placeholder="plex" onChange={e => set("name", e.target.value)} />
            </div>
            <div>
              <label className="block text-xs text-ink-3 mb-1.5">subdomain</label>
              <input className="input-field mono" value={service.subdomain}
                placeholder="plex" onChange={e => set("subdomain", e.target.value)} />
            </div>
            <div>
              <label className="block text-xs text-ink-3 mb-1.5">upstream host</label>
              <input className="input-field mono" value={service.host}
                placeholder="192.168.1.50" onChange={e => set("host", e.target.value)} />
            </div>
            <div>
              <label className="block text-xs text-ink-3 mb-1.5">port</label>
              <input className="input-field mono" type="number" value={service.port}
                min={1} max={65535} onChange={e => set("port", Number(e.target.value))} />
            </div>
          </div>

          {/* Optional fields — collapsed by default, shown when relevant */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-ink-3 mb-1.5">
                auth <span className="text-ink-5">optional</span>
              </label>
              <select className="input-field" value={service.auth}
                onChange={e => set("auth", e.target.value as AuthMode)}>
                <option value="none">none</option>
                <option value="basic">basic auth</option>
                <option value="forward">forward auth</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-ink-3 mb-1.5">
                rate limit <span className="text-ink-5">e.g. 60/min</span>
              </label>
              <input className="input-field mono" value={service.rate_limit}
                placeholder="60/min" onChange={e => set("rate_limit", e.target.value)} />
            </div>
            <div>
              <label className="block text-xs text-ink-3 mb-1.5">
                max upload <span className="text-ink-5">e.g. 10G</span>
              </label>
              <input className="input-field mono" value={service.max_upload}
                placeholder="10G" onChange={e => set("max_upload", e.target.value)} />
            </div>
          </div>

          <div className="flex gap-5 pt-1">
            <Toggle label="WebSocket" value={service.websocket} onChange={v => set("websocket", v)} />
            <Toggle label="CORS" value={service.cors} onChange={v => set("cors", v)} />
          </div>

          <HeadersEditor headers={service.headers} onChange={h => set("headers", h)} />

          <div className="pt-1 flex justify-end">
            <button onClick={() => onRemove(index)}
              className="text-xs text-ink-4 hover:text-red-400 transition-colors">
              remove
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function Toggle({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-center gap-2 cursor-pointer select-none">
      <button
        role="switch"
        aria-checked={value}
        onClick={() => onChange(!value)}
        className={`w-8 h-4.5 rounded-full relative transition-colors flex items-center ${
          value ? "bg-amber-500" : "bg-surface-5"
        }`}
        style={{ height: "18px" }}
      >
        <span className={`absolute w-3 h-3 bg-white rounded-full shadow transition-transform ${
          value ? "translate-x-4" : "translate-x-0.5"
        }`} />
      </button>
      <span className="text-xs text-ink-3">{label}</span>
    </label>
  );
}

function HeadersEditor({ headers, onChange }: { headers: Record<string, string>; onChange: (h: Record<string, string>) => void }) {
  const entries = Object.entries(headers);
  if (entries.length === 0) {
    return (
      <button onClick={() => onChange({ "": "" })}
        className="text-xs text-ink-4 hover:text-ink-3 transition-colors">
        + custom header
      </button>
    );
  }
  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs text-ink-3">custom headers</span>
        <button onClick={() => onChange({ ...headers, "": "" })}
          className="text-xs text-amber-500/70 hover:text-amber-400 transition-colors">+ add</button>
      </div>
      {entries.map(([k, v], i) => (
        <div key={i} className="flex gap-2 mb-1.5">
          <input className="input-field mono flex-1 text-xs" value={k} placeholder="X-Header"
            onChange={e => {
              const next: Record<string, string> = {};
              for (const [ek, ev] of Object.entries(headers)) next[ek === k ? e.target.value : ek] = ev;
              onChange(next);
            }} />
          <input className="input-field mono flex-1 text-xs" value={v} placeholder="value"
            onChange={e => onChange({ ...headers, [k]: e.target.value })} />
          <button onClick={() => { const n = { ...headers }; delete n[k]; onChange(n); }}
            className="text-ink-5 hover:text-red-400 px-2 text-sm transition-colors">×</button>
        </div>
      ))}
    </div>
  );
}
