import React from "react";
import type { ValidationError } from "../types";

interface Props {
  value: string;
  onChange: (v: string) => void;
  errors: ValidationError[];
}

export function TomlEditor({ value, onChange, errors }: Props) {
  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-surface-4 flex-shrink-0">
        <span className="mono text-xs text-ink-4">proxysmith.toml</span>
        <span className={`mono text-xs ${errors.length > 0 ? "text-red-400" : value.trim() ? "text-green-500" : "text-ink-5"}`}>
          {errors.length > 0 ? `${errors.length} error${errors.length > 1 ? "s" : ""}` : value.trim() ? "valid" : ""}
        </span>
      </div>

      <textarea
        className="flex-1 mono text-xs bg-transparent text-ink-2 resize-none
                   focus:outline-none px-4 py-3 leading-relaxed caret-amber-400"
        value={value}
        onChange={e => onChange(e.target.value)}
        spellCheck={false}
        autoCapitalize="none"
        autoCorrect="off"
        autoComplete="off"
      />

      {errors.length > 0 && (
        <div className="border-t border-red-900/40 bg-red-950/20 px-4 py-2 flex-shrink-0 max-h-32 overflow-y-auto">
          {errors.map((e, i) => (
            <div key={i} className="mono text-xs text-red-400/90 leading-relaxed py-0.5">
              <span className="text-red-600">{e.field}</span>{" — "}{e.message}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
