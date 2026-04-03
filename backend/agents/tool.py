import os
import json
import re
import asyncio
from typing import Optional
from config import MODELS
from services.ollama_client import async_generate_stream
from services.event_emitter import emitter
from services.sanitizer import (
    strip_prompt_leakage,
    extract_json_object,
    sanitize_file_content,
    auto_fix_json,
)
from core.memory import store_fix, get_similar_fixes
from core.prompts import tool_prompt, coder_autofix_prompt

WORKSPACE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "workspace")


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

    # AI PARSER: Fallback or if ---JSON--- isn't used
    if not result_json:
        mgr_cfg = MODELS.get("manager", {"name": "llama3:8b"})
        mgr_model = mgr_cfg["name"] if isinstance(mgr_cfg, dict) else mgr_cfg
        async for chunk in async_generate_stream(mgr_model, system_prompt):
            result_json += chunk
            # Throttle UI updates
            if len(result_json) % 40 == 0:
                await emitter.emit(
                    run_id,
                    node_id,
                    "update",
                    output_str=f"Parsing structure...\n{result_json[-300:]}",
                )

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

        # Save project.json metadata
        meta = {
            "project_id": pid,
            "entry_point": project_data.get("entry_point", "main.py"),
            "language": project_data.get("language", "python"),
            "dependencies": project_data.get("dependencies", []),
            "files": created_files,
        }
        with open(os.path.join(project_dir, "project.json"), "w") as f:
            json.dump(meta, f, indent=2)
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
    Sandboxed Execution Engine: Runs projects in isolated venvs.
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
    venv_dir = os.path.join(project_dir, ".venv")

    # ── Step 1: Create isolated venv ──
    actual_python = "python3"
    venv_ok = False
    try:
        await emitter.emit(
            run_id, node_id, "update", output_str="🔧 Creating isolated venv..."
        )
        actual_python = await _create_venv_safely(venv_dir, project_dir)
        venv_ok = True
        await emitter.emit(
            run_id, node_id, "update", output_str=f"✅ Venv ready: {actual_python}"
        )
    except Exception as e:
        await emitter.emit(
            run_id,
            node_id,
            "update",
            output_str=f"⚠️ Venv failed ({e}), using system python",
        )

    # ── Step 2: Install dependencies ──
    STDLIB = {
        "os",
        "sys",
        "json",
        "re",
        "math",
        "time",
        "datetime",
        "collections",
        "itertools",
        "functools",
        "pathlib",
        "subprocess",
        "typing",
        "random",
        "string",
        "io",
        "hashlib",
        "copy",
        "argparse",
        "logging",
        "unittest",
        "csv",
        "sqlite3",
        "http",
        "urllib",
        "socket",
        "threading",
        "asyncio",
        "abc",
        "enum",
        "dataclasses",
        "textwrap",
        "shutil",
        "tempfile",
        "contextlib",
        "operator",
        "struct",
        "array",
        "heapq",
        "bisect",
        "psutil",
        "platform",
        "signal",
        "warnings",
        "traceback",
        "code",
        "inspect",
        "dis",
        "pprint",
        "reprlib",
        "numbers",
        "decimal",
        "fractions",
        "statistics",
        "secrets",
        "glob",
        "fnmatch",
        "stat",
        "fileinput",
        "filecmp",
        "pickle",
        "shelve",
        "marshal",
        "dbm",
        "configparser",
        "netrc",
        "xdrlib",
        "plistlib",
        "email",
        "html",
        "xml",
        "webbrowser",
        "cgi",
        "cgitb",
        "wsgiref",
        "xmlrpc",
        "ipaddress",
        "mailbox",
        "mimetypes",
        "base64",
        "binascii",
        "quopri",
        "uu",
        "calendar",
        "locale",
        "gettext",
        "getpass",
        "curses",
        "ctypes",
        "readline",
        "rlcompleter",
        "struct",
        "codecs",
        "unicodedata",
        "stringprep",
        "difflib",
        "sched",
        "queue",
        "_thread",
        "multiprocessing",
        "concurrent",
        "contextvars",
        "gc",
        "weakref",
        "types",
        "copyreg",
        "tempfile",
        "atexit",
        "builtins",
        "__future__",
        "importlib",
        "pkgutil",
        "zipimport",
        "zipfile",
        "tarfile",
        "gzip",
        "bz2",
        "lzma",
        "zlib",
        "hmac",
        "secrets",
    }

    external_deps = [
        d for d in deps if d.lower().split(".")[0].split("[")[0] not in STDLIB
    ]

    if external_deps:
        pip_bin = os.path.join(venv_dir, "bin", "pip") if venv_ok else "pip3"
        if not os.path.exists(pip_bin):
            pip_bin = "pip3"

        await emitter.emit(
            run_id,
            node_id,
            "update",
            output_str=f"📦 Installing: {', '.join(external_deps)}...",
        )
        try:
            proc = await asyncio.create_subprocess_exec(
                pip_bin,
                "install",
                "--quiet",
                *external_deps,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=project_dir,
                env={**os.environ, "PIP_NO_INPUT": "1", "PYTHONIOENCODING": "utf-8"},
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)
            if proc.returncode != 0:
                err_text = stderr.decode().strip()[:500] if stderr else "unknown"
                await emitter.emit(
                    run_id, node_id, "update", output_str=f"⚠️ pip warning: {err_text}"
                )
        except asyncio.TimeoutError:
            await emitter.emit(
                run_id,
                node_id,
                "update",
                output_str="⚠️ pip install timed out after 180s",
            )
        except Exception as e:
            await emitter.emit(
                run_id, node_id, "update", output_str=f"⚠️ pip error: {e}"
            )

    # ── Step 3: Run entry point ──
    entry_path = os.path.join(project_dir, entry)
    if not os.path.exists(entry_path):
        await emitter.emit(run_id, node_id, "error", error=f"Entry '{entry}' not found")
        return {"status": "error", "output": f"Missing {entry}"}

    if not venv_ok:
        actual_python = "python3"

    await emitter.emit(
        run_id, node_id, "update", output_str=f"▶ Running: {actual_python} {entry}"
    )

    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"}
    if venv_ok:
        env["VIRTUAL_ENV"] = venv_dir
        env["PATH"] = (
            os.path.join(venv_dir, "bin") + os.pathsep + os.environ.get("PATH", "")
        )

    try:
        process = await asyncio.create_subprocess_exec(
            actual_python,
            entry,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=project_dir,
            env=env,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60)

        output = stdout.decode(errors="replace")
        errors = stderr.decode(errors="replace")

        if process.returncode == 0:
            result = (
                f"✅ Success (exit 0)\n\n--- stdout ---\n{output}"
                if output
                else "✅ Success (no output)"
            )
            await emitter.emit(
                run_id,
                node_id,
                "complete",
                output_str=result,
                metadata={"exit_code": 0, "project_id": project_id, "venv": venv_ok},
            )
            return {
                "status": "success",
                "output": output,
                "exit_code": 0,
                "venv": venv_ok,
            }
        else:
            result = f"❌ Failed (exit {process.returncode})\n\n--- stderr ---\n{errors}\n--- stdout ---\n{output}"
            await emitter.emit(run_id, node_id, "error", error=result)
            return {
                "status": "error",
                "output": output,
                "errors": errors,
                "exit_code": process.returncode,
                "venv": venv_ok,
            }

    except asyncio.TimeoutError:
        await emitter.emit(run_id, node_id, "error", error="⏱️ Timeout (60s)")
        return {"status": "error", "output": "Timeout after 60s", "venv": venv_ok}
    except Exception as e:
        await emitter.emit(run_id, node_id, "error", error=f"Runtime: {str(e)}")
        return {"status": "error", "output": str(e), "venv": venv_ok}


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
