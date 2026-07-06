import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { execFile } from "node:child_process";
import fs from "node:fs/promises";
import path from "node:path";
import { promisify } from "node:util";
import { z } from "zod";

const execFileAsync = promisify(execFile);
const harveyRoot = process.env.HARVEY_ROOT?.trim() || path.resolve(process.cwd(), ".harvey");
const watchlistPath = process.env.HARVEY_WATCHLIST_PATH?.trim() || path.join(harveyRoot, "LEGAL_CASE_WATCHLIST.yaml");
const runtimeDir = path.join(harveyRoot, "runtime");
const sessionPath = process.env.PACER_SESSION_PATH?.trim() || path.join(runtimeDir, "pacer_session.json");
const syncReportPath =
  process.env.PACER_CASE_SYNC_REPORT_PATH?.trim() || path.join(runtimeDir, "pacer_case_sync_report.json");
const storageStatePath = process.env.PACER_STORAGE_STATE_PATH?.trim() || path.join(runtimeDir, "pacer_storage_state.json");

const server = new McpServer({
  name: "harvey-legal-connectors-mcp",
  version: "0.3.0",
});

const textPayload = (text) => ({ content: [{ type: "text", text }] });

async function runPython(scriptName, args = []) {
  const scriptPath = path.join(harveyRoot, "scripts", scriptName);
  const { stdout, stderr } = await execFileAsync("python3", [scriptPath, ...args], {
    env: process.env,
    maxBuffer: 10 * 1024 * 1024,
  });
  return { stdout: stdout?.trim() ?? "", stderr: stderr?.trim() ?? "", scriptPath };
}

async function runProviderTemplate(provider, query) {
  const result = await runPython("provider_query_template.py", ["--provider", provider, "--query", query]);
  return result.stdout || result.stderr || `No output from ${provider} template.`;
}

function registerProviderTemplateTool(toolName, provider, fallbackText) {
  server.tool(
    toolName,
    {
      query: z.string(),
    },
    async ({ query }) => {
      const output = await runProviderTemplate(provider, query);
      return textPayload(output || fallbackText);
    }
  );
}

async function readIfExists(filePath) {
  try {
    return await fs.readFile(filePath, "utf8");
  } catch {
    return null;
  }
}

server.tool(
  "pacer_login_run",
  {
    mode: z.enum(["auto", "browser", "requests"]).default("auto"),
    mfa_timeout_seconds: z.number().int().positive().default(300),
  },
  async ({ mode, mfa_timeout_seconds }) => {
    await fs.mkdir(runtimeDir, { recursive: true });
    const result = await runPython("pacer_login_template.py", [
      "--watchlist",
      watchlistPath,
      "--session-out",
      sessionPath,
      "--state-out",
      storageStatePath,
      "--mode",
      mode,
      "--mfa-timeout-seconds",
      String(mfa_timeout_seconds),
    ]);
    const sessionRaw = await readIfExists(sessionPath);
    const session = sessionRaw ? JSON.parse(sessionRaw) : {};
    return textPayload(
      JSON.stringify(
        {
          script: result.scriptPath,
          stdout: result.stdout,
          stderr: result.stderr,
          session_path: sessionPath,
          session_status: session.login_status ?? "unknown",
          transport: session.transport ?? "unknown",
        },
        null,
        2
      )
    );
  }
);

server.tool("pacer_watchlist_sync_run", {}, async () => {
  await fs.mkdir(runtimeDir, { recursive: true });
  const result = await runPython("pacer_case_sync.py", [
    "--watchlist",
    watchlistPath,
    "--session-in",
    sessionPath,
    "--report-out",
    syncReportPath,
  ]);
  const report = await readIfExists(syncReportPath);
  return textPayload(
    JSON.stringify(
      {
        script: result.scriptPath,
        stdout: result.stdout,
        stderr: result.stderr,
        report_path: syncReportPath,
        report_preview: report ? JSON.parse(report) : null,
      },
      null,
      2
    )
  );
});

server.tool(
  "pacer_case_lookup_template",
  {
    case_number: z.string(),
    court: z.string().default("nced"),
  },
  async ({ case_number, court }) => {
    const reportRaw = await readIfExists(syncReportPath);
    if (!reportRaw) {
      return textPayload(
        `No sync report found at ${syncReportPath}. Run pacer_login_run and pacer_watchlist_sync_run first.`
      );
    }
    const report = JSON.parse(reportRaw);
    const matches = (report.queued_pacer_queries || []).filter(
      (entry) => entry.case_number === case_number && entry.court.toLowerCase() === court.toLowerCase()
    );
    return textPayload(
      JSON.stringify(
        {
          case_number,
          court,
          matches,
          note: "Template output. Bind this to your docket retrieval implementation.",
        },
        null,
        2
      )
    );
  }
);

server.tool("legal_research_mode_status", {}, async () => {
  const providerEnvVars = {
    westlaw: "WESTLAW_API_URL",
    lexisnexis: "LEXIS_API_URL",
    courtlistener: "COURTLISTENER_API_URL",
    recap: "RECAP_API_URL",
    govinfo: "GOVINFO_API_URL",
    worldlii: "WORLDLII_SEARCH_URL",
    bailii: "BAILII_SEARCH_URL",
    cornell_lii: "CORNELL_LII_SEARCH_URL",
    canlii: "CANLII_API_URL",
  };

  const configuredProviders = Object.entries(providerEnvVars)
    .filter(([, envVar]) => Boolean(process.env[envVar]?.trim()))
    .map(([provider]) => provider);

  return textPayload(
    JSON.stringify(
      {
        legal_mode: process.env.LEGAL_MODE || "zero_byok_free_open",
        enable_paid_escalation: process.env.ENABLE_PAID_ESCALATION || "0",
        pacer_billing_guard_enabled: process.env.PACER_BILLING_GUARD_ENABLED || "1",
        configured_provider_count: configuredProviders.length,
        configured_providers: configuredProviders,
      },
      null,
      2
    )
  );
});

registerProviderTemplateTool("westlaw_query_template", "westlaw", "No output from Westlaw template.");
registerProviderTemplateTool("lexis_query_template", "lexis", "No output from Lexis template.");
registerProviderTemplateTool(
  "courtlistener_search_template",
  "courtlistener",
  "No output from CourtListener template."
);
registerProviderTemplateTool("recap_search_template", "recap", "No output from RECAP template.");
registerProviderTemplateTool("govinfo_search_template", "govinfo", "No output from GovInfo template.");
registerProviderTemplateTool("worldlii_search_template", "worldlii", "No output from WorldLII template.");
registerProviderTemplateTool("bailii_search_template", "bailii", "No output from BAILII template.");
registerProviderTemplateTool(
  "cornell_lii_search_template",
  "cornell_lii",
  "No output from Cornell LII template."
);
registerProviderTemplateTool("canlii_search_template", "canlii", "No output from CanLII template.");

server.tool("case_watchlist_status", {}, async () => {
  const watchlistRaw = await readIfExists(watchlistPath);
  const sessionRaw = await readIfExists(sessionPath);
  const syncRaw = await readIfExists(syncReportPath);
  return textPayload(
    JSON.stringify(
      {
        watchlist_path: watchlistPath,
        watchlist_present: Boolean(watchlistRaw),
        session_path: sessionPath,
        session_present: Boolean(sessionRaw),
        sync_report_path: syncReportPath,
        sync_report_present: Boolean(syncRaw),
      },
      null,
      2
    )
  );
});

const transport = new StdioServerTransport();
await server.connect(transport);
