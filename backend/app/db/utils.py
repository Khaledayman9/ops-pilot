"""
Shared utilities used across all agents.
Agent-specific utilities live in agents/<name>/utils.py.
"""

import os
from functools import lru_cache

import yaml


@lru_cache(maxsize=32)
def load_prompt(agent_name: str) -> dict[str, str]:
    """
    Load prompts.yaml for a given agent by name.
    Cached after first load.

    Args:
        agent_name: folder name under app/agents/, e.g. 'classifier'

    Returns:
        dict with keys 'system' and 'user_template'
    """
    base_dir = os.path.dirname(os.path.dirname(__file__))
    prompt_path = os.path.join(base_dir, "agents", agent_name, "prompts.yaml")

    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    with open(prompt_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return {
        "system": data.get("system", ""),
        "user_template": data.get("user_template", ""),
    }


def format_prompt(template: str, **kwargs) -> str:
    """
    Format a prompt template string with keyword arguments.

    Args:
        template: string with {key} placeholders
        **kwargs: values to substitute

    Returns:
        formatted string
    """
    try:
        return template.format(**kwargs)
    except KeyError as exc:
        raise ValueError(f"Missing prompt variable: {exc}") from exc
