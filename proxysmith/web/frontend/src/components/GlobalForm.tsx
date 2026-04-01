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
    <div className="grid grid-cols-3 gap-3">
      <div>
        <label className="block text-xs text-gray-400 mb-1">domain *</label>
        <input
          className="input-base"
          value={config.domain}
          placeholder="home.example.com"
          onChange={(e) => set("domain", e.target.value)}
        />
      </div>
      <div>
        <label className="block text-xs text-gray-400 mb-1">ssl</label>
        <select
          className="input-base"
          value={config.ssl}
          onChange={(e) => set("ssl", e.target.value as SSLMode)}
        >
          <option value="auto">auto (Let's Encrypt)</option>
          <option value="manual">manual (own certs)</option>
          <option value="none">none (HTTP only)</option>
        </select>
      </div>
      {config.ssl === "auto" && (
        <div>
          <label className="block text-xs text-gray-400 mb-1">email *</label>
          <input
            className="input-base"
            type="email"
            value={config.email}
            placeholder="admin@example.com"
            onChange={(e) => set("email", e.target.value)}
          />
        </div>
      )}
    </div>
  );
}
