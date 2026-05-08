type LogLevel = "info" | "warn" | "error" | "debug";

interface LogEntry {
  ts: string;
  level: LogLevel;
  ctx: string;
  msg: string;
  data?: unknown;
}

const MAX_ENTRIES = 200;
const _buffer: LogEntry[] = [];

function write(level: LogLevel, ctx: string, msg: string, data?: unknown) {
  const entry: LogEntry = { ts: new Date().toISOString(), level, ctx, msg, data };
  _buffer.push(entry);
  if (_buffer.length > MAX_ENTRIES) _buffer.shift();

  const prefix = `[${entry.ts.slice(11, 19)}][${ctx}]`;
  if (level === "error") console.error(prefix, msg, data ?? "");
  else if (level === "warn") console.warn(prefix, msg, data ?? "");
  else if (process.env.NODE_ENV !== "production") console.log(prefix, msg, data ?? "");
}

export const logger = {
  info: (ctx: string, msg: string, data?: unknown) => write("info", ctx, msg, data),
  warn: (ctx: string, msg: string, data?: unknown) => write("warn", ctx, msg, data),
  error: (ctx: string, msg: string, data?: unknown) => write("error", ctx, msg, data),
  debug: (ctx: string, msg: string, data?: unknown) => write("debug", ctx, msg, data),
  getLogs: () => [..._buffer],
  getErrorLogs: () => _buffer.filter((e) => e.level === "error" || e.level === "warn"),
  exportJson: () => JSON.stringify(_buffer, null, 2),
};
