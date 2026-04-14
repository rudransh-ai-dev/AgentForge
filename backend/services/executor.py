import os
import asyncio
from abc import ABC, abstractmethod
from typing import Optional


class Runner(ABC):
    """Base class for language-specific project runners."""

    @property
    @abstractmethod
    def language(self) -> str:
        pass

    @abstractmethod
    async def setup(self, project_dir: str, emit) -> bool:
        pass

    @abstractmethod
    async def install_deps(self, project_dir: str, deps: list, emit) -> None:
        pass

    @abstractmethod
    async def run(self, project_dir: str, entry: str, emit, timeout: int = 60) -> dict:
        pass

    @abstractmethod
    def detect(self, project_dir: str, files: list) -> bool:
        pass


class PythonRunner(Runner):
    @property
    def language(self):
        return "python"

    def detect(self, project_dir, files):
        return any(f.endswith(".py") for f in files)

    async def setup(self, project_dir, emit):
        venv_dir = os.path.join(project_dir, ".venv")
        try:
            import venv
            builder = venv.EnvBuilder(with_pip=True, clear=False, symlinks=True)
            builder.create(venv_dir)
        except Exception:
            pass

        if not os.path.exists(venv_dir):
            try:
                proc = await asyncio.create_subprocess_exec(
                    "python3", "-m", "venv", "--clear", venv_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=project_dir,
                )
                await asyncio.wait_for(proc.communicate(), timeout=60)
            except Exception:
                pass

        python_bin = os.path.join(venv_dir, "bin", "python3")
        if not os.path.exists(python_bin):
            python_bin = os.path.join(venv_dir, "bin", "python")
        if not os.path.exists(python_bin):
            return False, "python3"
        return True, python_bin

    async def install_deps(self, project_dir, deps, emit):
        STDLIB = {
            "os", "sys", "json", "re", "math", "time", "datetime",
            "collections", "itertools", "functools", "pathlib", "subprocess",
            "typing", "random", "string", "io", "hashlib", "copy", "argparse",
            "logging", "unittest", "csv", "sqlite3", "http", "urllib", "socket",
            "threading", "asyncio", "abc", "enum", "dataclasses", "textwrap",
            "shutil", "tempfile", "contextlib", "operator", "struct", "array",
            "heapq", "bisect", "platform", "signal", "warnings", "traceback",
            "code", "inspect", "dis", "pprint", "reprlib", "numbers", "decimal",
            "fractions", "statistics", "secrets", "glob", "fnmatch", "stat",
            "fileinput", "filecmp", "pickle", "shelve", "marshal", "dbm",
            "configparser", "email", "html", "xml", "webbrowser", "cgi",
            "wsgiref", "xmlrpc", "ipaddress", "mailbox", "mimetypes", "base64",
            "binascii", "quopri", "calendar", "locale", "gettext", "getpass",
            "ctypes", "codecs", "unicodedata", "difflib", "sched", "queue",
            "_thread", "multiprocessing", "concurrent", "contextvars", "gc",
            "weakref", "types", "copyreg", "atexit", "builtins", "__future__",
            "importlib", "pkgutil", "zipimport", "zipfile", "tarfile", "gzip",
            "bz2", "lzma", "zlib", "hmac", "psutil",
        }
        external_deps = [d for d in deps if d.lower().split(".")[0].split("[")[0] not in STDLIB]
        if not external_deps:
            return

        venv_dir = os.path.join(project_dir, ".venv")
        pip_bin = os.path.join(venv_dir, "bin", "pip")
        if not os.path.exists(pip_bin):
            pip_bin = "pip3"

        await emit("update", f"Installing: {', '.join(external_deps)}...")
        try:
            proc = await asyncio.create_subprocess_exec(
                pip_bin, "install", "--quiet", *external_deps,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=project_dir,
                env={**os.environ, "PIP_NO_INPUT": "1", "PYTHONIOENCODING": "utf-8"},
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)
            if proc.returncode != 0:
                err_text = stderr.decode().strip()[:500] if stderr else "unknown"
                await emit("update", f"pip warning: {err_text}")
        except asyncio.TimeoutError:
            await emit("update", "pip install timed out after 180s")
        except Exception as e:
            await emit("update", f"pip error: {e}")

    async def run(self, project_dir, entry, emit, timeout=60):
        venv_dir = os.path.join(project_dir, ".venv")
        python_bin = os.path.join(venv_dir, "bin", "python3")
        if not os.path.exists(python_bin):
            python_bin = os.path.join(venv_dir, "bin", "python")
        if not os.path.exists(python_bin):
            python_bin = "python3"

        venv_ok = os.path.exists(venv_dir)
        env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"}
        if venv_ok:
            env["VIRTUAL_ENV"] = venv_dir
            env["PATH"] = os.path.join(venv_dir, "bin") + os.pathsep + os.environ.get("PATH", "")

        await emit("update", f"Running: {python_bin} {entry}")

        try:
            process = await asyncio.create_subprocess_exec(
                python_bin, entry,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=project_dir,
                env=env,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            output = stdout.decode(errors="replace")
            errors = stderr.decode(errors="replace")

            if process.returncode == 0:
                return {
                    "status": "success",
                    "output": output if output else "(no output)",
                    "exit_code": 0,
                }
            else:
                return {
                    "status": "error",
                    "output": output,
                    "errors": errors,
                    "exit_code": process.returncode,
                }
        except asyncio.TimeoutError:
            return {"status": "error", "output": f"Timeout after {timeout}s", "exit_code": -1}
        except Exception as e:
            return {"status": "error", "output": str(e), "exit_code": -1}


class NodeRunner(Runner):
    @property
    def language(self):
        return "node"

    def detect(self, project_dir, files):
        return any(f.endswith((".js", ".jsx", ".ts", ".tsx", ".mjs")) for f in files)

    async def setup(self, project_dir, emit):
        node_path = await self._find_command("node")
        npm_path = await self._find_command("npm")
        if not node_path:
            return False, None, None
        return True, node_path, npm_path

    async def install_deps(self, project_dir, deps, emit):
        package_json = os.path.join(project_dir, "package.json")
        if os.path.exists(package_json):
            _, _, npm_path = await self.setup(project_dir, emit)
            if npm_path:
                await emit("update", "Running npm install...")
                try:
                    proc = await asyncio.create_subprocess_exec(
                        npm_path, "install", "--no-audit", "--no-fund",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        cwd=project_dir,
                    )
                    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)
                    if proc.returncode != 0:
                        err_text = stderr.decode().strip()[:500]
                        await emit("update", f"npm warning: {err_text}")
                except Exception as e:
                    await emit("update", f"npm error: {e}")
        elif deps:
            _, _, npm_path = await self.setup(project_dir, emit)
            if npm_path:
                await emit("update", f"Installing: {', '.join(deps)}...")
                try:
                    proc = await asyncio.create_subprocess_exec(
                        npm_path, "install", "--save", *deps,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        cwd=project_dir,
                    )
                    await asyncio.wait_for(proc.communicate(), timeout=180)
                except Exception as e:
                    await emit("update", f"npm error: {e}")

    async def run(self, project_dir, entry, emit, timeout=60):
        _, node_path, _ = await self.setup(project_dir, emit)
        if not node_path:
            return {"status": "error", "output": "Node.js not found", "exit_code": -1}

        await emit("update", f"Running: node {entry}")
        env = {**os.environ, "NODE_ENV": "development"}

        try:
            process = await asyncio.create_subprocess_exec(
                node_path, entry,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=project_dir,
                env=env,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            output = stdout.decode(errors="replace")
            errors = stderr.decode(errors="replace")

            if process.returncode == 0:
                return {"status": "success", "output": output if output else "(no output)", "exit_code": 0}
            else:
                return {"status": "error", "output": output, "errors": errors, "exit_code": process.returncode}
        except asyncio.TimeoutError:
            return {"status": "error", "output": f"Timeout after {timeout}s", "exit_code": -1}
        except Exception as e:
            return {"status": "error", "output": str(e), "exit_code": -1}

    async def _find_command(self, cmd):
        for path in [f"/usr/bin/{cmd}", f"/usr/local/bin/{cmd}", cmd]:
            if os.path.exists(path) or os.system(f"which {cmd} > /dev/null 2>&1") == 0:
                return cmd
        return None


class GoRunner(Runner):
    @property
    def language(self):
        return "go"

    def detect(self, project_dir, files):
        return any(f.endswith(".go") for f in files)

    async def setup(self, project_dir, emit):
        go_path = await self._find_command("go")
        if not go_path:
            return False, None
        go_mod = os.path.join(project_dir, "go.mod")
        if not os.path.exists(go_mod):
            await emit("update", "Initializing go module...")
            try:
                proc = await asyncio.create_subprocess_exec(
                    go_path, "mod", "init", "project",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=project_dir,
                )
                await proc.communicate()
            except Exception:
                pass
        return True, go_path

    async def install_deps(self, project_dir, deps, emit):
        _, go_path = await self.setup(project_dir, emit)
        if go_path:
            await emit("update", "Running go mod tidy...")
            try:
                proc = await asyncio.create_subprocess_exec(
                    go_path, "mod", "tidy",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=project_dir,
                )
                await proc.communicate()
            except Exception as e:
                await emit("update", f"go mod error: {e}")

    async def run(self, project_dir, entry, emit, timeout=60):
        _, go_path = await self.setup(project_dir, emit)
        if not go_path:
            return {"status": "error", "output": "Go not found", "exit_code": -1}

        await emit("update", f"Running: go run {entry}")
        try:
            process = await asyncio.create_subprocess_exec(
                go_path, "run", entry,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=project_dir,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            output = stdout.decode(errors="replace")
            errors = stderr.decode(errors="replace")

            if process.returncode == 0:
                return {"status": "success", "output": output if output else "(no output)", "exit_code": 0}
            else:
                return {"status": "error", "output": output, "errors": errors, "exit_code": process.returncode}
        except asyncio.TimeoutError:
            return {"status": "error", "output": f"Timeout after {timeout}s", "exit_code": -1}
        except Exception as e:
            return {"status": "error", "output": str(e), "exit_code": -1}

    async def _find_command(self, cmd):
        if os.system(f"which {cmd} > /dev/null 2>&1") == 0:
            return cmd
        return None


class RustRunner(Runner):
    @property
    def language(self):
        return "rust"

    def detect(self, project_dir, files):
        return any(f.endswith(".rs") for f in files)

    async def setup(self, project_dir, emit):
        cargo_path = await self._find_command("cargo")
        if not cargo_path:
            return False, None
        cargo_toml = os.path.join(project_dir, "Cargo.toml")
        if not os.path.exists(cargo_toml):
            await emit("update", "Cargo.toml not found — Rust projects need Cargo.toml")
            return False, None
        return True, cargo_path

    async def install_deps(self, project_dir, deps, emit):
        _, cargo_path = await self.setup(project_dir, emit)
        if cargo_path:
            await emit("update", "Running cargo fetch...")
            try:
                proc = await asyncio.create_subprocess_exec(
                    cargo_path, "fetch",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=project_dir,
                )
                await asyncio.wait_for(proc.communicate(), timeout=300)
            except Exception as e:
                await emit("update", f"cargo fetch error: {e}")

    async def run(self, project_dir, entry, emit, timeout=120):
        _, cargo_path = await self.setup(project_dir, emit)
        if not cargo_path:
            return {"status": "error", "output": "Cargo not found or Cargo.toml missing", "exit_code": -1}

        await emit("update", "Running: cargo run")
        try:
            process = await asyncio.create_subprocess_exec(
                cargo_path, "run",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=project_dir,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            output = stdout.decode(errors="replace")
            errors = stderr.decode(errors="replace")

            if process.returncode == 0:
                return {"status": "success", "output": output if output else "(no output)", "exit_code": 0}
            else:
                return {"status": "error", "output": output, "errors": errors, "exit_code": process.returncode}
        except asyncio.TimeoutError:
            return {"status": "error", "output": f"Timeout after {timeout}s", "exit_code": -1}
        except Exception as e:
            return {"status": "error", "output": str(e), "exit_code": -1}

    async def _find_command(self, cmd):
        if os.system(f"which {cmd} > /dev/null 2>&1") == 0:
            return cmd
        return None


class BashRunner(Runner):
    @property
    def language(self):
        return "bash"

    def detect(self, project_dir, files):
        return any(f.endswith(".sh") for f in files)

    async def setup(self, project_dir, emit):
        return True, "bash"

    async def install_deps(self, project_dir, deps, emit):
        pass

    async def run(self, project_dir, entry, emit, timeout=60):
        await emit("update", f"Running: bash {entry}")
        try:
            process = await asyncio.create_subprocess_exec(
                "bash", entry,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=project_dir,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            output = stdout.decode(errors="replace")
            errors = stderr.decode(errors="replace")

            if process.returncode == 0:
                return {"status": "success", "output": output if output else "(no output)", "exit_code": 0}
            else:
                return {"status": "error", "output": output, "errors": errors, "exit_code": process.returncode}
        except asyncio.TimeoutError:
            return {"status": "error", "output": f"Timeout after {timeout}s", "exit_code": -1}
        except Exception as e:
            return {"status": "error", "output": str(e), "exit_code": -1}


RUNNERS = [PythonRunner(), NodeRunner(), GoRunner(), RustRunner(), BashRunner()]


def detect_language(project_dir, files):
    for runner in RUNNERS:
        if runner.detect(project_dir, files):
            return runner.language
    return "python"


def get_runner(language):
    for runner in RUNNERS:
        if runner.language == language:
            return runner
    return PythonRunner()
