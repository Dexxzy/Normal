import React, { useState, useCallback } from "react";
import toast from "react-hot-toast";
import type { GeneratedFile, Target } from "../types";

interface Props {
  files: GeneratedFile[];
  loading: boolean;
  toml: string;
  targets: Target[];
}

export function ConfigPreview({ files, loading, toml, targets }: Props) {
  const [activeFile, setActiveFile] = useState<string | null>(null);

  const displayed = files.find(f => f.filename === (activeFile ?? files[0]?.filename)) ?? files[0] ?? null;

  const copy = useCallback(async (content: string) => {
    await navigator.clipboard.writeText(content);
    toast.success("copied");
  }, []);

  const download = useCallback(async () => {
    const res = await fetch("/api/generate/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ toml, targets }),
    });
    if (!res.ok) { toast.error("download failed"); return; }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "proxysmith-configs.zip";
    a.click();
    URL.revokeObjectURL(url);
    toast.success("proxysmith-configs.zip");
  }, [toml, targets]);

  return (
    <div className="h-full flex flex-col">
      {/* Tab bar */}
      <div className="flex items-center justify-between border-b border-surface-4 px-2 min-h-[41px] flex-shrink-0">
        <div className="flex overflow-x-auto">
          {files.map(f => (
            <button key={f.filename}
              onClick={() => setActiveFile(f.filename)}
              className={`tab-btn ${(activeFile ?? files[0]?.filename) === f.filename ? "tab-active" : "tab-inactive"}`}>
              {f.filename.split("/").pop()}
            </button>
          ))}
          {loading && !files.length && (
            <span className="px-4 py-2.5 mono text-xs text-ink-5 animate-pulse">generating…</span>
          )}
        </div>

        {displayed && (
          <div className="flex items-center gap-0.5 flex-shrink-0">
            <button className="btn-ghost text-xs mono" onClick={() => copy(displayed.content)}>copy</button>
            <button className="btn-ghost text-xs mono" onClick={download}>zip ↓</button>
          </div>
        )}
      </div>

      {/* Code */}
      <div className="flex-1 overflow-auto">
        {!displayed && !loading && (
          <div className="flex flex-col items-center justify-center h-full text-ink-5 select-none gap-2">
            <div className="mono text-3xl">{ }</div>
            <div className="text-sm">add a service to see output</div>
          </div>
        )}

        {displayed && (
          <pre className="mono text-xs text-ink-3 p-4 leading-[1.65] min-h-full">
            <HighlightedCode content={displayed.content} filename={displayed.filename} />
          </pre>
        )}
      </div>

      {/* Status bar */}
      {displayed && (
        <div className="border-t border-surface-4 px-4 py-1 flex items-center gap-4 mono text-xs text-ink-5 flex-shrink-0">
          <span>{displayed.filename}</span>
          <span className="ml-auto">{(displayed.size / 1024).toFixed(1)}kb</span>
          <span className="text-ink-5/60">#{displayed.checksum}</span>
        </div>
      )}
    </div>
  );
}

// ── Syntax highlighting ──────────────────────────────────────────────────────

function HighlightedCode({ content, filename }: { content: string; filename: string }) {
  const isNginx = filename.endsWith(".conf");
  const isYaml  = filename.endsWith(".yml") || filename.endsWith(".yaml");
  const lines   = content.split("\n");

  return (
    <>
      {lines.map((line, i) => (
        <span key={i} className="block">
          <span className="select-none text-ink-5/40 mr-5 inline-block w-7 text-right">{i + 1}</span>
          <HL line={line} nginx={isNginx} yaml={isYaml} />
        </span>
      ))}
    </>
  );
}

function HL({ line, nginx, yaml }: { line: string; nginx: boolean; yaml: boolean }) {
  const t = line.trimStart();

  if (t.startsWith("#"))  return <span className="text-ink-5/70 italic">{line}</span>;
  if (t.startsWith("---")) return <span className="text-ink-5">{line}</span>;

  if (yaml) {
    const m = line.match(/^(\s*)([\w.-]+)(\s*:\s*)(.*)$/);
    if (m) return (
      <span>
        {m[1]}<span className="text-amber-300/90">{m[2]}</span>
        <span className="text-ink-4">{m[3]}</span>
        <YamlVal v={m[4]} />
      </span>
    );
    if (t.startsWith("- ")) {
      const indent = line.slice(0, line.indexOf("- "));
      const rest   = line.slice(line.indexOf("- ") + 2);
      return <span>{indent}<span className="text-ink-4">- </span><span className="text-green-400/80">{rest}</span></span>;
    }
  }

  if (nginx) {
    if (t === "{" || t === "}") return <span className="text-ink-4">{line}</span>;
    const m = line.match(/^(\s*)(\w[\w_-]*)(\s+)(.+?)(;?\s*)$/);
    if (m) return (
      <span>
        {m[1]}<span className="text-amber-300/80">{m[2]}</span>
        {m[3]}<span className="text-green-400/80">{m[4]}</span>
        <span className="text-ink-5">{m[5]}</span>
      </span>
    );
    if (/^\S.*\{/.test(t)) return <span className="text-sky-300/80">{line}</span>;
  }

  // Caddyfile block header
  if (!yaml && !nginx && /^\S.*\{$/.test(t)) return <span className="text-sky-300/80">{line}</span>;

  return <span>{line}</span>;
}

function YamlVal({ v }: { v: string }) {
  if (!v) return null;
  if (v.startsWith('"') || v.startsWith("'")) return <span className="text-green-400/80">{v}</span>;
  if (v === "true" || v === "false")           return <span className="text-orange-400/80">{v}</span>;
  if (/^\d/.test(v))                           return <span className="text-purple-400/80">{v}</span>;
  return <span className="text-ink-2">{v}</span>;
}
