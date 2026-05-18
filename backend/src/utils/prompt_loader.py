"""Prompt 加载工具 — 从 YAML 文件读取 Agent 的 system prompt"""

import yaml
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent.parent / "ai_core" / "prompts"


def load_prompt(name: str) -> str:
    """读取 prompts/{name}.yaml 并返回 system 字段"""
    path = PROMPTS_DIR / f"{name}.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)["system"]
