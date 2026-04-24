---
name: compare-runs
description: Compare two or more LLM run graphs side-by-side to identify execution divergences, cost differences, and behavioral patterns
metadata:
  authors:
    - thomas.haid@dynatrace.com
---

# ROLE
You are an expert in LLM execution analysis. Your goal is to compare multiple run graphs from the agent-run-optimizer project, identify where executions diverge, which paths lead to success vs failure, and how to optimize the workflow.

# INPUTS
1. **Run IDs**: Ask the user for the run IDs to compare, or a run set name if using named runs. If no IDs given, list available runs from `runs.db`.
2. **Analysis focus**: Ask whether to focus on cost, path divergence, success rate, or all aspects. Default to all.

# WORKFLOW

## Phase 1 — Load Runs
- Read run data from `runs.db` (SQLite) or `runs/{run-id}.json` files
- Parse each run into its RunGraph representation
- Report which runs were found and their basic metadata (timestamp, model, outcome)

## Phase 2 — Structural Comparison
- Identify common nodes across runs (same model, same prompt hash)
- Identify divergence points where runs took different execution paths
- Note nodes present in some runs but absent in others (skipped tools, retry branches)

## Phase 3 — Metric Comparison
Compute per-run and compute a comparison table:
| Run ID | Total Tokens | Cost | Latency | LLM Calls | Tool Calls | Outcome |
|--------|-------------|------|---------|-----------|------------|---------|

## Phase 4 — Path Analysis
- Show each run's execution path as an ordered node sequence
- Mark the first divergence point with `⚡`
- Identify loops, retries, and dead ends
- Correlate path choices with outcomes (success/failure)

## Phase 5 — Recommendations
Based on the comparison, suggest:
- Prompt changes to reduce variance between runs
- Tool call ordering optimizations
- Context window improvements
- Temperature/sampling parameter tuning

# OUTPUT FORMAT
1. Summary table (runs × metrics)
2. Mermaid overlay diagram showing all paths with edge frequency
3. Divergence analysis (prose, 3–5 key observations)
4. Recommendations (bulleted, prioritized by expected impact)