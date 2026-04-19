import os
import json
import re
import asyncio
from typing import Optional
from config import MODELS
from services.ollama_client import async_generate_stream
from services.vram_scheduler import scheduled_generate
from services.event_emitter import emitter
from services.sanitizer import (
    strip_prompt_leakage,
    extract_json_object,
    sanitize_file_content,
    auto_fix_json,
)
from core.memory import store_fix, get_similar_fixes
from core.prompts import tool_prompt, coder_autofix_prompt

WORKSPACE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "workspace")


async def run_tool_agent_async(run_id: str, prompt: str, project_id: str | None = None):
    """
    Smart Tool Agent: Filesystem + Dependency Detection + Project Metadata.
    """
    node_id = "tool"
    await emitter.emit(
        run_id, node_id, "start", input_str="Extracting project structure..."
    )

    system_prompt = tool_prompt().format(prompt=prompt)

    result_json = ""
    # FAST PATH: Deterministically parse the Hybrid JSON output from Coder Agent
    if "---JSON---" in prompt:
        await emitter.emit(
            run_id, node_id, "update", output_str="Fast parsing JSON payload..."
        )
        try:
            # Extract JSON between ---JSON--- and ---OUTPUT--- (or the end of the text)
            json_text = prompt.split("---JSON---", 1)[1]
            if "---OUTPUT---" in json_text:
                json_text = json_text.split("---OUTPUT---", 1)[0]

            # Find the actual JSON object, it might be a dictionary or a list
            json_text = strip_prompt_leakage(json_text)
            parsed_data = json.loads(json_text)

            # Normalize to the expected tool parsing schema
            if isinstance(parsed_data, list):
                project_data = {"files": parsed_data}
            elif isinstance(parsed_data, dict) and "files" in parsed_data:
                project_data = parsed_data
            else:
                raise ValueError("Format mismatch")

            result_json = json.dumps(project_data)
        except Exception as e:
            # Fallback to LLM if direct parsing fails
            await emitter.emit(
                run_id,
                node_id,
                "update",
                output_str=f"Direct parse failed ({e}), falling back to AI parser...",
            )
            result_json = ""

    # RAW JSON FAST PATH: Try to parse the entire prompt as JSON directly.
    # The Writer agent outputs pure JSON — no wrapping needed.
    if not result_json:
        try:
            raw = strip_prompt_leakage(prompt.strip())
            # Strip leading/trailing markdown fences if present
            raw = re.sub(r'^```(?:json)?\s*\n', '', raw)
            raw = re.sub(r'\n\s*```\s*$', '', raw)
            candidate = json.loads(raw)
            if isinstance(candidate, dict) and "files" in candidate:
                result_json = json.dumps(candidate)
                await emitter.emit(
                    run_id, node_id, "update",
                    output_str="Parsed project JSON directly from agent output",
                )
        except Exception:
            pass

    # JSON-IN-MARKDOWN FAST PATH: If the model wrapped a full project
    # structure inside a ```json ... ``` block, unwrap it and treat it
    # as the project payload instead of saving the JSON literally.
    # Uses GREEDY matching (.*) to capture the full nested JSON.
    if not result_json:
        json_blocks = re.findall(
            r"```(?:json)?\s*\n(\{.+\})\s*```", prompt, re.DOTALL
        )
        for jb in json_blocks:
            try:
                candidate = json.loads(strip_prompt_leakage(jb))
                if isinstance(candidate, dict) and (
                    "files" in candidate or "project_id" in candidate
                ):
                    result_json = json.dumps(candidate)
                    await emitter.emit(
                        run_id, node_id, "update",
                        output_str="Unwrapped JSON project structure from markdown block",
                    )
                    break
            except Exception:
                continue

    # MARKDOWN FAST PATH: If the coder output contains fenced code blocks,
    # extract them directly without calling an LLM. This avoids VRAM swap races
    # and makes trivial tasks (hello world, calculator) instant.
    if not result_json:
        md_blocks = re.findall(
            r"```([a-zA-Z0-9_+\-]*)\n(.*?)```", prompt, re.DOTALL
        )
        # Filter out any raw JSON blocks — those should have been handled
        # by the JSON fast path above; if they slipped through, skip them
        # here so we don't end up saving the project spec as `main.json`.
        md_blocks = [
            (lang, code) for (lang, code) in md_blocks
            if (lang or "").lower() != "json"
        ]
        if md_blocks:
            ext_map = {
                "python": "py", "py": "py",
                "javascript": "js", "js": "js",
                "typescript": "ts", "ts": "ts",
                "bash": "sh", "shell": "sh", "sh": "sh",
                "html": "html", "css": "css",
                "go": "go", "rust": "rs", "java": "java",
                "c": "c", "cpp": "cpp", "c++": "cpp",
                "json": "json", "yaml": "yml", "yml": "yml",
            }
            files = []
            used_names = set()
            deps = set()
            
            for idx, (lang, code) in enumerate(md_blocks):
                lang_lc = (lang or "").lower()
                ext = ext_map.get(lang_lc, "txt")
                
                # Extract python imports for dependencies
                if ext == "py":
                    for line in code.split("\n"):
                        line = line.strip()
                        if line.startswith("import "):
                            for pkg in line[7:].split(","):
                                deps.add(pkg.strip().split(".")[0])
                        elif line.startswith("from ") and " import " in line:
                            pkg = line[5:].split(" import ")[0].strip().split(".")[0]
                            # exclude local imports
                            if pkg and not pkg.startswith("."):
                                deps.add(pkg)

                # Try to recover a filename from a nearby "filename.ext" hint
                name_hint = re.search(
                    r"([a-zA-Z0-9_\-]+)\." + re.escape(ext), code[:200]
                )
                if name_hint:
                    fname = f"{name_hint.group(1)}.{ext}"
                else:
                    base = "main" if idx == 0 else f"file_{idx}"
                    fname = f"{base}.{ext}"
                while fname in used_names:
                    base, dot, rest = fname.rpartition(".")
                    fname = f"{base}_{idx}.{rest}"
                used_names.add(fname)
                files.append({"name": fname, "content": code.strip()})
            result_json = json.dumps({"files": files, "dependencies": list(deps)})
            await emitter.emit(
                run_id, node_id, "update",
                output_str=f"Extracted {len(files)} file(s) and {len(deps)} dep(s) from markdown"
            )

    # AI PARSER: Fallback if markdown extraction also failed
    if not result_json:
        mgr_cfg = MODELS.get("manager", {"name": "llama3.1:8b"})
        mgr_model = mgr_cfg["name"] if isinstance(mgr_cfg, dict) else mgr_cfg
        await emitter.emit(
            run_id, node_id, "update",
            output_str=f"Fast paths missed — invoking AI parser ({mgr_model})..."
        )
        try:
            chunk_count = 0
            async for chunk in scheduled_generate(mgr_model, system_prompt, stream=True):
                result_json += chunk
                chunk_count += 1
                # Emit every 10 chunks so the UI gets a live heartbeat
                if chunk_count % 10 == 0:
                    await emitter.emit(
                        run_id,
                        node_id,
                        "update",
                        output_str=f"Parsing structure...\n{result_json[-300:]}",
                    )
        except Exception as e:
            error_msg = f"Tool AI parser failed: {e}"
            await emitter.emit(run_id, node_id, "error", error=error_msg)
            return {"status": "error", "message": error_msg}

    try:
        # Sanitize: strip any prompt leakage before parsing
        cleaned = strip_prompt_leakage(result_json)
        project_data = extract_json_object(cleaned)

        # [CRITIC AUTO-VALIDATOR] If JSON parsing fails, ask Critic to repair it
        if not project_data:
            await emitter.emit(
                run_id,
                node_id,
                "update",
                output_str="CRITIC: JSON malformed. Auto-repairing output...",
            )
            project_data = await auto_fix_json(
                cleaned, "No valid JSON could be extracted from this text."
            )

        if not project_data:
            raise ValueError(
                "No valid JSON found in tool output, even after Critic auto-repair"
            )

        # Normalize: if we got a list, wrap it in a dict
        if isinstance(project_data, list):
            project_data = {"files": project_data, "project_id": "project"}
        elif not isinstance(project_data, dict):
            raise ValueError("Unexpected JSON type in tool output")

        # At this point project_data is guaranteed to be a dict
        assert isinstance(project_data, dict)

        pid = project_id or project_data.get("project_id", "project")
        project_dir = os.path.join(WORKSPACE_DIR, pid)
        os.makedirs(project_dir, exist_ok=True)

        files = project_data.get("files", [])
        created_files = []
        for file_obj in files:
            # Accept both "path" and "name" — Coder uses "name", Tool prompt says "path"
            if not isinstance(file_obj, dict):
                continue
            path = file_obj.get("path") or file_obj.get("name")
            content = file_obj.get("content")
            if path and content is not None:
                # Sanitize: strip markdown wrappers and LLM commentary
                from services.sanitizer import sanitize_file_content

                content = sanitize_file_content(content)

                # Validate Python files have actual code, not English text
                if path.endswith(".py") and content.strip():
                    try:
                        compile(content, path, "exec")
                    except SyntaxError:
                        await emitter.emit(
                            run_id,
                            node_id,
                            "update",
                            output_str=f"⚠️ Syntax error in '{path}', attempting cleanup...",
                        )
                        # Try stripping common LLM preamble lines
                        lines = content.split("\n")
                        code_lines = [
                            l
                            for l in lines
                            if not l.strip().startswith(
                                (
                                    "Based on",
                                    "Here is",
                                    "Here's",
                                    "This script",
                                    "This Python",
                                )
                            )
                        ]
                        content = "\n".join(code_lines)
                        try:
                            compile(content, path, "exec")
                        except SyntaxError:
                            await emitter.emit(
                                run_id,
                                node_id,
                                "update",
                                output_str=f"⚠️ '{path}' still has syntax errors — saving as-is for auto-fix",
                            )

                full_path = os.path.join(project_dir, path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w") as f:
                    f.write(content)
                created_files.append(path)

        # Save project.json metadata (merge with existing if present)
        meta_file = os.path.join(project_dir, "project.json")
        meta = {}
        if os.path.exists(meta_file):
            try:
                with open(meta_file, "r") as f:
                    meta = json.load(f)
            except Exception:
                pass

        merged_files = list(set(meta.get("files", []) + created_files))
        merged_deps = list(set(meta.get("dependencies", []) + project_data.get("dependencies", [])))

        meta.update({
            "project_id": pid,
            "entry_point": meta.get("entry_point") or project_data.get("entry_point", "main.py"),
            "language": meta.get("language") or project_data.get("language", "python"),
            "dependencies": merged_deps,
            "files": merged_files,
        })

        with open(meta_file, "w") as f:
            json.dump(meta, f, indent=2)
            
        if "project.json" not in created_files:
            created_files.append("project.json")

        summary = (
            f"Project '{pid}' created ({len(created_files)} files):\n"
            + "\n".join([f"  📄 {f}" for f in created_files])
        )
        if meta["dependencies"]:
            summary += f"\n\n📦 Deps: {', '.join(meta['dependencies'])}"

        await emitter.emit(
            run_id,
            node_id,
            "complete",
            output_str=summary,
            metadata={"files_created": len(created_files), "project_id": pid},
        )
        return {
            "status": "success",
            "files": created_files,
            "project_id": pid,
            "meta": meta,
        }

    except Exception as e:
        error_msg = f"Tool Error: {str(e)}"
        await emitter.emit(run_id, node_id, "error", error=error_msg)
        return {"status": "error", "message": error_msg}


async def _create_venv_safely(venv_dir: str, project_dir: str) -> str:
    """
    Create a virtual environment with proper isolation.
    Returns the path to the python binary in the venv, or 'python3' if fallback.
    """
    try:
        import venv

        builder = venv.EnvBuilder(with_pip=True, clear=False, symlinks=True)
        builder.create(venv_dir)
    except Exception:
        pass

    if not os.path.exists(venv_dir):
        try:
            proc = await asyncio.create_subprocess_exec(
                "python3",
                "-m",
                "venv",
                "--clear",
                venv_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=project_dir,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
            if proc.returncode != 0:
                err_text = stderr.decode().strip()[:200] if stderr else "unknown"
                raise RuntimeError(f"venv creation failed: {err_text}")
        except asyncio.TimeoutError:
            raise RuntimeError("venv creation timed out after 60s")
        except Exception as e:
            raise RuntimeError(f"venv creation failed: {e}")

    python_bin = os.path.join(venv_dir, "bin", "python3")
    if not os.path.exists(python_bin):
        python_bin = os.path.join(venv_dir, "bin", "python")
    if not os.path.exists(python_bin):
        raise RuntimeError("venv created but no python binary found")

    return python_bin


async def execute_project_async(run_id: str, project_id: str):
    """
    Sandboxed Execution Engine: Routes to language-specific runner.
    """
    node_id = "executor"
    project_dir = os.path.join(WORKSPACE_DIR, project_id)
    meta_path = os.path.join(project_dir, "project.json")

    await emitter.emit(run_id, node_id, "start", input_str=f"Executing: {project_id}")

    if not os.path.exists(meta_path):
        await emitter.emit(
            run_id, node_id, "error", error=f"No project.json for '{project_id}'"
        )
        return {"status": "error", "output": "Missing project.json"}

    with open(meta_path, "r") as f:
        meta = json.load(f)

    entry = meta.get("entry_point", "main.py")
    deps = meta.get("dependencies", [])
    language = meta.get("language", "python")

    from services.executor import get_runner, detect_language

    if not os.path.exists(os.path.join(project_dir, entry)):
        files = meta.get("files", [])
        detected = detect_language(project_dir, files)
        if detected != language:
            language = detected
            meta["language"] = language
            with open(meta_path, "w") as f:
                json.dump(meta, f, indent=2)

    runner = get_runner(language)

    async def emit_fn(event_type, message):
        await emitter.emit(run_id, node_id, event_type, output_str=message)

    await emit_fn("update", f"Detected language: {language}")

    setup_ok, *setup_extra = await runner.setup(project_dir, emit_fn)
    if not setup_ok and language == "python":
        await emit_fn("update", "Venv setup failed, using system python")

    await runner.install_deps(project_dir, deps, emit_fn)

    if not os.path.exists(os.path.join(project_dir, entry)):
        await emitter.emit(run_id, node_id, "error", error=f"Entry '{entry}' not found")
        return {"status": "error", "output": f"Missing {entry}"}

    result = await runner.run(project_dir, entry, emit_fn)

    if result["status"] == "success":
        await emitter.emit(
            run_id,
            node_id,
            "complete",
            output_str=f"Success (exit {result['exit_code']})\n\n{result['output']}",
            metadata={"exit_code": result["exit_code"], "project_id": project_id, "language": language},
        )
    else:
        error_text = result.get("errors", result.get("output", "Unknown error"))
        await emitter.emit(
            run_id,
            node_id,
            "error",
            error=f"Failed (exit {result.get('exit_code', -1)})\n\n{error_text}",
        )

    return result


async def autofix_loop_async(run_id: str, project_id: str, max_retries: int = 2):
    """
    Memory-Assisted Self-Correction Loop.
    Uses past fix patterns to guide the coder on repeated errors.
    """
    from agents.coder import run_coder_async

    for attempt in range(1, max_retries + 1):
        exec_result = await execute_project_async(run_id, project_id)

        if exec_result["status"] == "success":
            return exec_result

        # ── Failed: engage fix loop ──
        error_output = exec_result.get("errors", exec_result.get("output", "Unknown"))

        # Query memory for similar past fixes
        similar_fixes = get_similar_fixes(error_output)
        memory_hint = ""
        if similar_fixes:
            memory_hint = "\n\nPAST SUCCESSFUL FIXES FOR SIMILAR ERRORS:\n"
            for fix in similar_fixes:
                memory_hint += f"Error was: {fix['error'][:200]}\nFix was: {fix['fix'][:500]}\n---\n"

        project_dir = os.path.join(WORKSPACE_DIR, project_id)
        meta_path = os.path.join(project_dir, "project.json")
        with open(meta_path, "r") as f:
            meta = json.load(f)

        entry = meta.get("entry_point", "main.py")
        entry_path = os.path.join(project_dir, entry)
        original_code = ""
        if os.path.exists(entry_path):
            with open(entry_path, "r") as f:
                original_code = f.read()

        fix_prompt = coder_autofix_prompt().format(
            memory_hint=memory_hint,
            error_output=error_output[:1500],
            entry=entry,
            original_code=original_code,
        )

        await emitter.emit(
            run_id,
            "coder",
            "start",
            input_str=f"Auto-fix attempt {attempt}/{max_retries}",
        )
        fixed_code = ""
        async for chunk in run_coder_async(fix_prompt):
            fixed_code += chunk
            await emitter.emit(run_id, "coder", "update", output_str=fixed_code)

        code_match = re.search(r"```python\s*(.*?)```", fixed_code, re.DOTALL)
        patched = code_match.group(1).strip() if code_match else fixed_code.strip()

        with open(entry_path, "w") as f:
            f.write(patched)

        # Save diff for the fix
        try:
            from services.diff import save_diff
            save_diff(project_id, entry, original_code, patched, attempt)
        except Exception:
            pass

        await emitter.emit(
            run_id,
            "coder",
            "complete",
            output_str=f"Patch applied to {entry} (attempt {attempt})",
            metadata={"attempt": attempt},
        )

        # Store fix attempt in memory
        store_fix(
            run_id, project_id, error_output[:2000], patched[:5000], attempt, False
        )

    # Final run after all patches
    final = await execute_project_async(run_id, project_id)

    # Store the final fix result
    store_fix(
        run_id,
        project_id,
        "final_attempt",
        "see_project_files",
        max_retries + 1,
        final["status"] == "success",
    )

    return final
