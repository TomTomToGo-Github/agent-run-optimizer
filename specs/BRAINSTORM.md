# AI Reproducibility — Brainstorm

## Core Problem

Modern AI agent workflows are inherently non-deterministic. Executions may succeed or fail depending on subtle variations in context, tool usage, prompt phrasing, or execution paths. This makes:

- Failures hard to reproduce
- Optimization largely trial-and-error
- Debugging opaque — no structured view of what happened and why
- Trust in production agents hard to build

As agentic systems grow more autonomous and complex, this non-determinism becomes a major blocker for reliability, scalability, and trust.

---

## Key Idea

Make every agent execution **observable** (visible as a structured graph), **replayable** (re-run from any checkpoint), and **analyzable** (compare runs, identify patterns, optimize systematically).

Each run of an LLM task = one path in a graph.  
Repeat the same call = another path.  
Overlay many runs = a probabilistic map of the agent's behavior space.

---

## 1. Graph Model for Runs

### Node Types
- **LLM node**: one call to a language model — captures model, temperature, full message list (input), response (output), token counts, latency, stop reason
- **Tool node**: one tool invocation — captures tool name, input arguments, output/result, latency, success/failure
- **Human node**: a human intervention, approval step, or feedback injection
- **Checkpoint node**: a saved execution state that can be resumed from
- **Branch node**: a decision point where execution could go different ways (e.g., conditional tool use)

### Edge Types
- **Sequential**: A → B (B runs after A)
- **Conditional**: A →[condition]→ B (B only if condition met)
- **Retry**: A →[retry]→ A' (re-run of same node with same or modified input)
- **Parallel**: A → [B, C] (B and C run concurrently)

### Graph Properties
- Directed acyclic graph (DAG) for simple runs; can contain cycles for retry loops
- Root node = start of the run (first LLM call or explicit start marker)
- Terminal nodes = success or failure endpoints
- Each path from root to terminal = one complete execution trace

### Overlay Graph
- Merge N RunGraphs into one weighted graph
- Node identity: same by (node_type, model/tool_name, prompt_hash)
- Edge weight = count of runs that traversed this edge
- Nodes annotated with aggregate stats: mean tokens, mean latency, success rate

---

## 2. Capture Layer

### What to Capture

**Execution Context**
- System prompt (full text + hash)
- Conversation history at the moment of each call
- Available tools and their schemas
- Memory / retrieved knowledge injected into context
- Context window size, token budget, any truncation applied

**Model Config**
- Model name + version (e.g., `claude-opus-4-7`)
- Temperature, top_p, max_tokens
- Any other sampling parameters
- API version / SDK version

**Tool Usage**
- Which tools were declared available
- Which tools were actually called and in what order
- Tool inputs (arguments)
- Tool outputs (results, including errors)
- Tool latency

**Per-Call Metrics**
- Input tokens, output tokens, cache hit/miss tokens
- Wall-clock latency (start → end of API call)
- Cost estimate (based on model pricing table)

**Environment / Determinism Signals**
- Python version, library versions (esp. anthropic SDK)
- Random seed (if applicable)
- External dependency versions
- Timestamp (UTC)

**Outcome**
- Explicit success / failure signal
- Partial success (goal partially met)
- Quality metrics if available (correctness, completeness, user rating)
- Error type and traceback for failures

**Human Interaction**
- Manual overrides or edits
- User feedback injected mid-run
- Retry triggers initiated by a human

### How to Capture
- Decorator `@capture_run` wrapping a function that makes LLM calls
- SDK wrapper: wrap `anthropic.Anthropic.messages.create` to auto-intercept
- Context manager `with RunCapture() as run:` for finer control
- Automatic graph building as calls are made (no manual node creation needed)

---

## 3. Storage

### Backends
- **SQLite** (default, zero-setup): `runs.db` in project root
- **JSON files**: `runs/{run-id}.json` — human-readable, git-committable
- **PostgreSQL** (for production / multi-user scenarios)

### Run Indexing
- Run ID (UUID or human-readable slug like `run-2026-04-23-abc123`)
- Tags (e.g., `success`, `failure`, `experiment-A`)
- Named run sets (group related runs)
- Filter by: date range, model, outcome, tag, cost threshold

---

## 4. Graph Analysis

### Path Comparison
- Diff two execution paths (like git diff for agent behavior)
- Find the first divergence point
- Classify divergence cause: different tool chosen, different prompt hash, different model response

