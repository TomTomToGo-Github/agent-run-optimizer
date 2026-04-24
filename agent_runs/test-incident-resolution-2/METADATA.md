# incident-resolution

AI agent resolves a production CPU-spike incident using search, log-reading, and metrics tools

**Created:** 2026-04-23  
**Tags:** `incident-response`, `demo`

---

## Nodes

| ID | Type | Label | Required Step | User-marked |
|---|---|:---|:---:|:---:|
| llm-initial | llm | Analyze Incident | ✓ |  |
| tool-search | tool | Search Alerts |  |  |
| tool-read-logs | tool | Read Log Files |  |  |
| llm-resolve | llm | Generate Resolution | ✓ |  |
| tool-apply-fix | tool | Apply Fix |  |  |
| llm-verify | llm | Verify Resolution | ✓ |  |
| tool-check-metrics | tool | Check Metrics |  |  |
| tool-validate-logs | tool | Validate Log Entry |  |  |
| llm-assess | llm | Assess Finding |  |  |
| tool-search-refined | tool | Refined Search |  |  |
| llm-correlate | llm | Correlate Results |  |  |
| llm-deep-analyze | llm | Deep Analysis |  |  |

---

## Runs

| Run | Outcome | Duration | Steps |
|---|---|---|---|
| [run-001](run-001.yaml) | ✅ success | 5.8s | 6 |
| [run-002](run-002.yaml) | ✅ success | 6.1s | 6 |
| [run-003](run-003.yaml) | ⚠️ partial | 12.8s | 10 |
