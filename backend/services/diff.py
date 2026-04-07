import difflib
import os
import json
import time
from datetime import datetime

WORKSPACE_DIR = os.path.join(os.path.dirname(__file__), "..", "workspace")
DIFFS_DIR = os.path.join(os.path.dirname(__file__), "..", "diffs")
os.makedirs(DIFFS_DIR, exist_ok=True)


def generate_diff(original, patched, filename="file"):
    """Generate a unified diff between two strings."""
    original_lines = original.splitlines(keepends=True)
    patched_lines = patched.splitlines(keepends=True)

    diff = list(difflib.unified_diff(
        original_lines,
        patched_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm="",
    ))

    return "".join(diff)


def generate_html_diff(original, patched, filename="file"):
    """Generate an HTML-friendly diff with line-by-line details."""
    original_lines = original.splitlines()
    patched_lines = patched.splitlines()

    differ = difflib.SequenceMatcher(None, original_lines, patched_lines)
    result = []

    for tag, i1, i2, j1, j2 in differ.get_opcodes():
        if tag == "equal":
            for i in range(i1, i2):
                result.append({"type": "equal", "line_num": i + 1, "content": original_lines[i]})
        elif tag == "replace":
            for i in range(i1, i2):
                result.append({"type": "removed", "line_num": i + 1, "content": original_lines[i]})
            for j in range(j1, j2):
                result.append({"type": "added", "line_num": j + 1, "content": patched_lines[j]})
        elif tag == "delete":
            for i in range(i1, i2):
                result.append({"type": "removed", "line_num": i + 1, "content": original_lines[i]})
        elif tag == "insert":
            for j in range(j1, j2):
                result.append({"type": "added", "line_num": j + 1, "content": patched_lines[j]})

    return result


def save_diff(project_id, filename, original, patched, attempt=0):
    """Save a diff record to disk."""
    project_diffs_dir = os.path.join(DIFFS_DIR, project_id)
    os.makedirs(project_diffs_dir, exist_ok=True)

    diff_id = f"{int(time.time())}_{filename.replace('/', '_')}"
    diff_data = {
        "diff_id": diff_id,
        "project_id": project_id,
        "filename": filename,
        "original": original,
        "patched": patched,
        "unified_diff": generate_diff(original, patched, filename),
        "line_diff": generate_html_diff(original, patched, filename),
        "attempt": attempt,
        "timestamp": datetime.now().isoformat(),
        "additions": sum(1 for line in diff_data.get("line_diff", []) if line["type"] == "added") if False else 0,
        "deletions": sum(1 for line in diff_data.get("line_diff", []) if line["type"] == "removed") if False else 0,
    }

    diff_data["additions"] = sum(1 for line in diff_data["line_diff"] if line["type"] == "added")
    diff_data["deletions"] = sum(1 for line in diff_data["line_diff"] if line["type"] == "removed")

    diff_path = os.path.join(project_diffs_dir, f"{diff_id}.json")
    with open(diff_path, "w") as f:
        json.dump(diff_data, f, indent=2)

    return diff_data


def get_diffs_for_project(project_id):
    """Get all diffs for a project."""
    project_diffs_dir = os.path.join(DIFFS_DIR, project_id)
    if not os.path.exists(project_diffs_dir):
        return []

    diffs = []
    for filename in sorted(os.listdir(project_diffs_dir)):
        if filename.endswith(".json"):
            with open(os.path.join(project_diffs_dir, filename), "r") as f:
                diff_data = json.load(f)
                diffs.append({
                    "diff_id": diff_data["diff_id"],
                    "filename": diff_data["filename"],
                    "attempt": diff_data["attempt"],
                    "timestamp": diff_data["timestamp"],
                    "additions": diff_data["additions"],
                    "deletions": diff_data["deletions"],
                })

    return sorted(diffs, key=lambda d: d["timestamp"], reverse=True)


def get_diff(project_id, diff_id):
    """Get a specific diff."""
    project_diffs_dir = os.path.join(DIFFS_DIR, project_id)
    diff_path = os.path.join(project_diffs_dir, f"{diff_id}.json")
    if not os.path.exists(diff_path):
        return None

    with open(diff_path, "r") as f:
        return json.load(f)
