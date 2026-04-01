import React, { useState, useEffect, useCallback } from "react";
import toast from "react-hot-toast";
import { api } from "./api";
import { useDebounce } from "./hooks/useDebounce";
import { GlobalForm } from "./components/GlobalForm";
import { ServiceForm } from "./components/ServiceForm";
import { ConfigPreview } from "./components/ConfigPreview";
import { TomlEditor } from "./components/TomlEditor";
import type {
  GlobalConfig,
  ServiceConfig,
  GeneratedFile,
  ValidationError,
  Target,
} from "./types";
import {
  DEFAULT_GLOBAL,
  DEFAULT_SERVICE,
  EXAMPLE_TOML,
} from "./types";

// ---- TOML serializer (simple, covers our schema) ----
function toToml(global_: GlobalConfig, services: ServiceConfig[]): string {
  const lines: string[] = [];
  lines.push("[global]");
  lines.push(`domain = "${global_.domain}"`);
  lines.push(`ssl    = "${global_.ssl}"`);
  if (global_.ssl === "auto" && global_.email)
    lines.push(`email  = "${global_.email}"`);
  lines.push("");

  for (const svc of services) {
    lines.push("[[service]]");
    if (svc.name) lines.push(`name      = "${svc.name}"`);
    if (svc.host) lines.push(`host      = "${svc.host}"`);
    lines.push(`port      = ${svc.port}`);
    if (svc.subdomain) lines.push(`subdomain = "${svc.subdomain}"`);
    if (svc.websocket) lines.push(`websocket = true`);
    if (svc.auth !== "none") lines.push(`auth      = "${svc.auth}"`);
    if (svc.rate_limit) lines.push(`rate_limit = "${svc.rate_limit}"`);
    if (svc.max_upload) lines.push(`max_upload = "${svc.max_upload}"`);
    if (svc.cors) lines.push(`cors = true`);
    if (Object.keys(svc.headers).length > 0) {
      const hEntries = Object.entries(svc.headers)
        .map(([k, v]) => `${k} = "${v}"`)
        .join(", ");
      lines.push(`headers = { ${hEntries} }`);
    }
    lines.push("");
  }

  return lines.join("\n");
}

type Mode = "visual" | "toml";
type PanelTab = "nginx" | "caddy" | "traefik";

const PANEL_TARGETS: PanelTab[] = ["nginx", "caddy", "traefik"];

