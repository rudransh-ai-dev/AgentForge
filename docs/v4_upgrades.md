# v4.0 Upgrade Notes

Changelog of the bugs hunted and features added in the v4.0 pass — the production hardening round before demo.

## New Agents & Model Roster

7-agent production roster, tuned for 16 GB VRAM (RTX 5070 Ti).

| Role      | Model              | VRAM    | Purpose                      |
|-----------|--------------------|---------|------------------------------|
| Manager   | llama3.1:8b        | 6.6 GB  | Routing, planning, chat      |
| Writer    | gpt-oss:20b        | 13 GB   | First-draft code generation  |
| Editor    | qwen2.5-coder:14b  | 9 GB    | Refinement of Writer output  |
| Tester    | deepseek-r1:8b     | 5.2 GB  | QA validation / critique     |
| Researcher| qwen2.5:14b        | 9 GB    | Web/context research         |
| Reader    | llama3.1:8b        | pinned  | Codebase Q&A                 |
| Heavy     | phi4:latest        | 17 GB   | Architectural fallback       |

**Rule:** Writer and Editor MUST be different models — same model on both collapses the 3-stage pipeline into pointless self-review.

## Pipeline Fixes

- **Dead fallback chain**: `FALLBACK_CHAIN` pointed at models no longer pulled locally (phi3:mini, llama3:8b) → 600s hangs on every fallback. Now references only verified local tags.
- **Cold-load tax**: every agent hop paid a full model reload. Added `keep_alive=15m` to both `generate` and `stream` Ollama payloads → model-switch latency drops from minutes to seconds.
- **Manager warmup**: `main.py` startup now pre-loads the manager model so the first demo click isn't the cold one.
- **Dynamic model release**: orchestrator's `release_model()` calls previously hardcoded `qwen2.5-coder:14b` and evicted the editor mid-pipeline. Now resolved dynamically via `_model_name()` helper.

## Prompt System (v4.1)

- **`SafePromptTemplate`**: `str` subclass that treats literal `{`/`}` as data, not format fields. Fixes the `KeyError: '\n  "project_id"'` that crashed the Writer agent whenever its prompt contained embedded JSON examples.
- **Flat-prompt support**: prompt loader now handles both `## Pipeline Prompt` sectioned format and flat single-prompt markdown files.
- **Zero-arg runnability rule**: writer.md and editor.md now require scripts to run with `python main.py` alone — no `sys.argv[1]` dependencies. Tester no longer flags hardcoded demo values as bugs.
- **Visual-impact rules**: writer.md mandates multi-file projects (`index.html` + `styles.css` + `script.js` + `main.py`) with modern dark-theme CSS. No more monolithic script dumps.

## Canvas & Frontend

- **`/run-node` dispatcher**: previously handled only 3 agent types (coder / critic / analyst). Rewrote with `_resolve_node_handler()` covering writer, editor, tester, critic, manager, analyst, researcher, tool, executor, and input nodes.
- **Input node + Run Pipeline button**: the canvas Input node now has a textarea and a green ▶ Run Pipeline button (Ctrl/Cmd+Enter to submit). Previously there was no way to start a pipeline from the canvas at all.
- **Manager model override plumbing**: `node_models["manager"]` is now passed through `route_task_async` → canvas model overrides actually take effect.
- **Workspace routing**: `WORKSPACE_DIR` in `main.py` fixed to point at the project-root `workspace/` matching what `tool.py` writes to. Previously the UI read an empty `backend/workspace/`.

## Tool Agent

- **JSON-in-markdown fast-path**: Writer's `{project_id, files:[...]}` JSON was being caught by the generic markdown fast-path and saved as a literal `main.json` file. New JSON fast-path runs first and correctly unpacks the file tree.

## Executor

- **`stdin=DEVNULL`**: scripts calling `input()` no longer hang 60s waiting on stdin — they fail fast so the tester flags the bug.

## Metrics Panel

- **UTC timestamp bug**: `get_latency_timeseries` and `get_vram_timeseries` used `datetime.now().isoformat()` for the SQL cutoff. SQLite's `CURRENT_TIMESTAMP` stores UTC with a space separator; Python's `isoformat()` returns local-time with a `T` separator. String comparison silently failed → panel always empty. Fixed to `datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")`. Verified: 0 rows → 13 rows on the same DB.
- **Model breakdown injection**: all configured models now appear in the breakdown table even with runs=0, so the demo doesn't show a half-empty panel on a fresh DB.

## Housekeeping (this commit)

- Deleted `backend.log`, `curl1.log`, `curl2.log`, `curl3.log` from project root.
- `.gitignore` extended to cover `*.log`, SQLite WAL/SHM files, `backend/diffs/`, and nested `.venv` dirs inside generated workspace projects.
- Purged `backend/__pycache__` directories.

## Known Gaps

- `make_a_to_do_list_app/` in workspace has a Flask backend without a root-route static file server — frontend can't fetch its own API when opened from file://. Demo uses `project/` (crypto dashboard) instead, which streams cleanly over WebSocket on localhost:8000.
- `agent Testing/` and `.agents/skills/` folders at project root are personal notes — intentionally left alone.
