from __future__ import annotations
import yaml
from pathlib import Path

def load_yaml(path: str | Path) -> dict:
    p = Path(path)
    return yaml.safe_load(p.read_text(encoding="utf-8"))

def load_config(project_root: str | Path) -> dict:
    root = Path(project_root)
    return load_yaml(root / "config" / "config.yaml")

def load_score_maps(project_root: str | Path) -> dict:
    root = Path(project_root)
    return load_yaml(root / "config" / "score_maps.yaml")
