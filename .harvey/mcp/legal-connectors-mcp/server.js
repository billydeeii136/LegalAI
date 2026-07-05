import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const server = new McpServer({
  name: "harvey-legal-connectors-mcp",
  version: "0.1.0",
});

const configured = (...names) => names.every((name) => Boolean(process.env[name]?.trim()));

server.tool(
  "pacer_case_lookup_template",
  {
    case_number: z.string(),
    court: z.string().default("nced"),
  },
  async ({ case_number, court }) => {
    const ready = configured("PACER_USERNAME", "PACER_PASSWORD");
    const text = ready
      ? `PACER template is configured. Next step: connect this tool to your PACER docket retrieval implementation for ${court} ${case_number}.`
      : "PACER template is not configured. Set PACER_USERNAME and PACER_PASSWORD.";
    return { content: [{ type: "text", text }] };
  }
);

server.tool(
  "westlaw_query_template",
  {
    query: z.string(),
  },
  async ({ query }) => {
    const ready = configured("WESTLAW_API_URL", "WESTLAW_API_KEY");
    const text = ready
      ? `Westlaw template is configured for query: ${query}`
      : "Westlaw template is not configured. Set WESTLAW_API_URL and WESTLAW_API_KEY.";
    return { content: [{ type: "text", text }] };
  }
);

server.tool(
  "lexis_query_template",
  {
    query: z.string(),
  },
  async ({ query }) => {
    const ready = configured("LEXIS_API_URL", "LEXIS_API_KEY");
    const text = ready
      ? `Lexis template is configured for query: ${query}`
      : "Lexis template is not configured. Set LEXIS_API_URL and LEXIS_API_KEY.";
    return { content: [{ type: "text", text }] };
  }
);

server.tool("case_watchlist_status", {}, async () => {
  return {
    content: [
      {
        type: "text",
        text: "Watchlist source: .harvey/LEGAL_CASE_WATCHLIST.yaml",
      },
    ],
  };
});

const transport = new StdioServerTransport();
await server.connect(transport);