### Overlay Analysis
- Most common path vs rare paths
- "Happy path" (fastest, cheapest, most successful)
- Dead ends (paths that always fail)
- High-variance nodes (where runs diverge most often)

### Statistical Analysis
- Distribution of: token usage, latency, cost, number of steps
- Correlation: does higher temperature → more path variance?
- Success rate per path, per node, per tool
- Retry rate per node

### Semantic Deduplication
- Identify "equivalent" nodes across runs despite minor prompt variations
- Use embedding similarity to cluster semantically similar context states
- Useful for building a coarser but more generalizable overlay

---

## 5. Checkpointed Execution

- Decorator `@checkpoint` on any function within a run
- State serialized to storage at each checkpoint
- Re-run from any saved checkpoint (not just from the beginning)
- Use case: expensive first-stage tool call succeeded → don't re-run it; only re-run from stage 2
- Deterministic replay mode: re-use captured inputs exactly to reproduce a previous run

---

## 6. Visualization

### Terminal (default, no dependencies)
- `rich`-based tree view of the execution path
- Color-coded by node type
- Shows token/cost summary inline

### Mermaid Diagram
- Flowchart export for embedding in GitHub/Confluence
- Overlay version shows edge frequencies

### Interactive HTML
- D3.js force-directed graph (self-contained, no CDN)
- Node tooltips with full context (truncated)
- Click to expand node details
- Filter view: show only failed nodes, show only tool nodes, etc.

### Run Timeline
- Gantt-style view showing LLM call durations and parallelism
- Useful for identifying latency bottlenecks

---

## 7. CLI

```
ai-repro list                           # list recent runs
ai-repro show <run-id>                  # display run graph in terminal
ai-repro compare <run-id> <run-id>      # diff two runs
ai-repro overlay <run-id>...            # overlay N runs
ai-repro export <run-id> --format mermaid|html|json
ai-repro replay <run-id> [--from <checkpoint-id>]
ai-repro tag <run-id> <tag>             # add tag to a run
ai-repro stats [--tag <tag>]            # aggregate statistics
```

---

## 8. Additional Ideas (Suggested)

### A/B Testing Framework
- Run the same agent prompt with two different configs (model A vs model B, temperature 0.0 vs 0.7)
- Automatically compare outcomes and metrics
- Statistical significance testing for differences

### Cost Budgets / Guardrails
- Set per-run cost limits; abort and record if exceeded
- Alert when a run exceeds N-sigma from the mean cost

### Privacy / PII Redaction
- Configurable redaction before any context is stored
- Regex-based + ML-based PII detection hooks
- Critical for production use with real user data

### OpenTelemetry Integration
- Export spans compatible with OTel trace format
- Send to Jaeger, Grafana Tempo, or Dynatrace
- Interoperate with existing distributed tracing infrastructure

### LangChain / LangGraph Integration
- Adapter layer to capture LangChain callbacks
- Translate LangGraph state machine transitions to RunGraph nodes
- Enables use on existing LangChain-based agents without rewriting

### Export to Existing Tracing Tools
- LangSmith-compatible export format
- Weights & Biases run logging
- Enables comparison with teams already using these tools

### Quality Metrics
- Plug in custom scorer functions: `score(input, output) -> float`
- Built-in scorers: response length, JSON validity, task completion detection
- Aggregate scores per node/path for optimization targeting

### Annotation Layer
- Human-readable labels for nodes ("this is where it hallucinates")
- Severity flags: info / warning / error
- Shared annotation across a team via a central store

### Multi-Agent / Multi-Turn Tracking
- Track parent–child relationships between subagent calls
- Nested RunGraphs for hierarchical agents
- Cross-agent dependency edges

### Experiment Tracking
- Group runs into named experiments
- Track hypothesis → runs → result
- Version config alongside runs (model, prompt version, tool set)

---

## Key Success Metrics

| Metric | Description |
|--------|-------------|
| Reproducibility rate | % of re-runs that follow the same path as the original |
| Variance score | Normalized path divergence across N runs of the same task |
| Cost efficiency | Tokens used vs minimum possible for the task |
| Step efficiency | LLM calls vs minimum for the task |
| Success rate | % of runs reaching a successful terminal node |
| Time to debug | How quickly a failure can be traced to its root cause |