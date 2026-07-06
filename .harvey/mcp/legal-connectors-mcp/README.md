# Harvey Legal Connectors MCP Server (Template)
This MCP server scaffold provides starter tools for:
- PACER login execution (`pacer_login_run`)
- PACER watchlist sync (`pacer_watchlist_sync_run`)
- PACER case lookup templates (`pacer_case_lookup_template`)
- Legal research mode status (`legal_research_mode_status`)
- Westlaw query wiring (`westlaw_query_template`)
- LexisNexis query wiring (`lexis_query_template`)
- CourtListener query wiring (`courtlistener_search_template`)
- RECAP query wiring (`recap_search_template`)
- GovInfo query wiring (`govinfo_search_template`)
- WorldLII query wiring (`worldlii_search_template`)
- BAILII query wiring (`bailii_search_template`)
- Cornell LII query wiring (`cornell_lii_search_template`)
- CanLII query wiring (`canlii_search_template`)
- Case watchlist status (`case_watchlist_status`)

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
- Free/open-source-first routing is controlled by `LEGAL_MODE` and `ENABLE_PAID_ESCALATION`.
