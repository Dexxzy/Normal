import React, { useState, useEffect, useCallback } from "react";
import toast from "react-hot-toast";
import { api } from "./api";
import { useDebounce } from "./hooks/useDebounce";
import { GlobalForm } from "./components/GlobalForm";
import { ServiceForm } from "./components/ServiceForm";
import { ConfigPreview } from "./components/ConfigPreview";
import { TomlEditor } from "./components/TomlEditor";
import type {
  GlobalConfig, ServiceConfig, GeneratedFile, ValidationError, Target,
} from "./types";
import { DEFAULT_GLOBAL, DEFAULT_SERVICE, EXAMPLE_TOML } from "./types";

// ── TOML serializer ──────────────────────────────────────────────────────────

function toToml(g: GlobalConfig, services: ServiceConfig[]): string {
  const L: string[] = ["[global]"];
  L.push(`domain = "${g.domain}"`);
  L.push(`ssl    = "${g.ssl}"`);
  if (g.ssl === "auto" && g.email) L.push(`email  = "${g.email}"`);
  L.push("");
  for (const s of services) {
    L.push("[[service]]");
    if (s.name)      L.push(`name      = "${s.name}"`);
    if (s.host)      L.push(`host      = "${s.host}"`);
    L.push(`port      = ${s.port}`);
    if (s.subdomain) L.push(`subdomain = "${s.subdomain}"`);
    if (s.websocket) L.push("websocket = true");
    if (s.auth !== "none") L.push(`auth      = "${s.auth}"`);
    if (s.rate_limit) L.push(`rate_limit = "${s.rate_limit}"`);
    if (s.max_upload) L.push(`max_upload = "${s.max_upload}"`);
    if (s.cors)       L.push("cors = true");
    const hdrs = Object.entries(s.headers);
    if (hdrs.length) L.push(`headers = { ${hdrs.map(([k,v]) => `${k} = "${v}"`).join(", ")} }`);
    L.push("");
  }
  return L.join("\n");
}

// ── Types ────────────────────────────────────────────────────────────────────

type Mode  = "visual" | "toml";
type Panel = "nginx" | "caddy" | "traefik";
const PANELS: Panel[] = ["nginx", "caddy", "traefik"];

// ── Component ────────────────────────────────────────────────────────────────

