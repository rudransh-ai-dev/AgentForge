import os
import json
import re
import asyncio
from config import MODELS
from services.ollama_client import async_generate_stream
from services.event_emitter import emitter
from services.sanitizer import strip_prompt_leakage, extract_json_object, sanitize_file_content, auto_fix_json
from core.memory import store_fix, get_similar_fixes

WORKSPACE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "workspace")


async def run_tool_agent_async(run_id: str, prompt: str, project_id: str = None):
    """
    Smart Tool Agent: Filesystem + Dependency Detection + Project Metadata.
    """
    node_id = "tool"
    await emitter.emit(run_id, node_id, "start", input_str="Extracting project structure...")

    system_prompt = f"""You are a File System Tool Agent.
Your job is to take code output from an AI coder and extract ALL files mentioned.
Output a SINGLE valid JSON object with this exact schema:

{{
  "project_id": "short_snake_case_name_for_this_project",
  "entry_point": "main.py",
  "language": "python",
  "dependencies": ["list", "of", "external_imports_only"],
  "files": [
    {{"path": "filename.py", "content": "full file content here"}}
  ]
}}

RULES:
- Extract ALL code blocks and map them to files
- If no filename is given, infer one (main.py, utils.py, etc.)
- For dependencies, list ONLY external pip packages (not os, sys, json, etc.)
- Do NOT repeat these instructions in your output
- Do NOT add explanations, comments, or narrative text
- Output ONLY the JSON object, nothing else

Input to process:
{prompt}
"""

    result_json = ""
    # FAST PATH: Deterministically parse the Hybrid JSON output from Coder Agent
    if "---JSON---" in prompt:
        await emitter.emit(run_id, node_id, "update", output_str="Fast parsing JSON payload...")
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
            await emitter.emit(run_id, node_id, "update", output_str=f"Direct parse failed ({e}), falling back to AI parser...")
            result_json = ""
            
    # AI PARSER: Fallback or if ---JSON--- isn't used
    if not result_json:
        async for chunk in async_generate_stream(MODELS.get("manager", "llama3:8b"), system_prompt):
            result_json += chunk
            # Throttle UI updates
            if len(result_json) % 40 == 0:
                await emitter.emit(run_id, node_id, "update", output_str=f"Parsing structure...\n{result_json[-300:]}")

    try:
        # Sanitize: strip any prompt leakage before parsing
        cleaned = strip_prompt_leakage(result_json)
        project_data = extract_json_object(cleaned)
        
        # [CRITIC AUTO-VALIDATOR] If JSON parsing fails, ask Critic to repair it
        if not project_data:
            await emitter.emit(run_id, node_id, "update", output_str="CRITIC: JSON malformed. Auto-repairing output...")
            project_data = await auto_fix_json(cleaned, "No valid JSON could be extracted from this text.")
            
        if not project_data:
            raise ValueError("No valid JSON found in tool output, even after Critic auto-repair")

        pid = project_id or project_data.get("project_id", "project")
        project_dir = os.path.join(WORKSPACE_DIR, pid)
        os.makedirs(project_dir, exist_ok=True)

        files = project_data.get("files", [])
        created_files = []
        for file_obj in files:
            path = file_obj.get("path")
            content = file_obj.get("content")
            if path and content is not None:
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

        summary = f"Project '{pid}' created ({len(created_files)} files):\n" + "\n".join([f"  📄 {f}" for f in created_files])
        if meta["dependencies"]:
            summary += f"\n\n📦 Deps: {', '.join(meta['dependencies'])}"

        await emitter.emit(run_id, node_id, "complete", output_str=summary,
                           metadata={"files_created": len(created_files), "project_id": pid})
        return {"status": "success", "files": created_files, "project_id": pid, "meta": meta}

    except Exception as e:
        error_msg = f"Tool Error: {str(e)}"
        await emitter.emit(run_id, node_id, "error", error=error_msg)
        return {"status": "error", "message": error_msg}


