export type SSLMode = "auto" | "manual" | "none";
export type AuthMode = "none" | "basic" | "forward";
export type Target = "nginx" | "caddy" | "traefik";

export interface ServiceConfig {
  name: string;
  host: string;
  port: number;
  subdomain: string;
  websocket: boolean;
  auth: AuthMode;
  rate_limit: string;
  max_upload: string;
  cors: boolean;
  headers: Record<string, string>;
}

export interface GlobalConfig {
  domain: string;
  ssl: SSLMode;
  email: string;
}

export interface ProxySmithConfig {
  global: GlobalConfig;
  services: ServiceConfig[];
}

export interface ValidationError {
  field: string;
  message: string;
}

export interface ValidateResponse {
  valid: boolean;
  errors: ValidationError[];
  service_count: number;
  domain: string;
  ssl_mode: string;
}

export interface GeneratedFile {
  filename: string;
  content: string;
  size: number;
  checksum: string;
}

export interface GenerateResponse {
  files: GeneratedFile[];
}

export interface ServiceSummary {
  name: string;
  fqdn: string;
  host: string;
  port: number;
  features: string[];
}

export interface ConfigSummaryResponse {
  domain: string;
  ssl_mode: string;
  email: string | null;
  services: ServiceSummary[];
}

export const DEFAULT_SERVICE: ServiceConfig = {
  name: "",
  host: "",
  port: 80,
  subdomain: "",
  websocket: false,
  auth: "none",
  rate_limit: "",
  max_upload: "",
  cors: false,
  headers: {},
};

export const DEFAULT_GLOBAL: GlobalConfig = {
  domain: "home.example.com",
  ssl: "auto",
  email: "admin@example.com",
};

export const EXAMPLE_TOML = `[global]
domain = "home.example.com"
ssl    = "auto"
email  = "admin@example.com"

[[service]]
name      = "plex"
host      = "192.168.1.50"
port      = 32400
subdomain = "plex"
websocket = true

[[service]]
name       = "immich"
host       = "192.168.1.50"
port       = 2283
subdomain  = "photos"
max_upload = "10G"

[[service]]
name       = "ollama"
host       = "192.168.1.50"
port       = 11434
subdomain  = "llm"
auth       = "basic"
rate_limit = "60/min"

[[service]]
name      = "homepage"
host      = "192.168.1.50"
port      = 3000
subdomain = "dash"
`;