export default function App() {
  // --- editor state ---
  const [mode, setMode] = useState<Mode>("visual");
  const [global_, setGlobal] = useState<GlobalConfig>(DEFAULT_GLOBAL);
  const [services, setServices] = useState<ServiceConfig[]>([]);
  const [rawToml, setRawToml] = useState(EXAMPLE_TOML);

  // --- output state ---
  const [activePanel, setActivePanel] = useState<PanelTab>("nginx");
  const [filesByTarget, setFilesByTarget] = useState<
    Record<PanelTab, GeneratedFile[]>
  >({ nginx: [], caddy: [], traefik: [] });
  const [loading, setLoading] = useState(false);
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([]);

  // Compute TOML from visual form
  const visualToml = toToml(global_, services);
  const effectiveToml = mode === "visual" ? visualToml : rawToml;

  const debouncedToml = useDebounce(effectiveToml, 600);

  // Load example on mount
  useEffect(() => {
    setRawToml(EXAMPLE_TOML);
  }, []);

  // Live generation on TOML change
  useEffect(() => {
    if (!debouncedToml.trim()) return;

    let cancelled = false;

    const run = async () => {
      setLoading(true);

      // Validate first
      try {
        const vr = await api.validate(debouncedToml);
        if (!cancelled) {
          setValidationErrors(vr.errors);
        }
        if (!vr.valid) {
          setLoading(false);
          return;
        }
      } catch {
        setLoading(false);
        return;
      }

      // Generate all three targets simultaneously
      try {
        const results = await Promise.all(
          PANEL_TARGETS.map((t) => api.generate(debouncedToml, [t]))
        );
        if (!cancelled) {
          const next: Record<PanelTab, GeneratedFile[]> = {
            nginx: [],
            caddy: [],
            traefik: [],
          };
          PANEL_TARGETS.forEach((t, i) => {
            next[t] = results[i].files;
          });
          setFilesByTarget(next);
        }
      } catch (err) {
        if (!cancelled) {
          toast.error("Generation failed — check your config");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    run();
    return () => {
      cancelled = true;
    };
  }, [debouncedToml]);

  // --- handlers ---
  const addService = () =>
    setServices((s) => [...s, { ...DEFAULT_SERVICE }]);

  const updateService = (i: number, svc: ServiceConfig) =>
    setServices((s) => s.map((x, j) => (j === i ? svc : x)));

  const removeService = (i: number) =>
    setServices((s) => s.filter((_, j) => j !== i));

  const loadExample = useCallback(() => {
    if (mode === "toml") {
      setRawToml(EXAMPLE_TOML);
    } else {
      setRawToml(EXAMPLE_TOML);
      setMode("toml");
      toast("Switched to TOML mode with example loaded");
    }
  }, [mode]);

  const currentFiles = filesByTarget[activePanel];

  return (
    <div className="h-screen flex flex-col bg-gray-950 overflow-hidden">
      {/* ── Header ── */}
      <header className="flex items-center justify-between px-5 py-3 border-b border-gray-800 flex-shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-lg font-bold text-white tracking-tight">
            Proxy<span className="text-brand-400">Smith</span>
          </span>
          <span className="text-xs text-gray-500 font-mono hidden sm:block">
            reverse proxy config generator
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Mode toggle */}
          <div className="flex bg-gray-800 rounded-lg p-0.5">
            <button
              className={`px-3 py-1 text-xs rounded-md transition-colors ${
                mode === "visual"
                  ? "bg-gray-700 text-white"
                  : "text-gray-400 hover:text-gray-200"
              }`}
              onClick={() => setMode("visual")}
            >
              Visual
            </button>
            <button
              className={`px-3 py-1 text-xs rounded-md transition-colors ${
                mode === "toml"
                  ? "bg-gray-700 text-white"
                  : "text-gray-400 hover:text-gray-200"
              }`}
              onClick={() => setMode("toml")}
            >
              TOML
            </button>
          </div>

          <button className="btn-ghost text-xs" onClick={loadExample}>
            Load example
          </button>

          <a
            href="https://github.com/dexxzy/proxysmith"
            target="_blank"
            rel="noopener noreferrer"
            className="btn-ghost text-xs"
          >
            GitHub
          </a>
        </div>
      </header>

      {/* ── Main layout ── */}
      <div className="flex flex-1 overflow-hidden">
        {/* ── Left panel: editor ── */}
        <div className="w-[45%] flex-shrink-0 border-r border-gray-800 flex flex-col overflow-hidden">
          {mode === "visual" ? (
            <div className="flex-1 overflow-y-auto p-4">
              {/* Global */}
              <section className="mb-5">
                <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
                  Global
                </h2>
                <GlobalForm config={global_} onChange={setGlobal} />
              </section>

              {/* Services */}
              <section>
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Services
                    <span className="ml-2 bg-gray-700 text-gray-300 rounded px-1.5 py-0.5 text-xs font-mono normal-case">
                      {services.length}
                    </span>
                  </h2>
                  <button className="btn-primary py-1 px-3 text-xs" onClick={addService}>
                    + Add service
                  </button>
                </div>

                {services.length === 0 && (
                  <div className="text-center py-10 text-gray-600 text-sm">
                    <div className="text-3xl mb-2">＋</div>
                    No services yet — click "Add service"
                  </div>
                )}

                {services.map((svc, i) => (
                  <ServiceForm
                    key={i}
                    service={svc}
                    index={i}
                    onUpdate={updateService}
                    onRemove={removeService}
                  />
                ))}
              </section>
            </div>
          ) : (
            <div className="flex-1 code-block border-none rounded-none overflow-hidden flex flex-col">
              <TomlEditor
                value={rawToml}
                onChange={setRawToml}
                errors={validationErrors}
              />
            </div>
          )}
        </div>

        {/* ── Right panel: generated output ── */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Target tabs */}
          <div className="flex items-center gap-1 px-4 border-b border-gray-800 flex-shrink-0">
            {PANEL_TARGETS.map((t) => (
              <button
                key={t}
                onClick={() => setActivePanel(t)}
                className={`px-4 py-2.5 text-sm font-medium transition-colors ${
                  activePanel === t ? "tab-active" : "tab-inactive"
                }`}
              >
                {t.charAt(0).toUpperCase() + t.slice(1)}
                {filesByTarget[t].length > 0 && (
                  <span className="ml-1.5 text-xs text-gray-500">
                    ({filesByTarget[t].length})
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Preview */}
          <div className="flex-1 overflow-hidden code-block border-none rounded-none">
            <ConfigPreview
              files={currentFiles}
              loading={loading}
              toml={effectiveToml}
              targets={[activePanel]}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
