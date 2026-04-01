import React, { useState } from "react";
import type { ServiceConfig, AuthMode } from "../types";
import { DEFAULT_SERVICE } from "../types";

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

  const displayName = service.name || `service-${index + 1}`;
  const fqdn = service.subdomain
    ? `${service.subdomain}.<domain>`
    : "—";

  return (
    <div className="card mb-2 overflow-hidden">
      {/* Header */}
      <button
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-800 transition-colors"
        onClick={() => setOpen((o) => !o)}
      >
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono bg-gray-700 text-gray-300 px-2 py-0.5 rounded">
            {index + 1}
          </span>
          <span className="font-medium text-gray-100">{displayName}</span>
          {service.host && (
            <span className="text-xs text-gray-500 font-mono">
              {service.host}:{service.port}
            </span>
          )}
          {service.subdomain && (
            <span className="text-xs text-brand-400 font-mono">{fqdn}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {service.websocket && <Tag>ws</Tag>}
          {service.auth !== "none" && <Tag color="yellow">auth:{service.auth}</Tag>}
          {service.rate_limit && <Tag color="purple">rl</Tag>}
          <span className="text-gray-500 text-lg leading-none">{open ? "▲" : "▼"}</span>
        </div>
      </button>

      {/* Body */}
      {open && (
        <div className="px-4 pb-4 border-t border-gray-700 pt-4">
          <div className="grid grid-cols-2 gap-3">
            {/* name */}
            <Field label="name *">
              <input
                className="input-base"
                value={service.name}
                placeholder="plex"
                onChange={(e) => set("name", e.target.value)}
              />
            </Field>
            {/* subdomain */}
            <Field label="subdomain *">
              <input
                className="input-base"
                value={service.subdomain}
                placeholder="plex"
                onChange={(e) => set("subdomain", e.target.value)}
              />
            </Field>
            {/* host */}
            <Field label="host *">
              <input
                className="input-base"
                value={service.host}
                placeholder="192.168.1.50"
                onChange={(e) => set("host", e.target.value)}
              />
            </Field>
            {/* port */}
            <Field label="port *">
              <input
                className="input-base"
                type="number"
                value={service.port}
                min={1}
                max={65535}
                onChange={(e) => set("port", Number(e.target.value))}
              />
            </Field>
            {/* auth */}
            <Field label="auth">
              <select
                className="input-base"
                value={service.auth}
                onChange={(e) => set("auth", e.target.value as AuthMode)}
              >
                <option value="none">none</option>
                <option value="basic">basic (htpasswd)</option>
                <option value="forward">forward (Authelia/Authentik)</option>
              </select>
            </Field>
            {/* rate_limit */}
            <Field label="rate_limit">
              <input
                className="input-base"
                value={service.rate_limit}
                placeholder="60/min"
                onChange={(e) => set("rate_limit", e.target.value)}
              />
            </Field>
            {/* max_upload */}
            <Field label="max_upload">
              <input
                className="input-base"
                value={service.max_upload}
                placeholder="10G"
                onChange={(e) => set("max_upload", e.target.value)}
              />
            </Field>
          </div>

          {/* Toggles */}
          <div className="flex gap-4 mt-3">
            <Toggle
              label="WebSocket"
              value={service.websocket}
              onChange={(v) => set("websocket", v)}
            />
            <Toggle
              label="CORS"
              value={service.cors}
              onChange={(v) => set("cors", v)}
            />
          </div>

          {/* Custom headers */}
          <HeadersEditor
            headers={service.headers}
            onChange={(h) => set("headers", h)}
          />

          {/* Remove */}
          <div className="mt-4 flex justify-end">
            <button
              className="text-xs text-red-400 hover:text-red-300 transition-colors"
              onClick={() => onRemove(index)}
            >
              Remove service
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ---- sub-components ----

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-xs text-gray-400 mb-1">{label}</label>
      {children}
    </div>
  );
}

function Toggle({
  label,
  value,
  onChange,
}: {
  label: string;
  value: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex items-center gap-2 cursor-pointer select-none">
      <div
        className={`w-9 h-5 rounded-full transition-colors ${
          value ? "bg-brand-600" : "bg-gray-600"
        } relative`}
        onClick={() => onChange(!value)}
      >
        <div
          className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${
            value ? "translate-x-4" : "translate-x-0.5"
          }`}
        />
      </div>
      <span className="text-sm text-gray-300">{label}</span>
    </label>
  );
}

function Tag({
  children,
  color = "blue",
}: {
  children: React.ReactNode;
  color?: "blue" | "yellow" | "purple";
}) {
  const colors = {
    blue: "bg-blue-900/50 text-blue-300",
    yellow: "bg-yellow-900/50 text-yellow-300",
    purple: "bg-purple-900/50 text-purple-300",
  };
  return (
    <span className={`text-xs px-1.5 py-0.5 rounded font-mono ${colors[color]}`}>
      {children}
    </span>
  );
}

function HeadersEditor({
  headers,
  onChange,
}: {
  headers: Record<string, string>;
  onChange: (h: Record<string, string>) => void;
}) {
  const entries = Object.entries(headers);

  const addRow = () => onChange({ ...headers, "": "" });
  const removeRow = (key: string) => {
    const next = { ...headers };
    delete next[key];
    onChange(next);
  };
  const updateKey = (oldKey: string, newKey: string) => {
    const next: Record<string, string> = {};
    for (const [k, v] of Object.entries(headers)) {
      next[k === oldKey ? newKey : k] = v;
    }
    onChange(next);
  };
  const updateVal = (key: string, val: string) =>
    onChange({ ...headers, [key]: val });

  return (
    <div className="mt-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-gray-400">custom headers</span>
        <button className="text-xs text-brand-400 hover:text-brand-300" onClick={addRow}>
          + add header
        </button>
      </div>
      {entries.map(([k, v], i) => (
        <div key={i} className="flex gap-2 mb-1">
          <input
            className="input-base flex-1"
            value={k}
            placeholder="X-Header-Name"
            onChange={(e) => updateKey(k, e.target.value)}
          />
          <input
            className="input-base flex-1"
            value={v}
            placeholder="value"
            onChange={(e) => updateVal(k, e.target.value)}
          />
          <button
            className="text-red-500 hover:text-red-400 px-2"
            onClick={() => removeRow(k)}
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
}
