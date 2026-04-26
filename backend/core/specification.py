"""
Specification Agent helpers for V5.

The spec step is intentionally deterministic. It turns vague user input into a
compact execution contract before routing, without spending another model call.
"""

import re
from dataclasses import dataclass, field


LANGUAGE_HINTS = {
    "python": ["python", ".py", "django", "flask", "fastapi"],
    "javascript": ["javascript", "js", "node", "react", "vite", ".js"],
    "typescript": ["typescript", "ts", ".ts", ".tsx"],
    "html": ["html", "css", "web page", "website", "frontend"],
    "java": ["java", "spring"],
    "go": ["golang", " go "],
    "rust": ["rust"],
    "c++": ["c++", "cpp"],
    "bash": ["bash", "shell", "script"],
}

CODE_WORDS = {
    "build", "create", "make", "write", "code", "implement", "develop",
    "script", "program", "app", "application", "function", "class", "fix",
    "debug", "refactor", "calculator", "todo", "dashboard", "api",
}


@dataclass
class TaskSpecification:
    original_prompt: str
    intent: str
    output_type: str
    language: str = "unspecified"
    constraints: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    needs_clarification: bool = False
    clarification_question: str = ""

    def to_prompt_block(self) -> str:
        constraints = "\n".join(f"- {item}" for item in self.constraints) or "- None"
        criteria = "\n".join(f"- {item}" for item in self.acceptance_criteria) or "- Complete the requested task"
        return (
            "[V5 Specification]\n"
            f"Intent: {self.intent}\n"
            f"Expected output: {self.output_type}\n"
            f"Language/framework: {self.language}\n"
            f"Needs clarification: {self.needs_clarification}\n"
            f"Clarifying question: {self.clarification_question or 'none'}\n"
            "Constraints:\n"
            f"{constraints}\n"
            "Acceptance criteria:\n"
            f"{criteria}"
        )

    def to_dict(self) -> dict:
        return {
            "intent": self.intent,
            "output_type": self.output_type,
            "language": self.language,
            "constraints": self.constraints,
            "acceptance_criteria": self.acceptance_criteria,
            "needs_clarification": self.needs_clarification,
            "clarification_question": self.clarification_question,
        }


def build_task_spec(prompt: str) -> TaskSpecification:
    text = (prompt or "").strip()
    lower = f" {text.lower()} "
    words = set(re.findall(r"[a-zA-Z0-9_+#.-]+", lower))

    language = "unspecified"
    for name, hints in LANGUAGE_HINTS.items():
        if any(hint in lower for hint in hints):
            language = name
            break

    is_code = bool(words & CODE_WORDS) or any(token in lower for token in [" in python", " in javascript", "hello world"])
    is_research = any(token in lower for token in ["research", "explain", "compare", "summarize", "what is", "how does", "why"])

    if is_code:
        output_type = "project_files"
        intent = "Generate or modify runnable code"
    elif is_research:
        output_type = "grounded_answer"
        intent = "Research and synthesize an answer"
    else:
        output_type = "answer"
        intent = "Analyze and respond"

    constraints = [
        "Do not invent missing facts; state assumptions explicitly.",
        "Keep the response focused on the user's requested outcome.",
    ]

    acceptance = []
    if output_type == "project_files":
        acceptance.extend([
            "Return complete files, not loose fragments.",
            "Include a runnable entry point when the task implies execution.",
            "Use the requested language or infer the smallest practical stack.",
            "Avoid placeholder-only implementations.",
        ])
    elif output_type == "grounded_answer":
        acceptance.extend([
            "Use retrieved project or documentation context when available.",
            "Separate facts from assumptions.",
        ])
    else:
        acceptance.append("Answer directly with enough context to be useful.")

    vague_code = is_code and language == "unspecified" and len(words) <= 5
    return TaskSpecification(
        original_prompt=text,
        intent=intent,
        output_type=output_type,
        language=language,
        constraints=constraints,
        acceptance_criteria=acceptance,
        needs_clarification=vague_code,
        clarification_question="Which language or platform should this be built in?" if vague_code else "",
    )
