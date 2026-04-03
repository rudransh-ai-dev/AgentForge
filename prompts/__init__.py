import os

_PROMPTS_DIR = os.path.dirname(os.path.abspath(__file__))


def _read(agent_name, section):
    path = os.path.join(_PROMPTS_DIR, f"{agent_name}.md")
    with open(path) as f:
        content = f.read()
    parts = content.split(f"## {section} Prompt")
    if len(parts) < 2:
        raise FileNotFoundError(f"Section '{section}' not found in {path}")
    return parts[1].strip()


def manager_pipeline():
    return _read("manager", "Pipeline")


def manager_chat():
    return _read("manager", "Chat")


def coder_pipeline():
    return _read("coder", "Pipeline")


def coder_chat():
    return _read("coder", "Chat")


def coder_simple():
    return coder_pipeline()


def coder_autofix():
    return coder_pipeline()


def coder_revision():
    return coder_pipeline()


def coder_fix():
    return coder_pipeline()


def analyst_pipeline():
    return _read("analyst", "Pipeline")


def analyst_chat():
    return _read("analyst", "Chat")


def critic_pipeline():
    return _read("critic", "Pipeline")


def critic_chat():
    return _read("critic", "Chat")


def critic_validation():
    return critic_pipeline()


def critic_recheck():
    return critic_pipeline()


def critic_file_review():
    return critic_pipeline()


def reader_pipeline():
    return analyst_pipeline()


def reader_chat():
    return analyst_chat()


def planner():
    return manager_pipeline()


def tool():
    return ""