export default function App() {
  // Editor
  const [mode, setMode]       = useState<Mode>("toml");
  const [rawToml, setRawToml] = useState(EXAMPLE_TOML);
  const [global_, setGlobal]  = useState<GlobalConfig>(DEFAULT_GLOBAL);
  const [services, setServices] = useState<ServiceConfig[]>([]);

  // Output
  const [panel, setPanel]     = useState<Panel>("nginx");
  const [files, setFiles]     = useState<Record<Panel, GeneratedFile[]>>({ nginx: [], caddy: [], traefik: [] });
  const [loading, setLoading] = useState(false);
  const [errors, setErrors]   = useState<ValidationError[]>([]);

  const effectiveToml  = mode === "visual" ? toToml(global_, services) : rawToml;
  const debouncedToml  = useDebounce(effectiveToml, 500);

  // Live generation
  useEffect(() => {
    if (!debouncedToml.trim()) return;
    let dead = false;
    const run = async () => {
      setLoading(true);
      try {
        const vr = await api.validate(debouncedToml);
        if (dead) return;
        setErrors(vr.errors);
        if (!vr.valid) { setLoading(false); return; }

        const results = await Promise.all(PANELS.map(t => api.generate(debouncedToml, [t])));
        if (dead) return;
        const next = { nginx: [], caddy: [], traefik: [] } as Record<Panel, GeneratedFile[]>;
        PANELS.forEach((t, i) => { next[t] = results[i].files; });
        setFiles(next);
      } catch {
        if (!dead) toast.error("generation failed");
      } finally {
        if (!dead) setLoading(false);
      }
    };
    run();
    return () => { dead = true; };
  }, [debouncedToml]);

  const addService    = () => setServices(s => [...s, { ...DEFAULT_SERVICE }]);
  const updateService = (i: number, svc: ServiceConfig) => setServices(s => s.map((x, j) => j === i ? svc : x));
  const removeService = (i: number) => setServices(s => s.filter((_, j) => j !== i));

  const currentFiles = files[panel];

  return (
    <div className="h-screen flex flex-col bg-surface-0 overflow-hidden text-ink-1">

      {/* ── Top bar ── */}
      <header className="flex items-center justify-between px-5 h-12 border-b border-surface-4 flex-shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            {/* Small hammer icon — inline svg, no icon lib */}
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="text-amber-400">
              <path d="M9.5 2L14 6.5L7 13.5L2.5 9L9.5 2Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round"/>
              <path d="M12 4L13.5 2.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
              <path d="M2 14L4 12" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
            </svg>
            <span className="text-sm font-semibold tracking-tight">
              proxy<span className="text-amber-400">smith</span>
            </span>
          </div>
          <span className="text-xs text-ink-4 hidden sm:block">nginx · caddy · traefik</span>
        </div>

        <div className="flex items-center gap-1">
          {/* Mode toggle */}
          <div className="flex bg-surface-3 rounded-lg p-0.5 border border-surface-4">
            {(["visual", "toml"] as Mode[]).map(m => (
              <button key={m} onClick={() => setMode(m)}
                className={`mono text-xs px-3 py-1 rounded-md transition-colors ${
                  mode === m ? "bg-surface-4 text-ink-1" : "text-ink-4 hover:text-ink-2"
                }`}>
                {m}
              </button>
            ))}
          </div>
          <a href="https://github.com/dexxzy/proxysmith" target="_blank" rel="noopener noreferrer"
            className="btn-ghost mono text-xs ml-1">
            github
          </a>
        </div>
      </header>

      {/* ── Body ── */}
      <div className="flex flex-1 overflow-hidden">

        {/* ── Left: editor ── */}
        <div className="w-[44%] min-w-[320px] flex-shrink-0 border-r border-surface-4 flex flex-col overflow-hidden">

          {mode === "toml" ? (
            <div className="flex-1 overflow-hidden flex flex-col">
              <TomlEditor value={rawToml} onChange={setRawToml} errors={errors} />
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto p-4 space-y-5">
              {/* Global */}
              <section>
                <SectionLabel>global</SectionLabel>
                <GlobalForm config={global_} onChange={setGlobal} />
              </section>

              {/* Services */}
              <section>
                <div className="flex items-center justify-between mb-3">
                  <SectionLabel>
                    services
                    {services.length > 0 && (
                      <span className="mono text-xs text-ink-5 font-normal ml-1.5">{services.length}</span>
                    )}
                  </SectionLabel>
                  <button className="btn-primary text-xs px-3 py-1.5" onClick={addService}>
                    + service
                  </button>
                </div>

                {services.length === 0 && (
                  <EmptyServices onAdd={addService} />
                )}

                {services.map((svc, i) => (
                  <ServiceForm key={i} service={svc} index={i}
                    onUpdate={updateService} onRemove={removeService} />
                ))}
              </section>
            </div>
          )}
        </div>

        {/* ── Right: output ── */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Target tabs */}
          <div className="flex items-center border-b border-surface-4 px-2 flex-shrink-0">
            {PANELS.map(p => (
              <button key={p} onClick={() => setPanel(p)}
                className={`tab-btn ${panel === p ? "tab-active" : "tab-inactive"}`}>
                {p}
                {files[p].length > 0 && (
                  <span className="ml-1 text-[10px] text-ink-5">
                    ×{files[p].length}
                  </span>
                )}
              </button>
            ))}
            {loading && (
              <span className="ml-auto mr-2 mono text-xs text-ink-5 animate-pulse">
                …
              </span>
            )}
          </div>

          <div className="flex-1 overflow-hidden">
            <ConfigPreview
              files={currentFiles}
              loading={loading}
              toml={effectiveToml}
              targets={[panel]}
            />
          </div>
        </div>
      </div>

      {/* ── Footer ── */}
      <footer className="border-t border-surface-4 px-5 py-2 flex items-center justify-between flex-shrink-0">
        <span className="mono text-xs text-ink-5">
          pip install proxysmith
        </span>
        <span className="mono text-xs text-ink-5">
          proxysmith generate --target nginx
        </span>
      </footer>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="mono text-xs text-ink-4 uppercase tracking-widest mb-3 flex items-center gap-2">
      {children}
    </h2>
  );
}

function EmptyServices({ onAdd }: { onAdd: () => void }) {
  return (
    <div className="border border-dashed border-surface-5 rounded-lg p-6 text-center">
      <p className="text-sm text-ink-4 mb-1">no services defined</p>
      <p className="text-xs text-ink-5 mb-4">
        each service becomes a server block, Caddyfile site, or Traefik router
      </p>
      <button className="btn-primary text-xs px-4 py-2" onClick={onAdd}>
        add first service
      </button>
    </div>
  );
}
