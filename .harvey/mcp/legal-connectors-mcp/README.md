# Harvey Legal Connectors MCP Server (Template)
This MCP server scaffold provides starter tools for:
- PACER case lookup wiring
- Westlaw query wiring
- LexisNexis query wiring
- Case watchlist status

## Quick start
1. Create `.harvey/PACER.env` from `.harvey/PACER.env.example`.
2. Create `.harvey/LEGAL_RESEARCH.env` from `.harvey/LEGAL_RESEARCH.env.example`.
3. Install dependencies:
   - `cd .harvey/mcp/legal-connectors-mcp`
   - `npm install`
4. Start server:
   - `node server.js`

## Notes
- This is a secure template and intentionally does not bypass MFA.
- Connect each template tool to your approved provider API workflows.
