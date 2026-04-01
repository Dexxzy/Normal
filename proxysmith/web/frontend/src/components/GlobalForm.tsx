import React from "react";
import type { GlobalConfig, SSLMode } from "../types";

interface Props {
  config: GlobalConfig;
  onChange: (g: GlobalConfig) => void;
}

export function GlobalForm({ config, onChange }: Props) {
  const set = <K extends keyof GlobalConfig>(k: K, v: GlobalConfig[K]) =>
    onChange({ ...config, [k]: v });

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-ink-3 mb-1.5">base domain</label>
          <input
            className="input-field"
            value={config.domain}
            placeholder="home.example.com"
            onChange={(e) => set("domain", e.target.value)}
          />
        </div>
        <div>
          <label className="block text-xs text-ink-3 mb-1.5">ssl mode</label>
          <select
            className="input-field"
            value={config.ssl}
            onChange={(e) => set("ssl", e.target.value as SSLMode)}
          >
            <option value="auto">auto — Let's Encrypt</option>
            <option value="manual">manual — your own certs</option>
            <option value="none">none — http only</option>
          </select>
        </div>
      </div>
      {config.ssl === "auto" && (
        <div>
          <label className="block text-xs text-ink-3 mb-1.5">
            acme email <span className="text-ink-4">(required for Let's Encrypt)</span>
          </label>
          <input
            className="input-field"
            type="email"
            value={config.email}
            placeholder="you@example.com"
            onChange={(e) => set("email", e.target.value)}
          />
        </div>
      )}
    </div>
  );
}
