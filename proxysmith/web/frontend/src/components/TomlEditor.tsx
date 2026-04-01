import React, { useRef, useEffect } from "react";
import type { ValidationError } from "../types";

interface Props {
  value: string;
  onChange: (v: string) => void;
  errors: ValidationError[];
}

export function TomlEditor({ value, onChange, errors }: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Sync scroll between textarea and highlight layer if desired
  // For now, a plain textarea with line numbers is sufficient.

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-700 flex-shrink-0">
        <span className="text-xs text-gray-400 font-mono">proxysmith.toml</span>
        {errors.length > 0 && (
          <span className="text-xs text-red-400">
            {errors.length} error{errors.length > 1 ? "s" : ""}
          </span>
        )}
        {errors.length === 0 && value.trim() && (
          <span className="text-xs text-green-400">valid</span>
        )}
      </div>

      <textarea
        ref={textareaRef}
        className="flex-1 font-mono text-xs bg-transparent text-gray-200 resize-none
                   focus:outline-none p-4 leading-relaxed"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        spellCheck={false}
        autoCapitalize="none"
        autoCorrect="off"
      />

      {errors.length > 0 && (
        <div className="border-t border-red-900/50 bg-red-950/30 px-4 py-2 flex-shrink-0 max-h-28 overflow-y-auto">
          {errors.map((e, i) => (
            <div key={i} className="text-xs text-red-400 font-mono leading-relaxed">
              <span className="text-red-600">{e.field}</span>
              {" — "}
              {e.message}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