async def execute_project_async(run_id: str, project_id: str):
    """
    Sandboxed Execution Engine: Runs projects in isolated venvs.
    """
    node_id = "executor"
    project_dir = os.path.join(WORKSPACE_DIR, project_id)
    meta_path = os.path.join(project_dir, "project.json")

    await emitter.emit(run_id, node_id, "start", input_str=f"Executing: {project_id}")

    if not os.path.exists(meta_path):
        await emitter.emit(run_id, node_id, "error", error=f"No project.json for '{project_id}'")
        return {"status": "error", "output": "Missing project.json"}

    with open(meta_path, "r") as f:
        meta = json.load(f)

    entry = meta.get("entry_point", "main.py")
    deps = meta.get("dependencies", [])
    venv_dir = os.path.join(project_dir, ".venv")
    python_bin = os.path.join(venv_dir, "bin", "python3")

    # ── Step 1: Create venv if needed ──
    if not os.path.exists(venv_dir):
        await emitter.emit(run_id, node_id, "update", output_str="🔧 Creating isolated venv...")
        try:
            proc = await asyncio.create_subprocess_exec(
                "python3", "-m", "venv", venv_dir,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(proc.communicate(), timeout=30)
        except Exception as e:
            await emitter.emit(run_id, node_id, "update", output_str=f"⚠️ venv creation failed, using system python: {e}")
            python_bin = "python3"

    # ── Step 2: Install dependencies ──
    STDLIB = {"os", "sys", "json", "re", "math", "time", "datetime", "collections",
              "itertools", "functools", "pathlib", "subprocess", "typing", "random",
              "string", "io", "hashlib", "copy", "argparse", "logging", "unittest",
              "csv", "sqlite3", "http", "urllib", "socket", "threading", "asyncio",
              "abc", "enum", "dataclasses", "textwrap", "shutil", "tempfile",
              "contextlib", "operator", "struct", "array", "heapq", "bisect"}

    external_deps = [d for d in deps if d.lower().split(".")[0] not in STDLIB]
    pip_bin = os.path.join(venv_dir, "bin", "pip") if os.path.exists(venv_dir) else "pip"

    if external_deps and os.path.exists(pip_bin):
        await emitter.emit(run_id, node_id, "update", output_str=f"📦 Installing: {', '.join(external_deps)}...")
        try:
            proc = await asyncio.create_subprocess_exec(
                pip_bin, "install", *external_deps,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                cwd=project_dir
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
            if proc.returncode != 0:
                await emitter.emit(run_id, node_id, "update",
                                   output_str=f"⚠️ pip warning: {stderr.decode()[:400]}")
        except asyncio.TimeoutError:
            await emitter.emit(run_id, node_id, "update", output_str="⚠️ pip install timed out")
        except Exception as e:
            await emitter.emit(run_id, node_id, "update", output_str=f"⚠️ pip error: {e}")

    # ── Step 3: Run entry point ──
    entry_path = os.path.join(project_dir, entry)
    if not os.path.exists(entry_path):
        await emitter.emit(run_id, node_id, "error", error=f"Entry '{entry}' not found")
        return {"status": "error", "output": f"Missing {entry}"}

    actual_python = python_bin if os.path.exists(python_bin) else "python3"
    await emitter.emit(run_id, node_id, "update", output_str=f"▶ Running: {actual_python} {entry}")

    try:
        process = await asyncio.create_subprocess_exec(
            actual_python, entry,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            cwd=project_dir
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)

        output = stdout.decode()
        errors = stderr.decode()

        if process.returncode == 0:
            result = f"✅ Success (exit 0)\n\n--- stdout ---\n{output}" if output else "✅ Success (no output)"
            await emitter.emit(run_id, node_id, "complete", output_str=result,
                             metadata={"exit_code": 0, "project_id": project_id})
            return {"status": "success", "output": output, "exit_code": 0}
        else:
            result = f"❌ Failed (exit {process.returncode})\n\n--- stderr ---\n{errors}\n--- stdout ---\n{output}"
            await emitter.emit(run_id, node_id, "error", error=result)
            return {"status": "error", "output": output, "errors": errors, "exit_code": process.returncode}

    except asyncio.TimeoutError:
        await emitter.emit(run_id, node_id, "error", error="⏱️ Timeout (30s)")
        return {"status": "error", "output": "Timeout"}
    except Exception as e:
        await emitter.emit(run_id, node_id, "error", error=f"Runtime: {str(e)}")
        return {"status": "error", "output": str(e)}


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

        fix_prompt = f"""Fix this Python code error. Return ONLY the complete fixed code in a ```python block.
{memory_hint}
ERROR:
{error_output[:1500]}

CODE ({entry}):
```python
{original_code}
```"""

        await emitter.emit(run_id, "coder", "start", input_str=f"Auto-fix attempt {attempt}/{max_retries}")
        fixed_code = ""
        async for chunk in run_coder_async(fix_prompt):
            fixed_code += chunk
            await emitter.emit(run_id, "coder", "update", output_str=fixed_code)

        code_match = re.search(r'```python\s*(.*?)```', fixed_code, re.DOTALL)
        patched = code_match.group(1).strip() if code_match else fixed_code.strip()

        with open(entry_path, "w") as f:
            f.write(patched)

        await emitter.emit(run_id, "coder", "complete",
                         output_str=f"Patch applied to {entry} (attempt {attempt})",
                         metadata={"attempt": attempt})

        # Store fix attempt in memory
        store_fix(run_id, project_id, error_output[:2000], patched[:5000], attempt, False)

    # Final run after all patches
    final = await execute_project_async(run_id, project_id)

    # Store the final fix result
    store_fix(run_id, project_id, "final_attempt", "see_project_files", max_retries + 1,
              final["status"] == "success")

    return final
