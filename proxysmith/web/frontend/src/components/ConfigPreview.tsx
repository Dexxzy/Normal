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

  const current =
    files.find((f) => f.filename === activeFile) ?? files[0] ?? null;

  const copy = useCallback(async (content: string) => {
    await navigator.clipboard.writeText(content);
    toast.success("Copied to clipboard");
  }, []);

  const download = useCallback(async () => {
    const res = await fetch("/api/generate/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ toml, targets }),
    });
    if (!res.ok) {
      toast.error("Download failed");
      return;
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "proxysmith-configs.zip";
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Downloaded proxysmith-configs.zip");
  }, [toml, targets]);

  return (
    <div className="h-full flex flex-col">
      {/* Tab bar */}
      <div className="flex items-center justify-between border-b border-gray-700 px-2 min-h-[42px] flex-shrink-0">
        <div className="flex gap-1 overflow-x-auto">
          {files.map((f) => (
            <button
              key={f.filename}
              onClick={() => setActiveFile(f.filename)}
              className={`px-3 py-2 text-xs font-mono whitespace-nowrap transition-colors ${
                (activeFile ?? files[0]?.filename) === f.filename
                  ? "tab-active"
                  : "tab-inactive"
              }`}
            >
              {f.filename.split("/").pop()}
            </button>
          ))}
          {loading && (
            <span className="px-3 py-2 text-xs text-gray-500 animate-pulse">
              generating…
            </span>
          )}
        </div>

        {files.length > 0 && (
          <div className="flex items-center gap-1 ml-2 flex-shrink-0">
            {current && (
              <button
                className="btn-ghost text-xs"
                onClick={() => copy(current.content)}
                title="Copy to clipboard"
              >
                Copy
              </button>
            )}
            <button
              className="btn-ghost text-xs"
              onClick={download}
              title="Download all as ZIP"
            >
              ↓ ZIP
            </button>
          </div>
        )}
      </div>

      {/* Code view */}
      <div className="flex-1 overflow-auto p-4">
        {!loading && files.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-gray-600 select-none">
            <div className="text-4xl mb-3">⚙</div>
            <div className="text-sm">
              Config preview will appear here
            </div>
            <div className="text-xs mt-1">
              Edit your services and the output updates live
            </div>
          </div>
        )}

        {current && (
          <pre className="font-mono text-xs text-gray-300 whitespace-pre leading-relaxed">
            <SyntaxHighlight content={current.content} filename={current.filename} />
          </pre>
        )}
      </div>

      {/* Footer stats */}
      {current && (
        <div className="border-t border-gray-700 px-4 py-1.5 flex items-center gap-4 text-xs text-gray-500 flex-shrink-0">
          <span>{current.filename}</span>
          <span>{current.size.toLocaleString()} bytes</span>
          <span className="font-mono">sha:{current.checksum}</span>
        </div>
      )}
    </div>
  );
}

// ---- Minimal syntax highlighter (no dependencies) ----

function SyntaxHighlight({
  content,
  filename,
}: {
  content: string;
  filename: string;
}) {
  const isNginx = filename.endsWith(".conf");
  const isYaml =
    filename.endsWith(".yml") || filename.endsWith(".yaml");
  const isCaddy = filename === "Caddyfile" || filename.endsWith("/Caddyfile");

  const lines = content.split("\n");

  return (
    <>
      {lines.map((line, i) => (
        <span key={i}>
          <LineNum n={i + 1} />
          <HighlightLine line={line} isNginx={isNginx} isYaml={isYaml} />
          {"\n"}
        </span>
      ))}
    </>
  );
}

function LineNum({ n }: { n: number }) {
  return (
    <span className="select-none text-gray-600 mr-4 inline-block w-7 text-right">
      {n}
    </span>
  );
}

function HighlightLine({
  line,
  isNginx,
  isYaml,
}: {
  line: string;
  isNginx: boolean;
  isYaml: boolean;
}) {
  const trimmed = line.trimStart();

  // Comments
  if (trimmed.startsWith("#")) {
    return <span className="text-gray-500">{line}</span>;
  }

  // YAML key: value
  if (isYaml) {
    const m = line.match(/^(\s*)([\w-]+)(\s*:\s*)(.*)$/);
    if (m) {
      return (
        <span>
          <span>{m[1]}</span>
          <span className="text-blue-300">{m[2]}</span>
          <span className="text-gray-400">{m[3]}</span>
          <ValueSpan value={m[4]} />
        </span>
      );
    }
    // list item
    if (trimmed.startsWith("- ")) {
      return (
        <span>
          <span className="text-gray-400">{line.slice(0, line.indexOf("- ") + 2)}</span>
          <span className="text-green-300">{line.slice(line.indexOf("- ") + 2)}</span>
        </span>
      );
    }
  }

  // Nginx directive
  if (isNginx) {
    const m = line.match(/^(\s*)(\w[\w_-]*)(\s+)(.+?)(;?)(\s*)$/);
    if (m && !trimmed.startsWith("{") && !trimmed.startsWith("}")) {
      return (
        <span>
          <span>{m[1]}</span>
          <span className="text-yellow-300">{m[2]}</span>
          <span>{m[3]}</span>
          <span className="text-green-300">{m[4]}</span>
          <span className="text-gray-400">{m[5]}</span>
        </span>
      );
    }
    if (trimmed === "{" || trimmed === "}") {
      return <span className="text-gray-400">{line}</span>;
    }
  }

  // Caddyfile block header (fqdn { )
  if (!isYaml && !isNginx) {
    if (/^\S.*\{$/.test(trimmed)) {
      return <span className="text-cyan-300">{line}</span>;
    }
  }

  return <span>{line}</span>;
}

function ValueSpan({ value }: { value: string }) {
  if (value.startsWith('"') || value.startsWith("'")) {
    return <span className="text-green-300">{value}</span>;
  }
  if (value === "true" || value === "false") {
    return <span className="text-orange-300">{value}</span>;
  }
  if (/^\d/.test(value)) {
    return <span className="text-purple-300">{value}</span>;
  }
  return <span className="text-gray-200">{value}</span>;
}
