from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class GemDef:
    name: str
    slug: str
    category: str  # "normal" or "legendary"
    stars: int | None = None


@dataclass
class TemplateDef:
    name: str
    file: str
    confidence: float = 0.85


@dataclass
class Region:
    x: int
    y: int
    w: int
    h: int

    def as_tuple(self) -> tuple[int, int, int, int]:
        return (self.x, self.y, self.w, self.h)


@dataclass
class TimingConfig:
    click_delay: tuple[float, float] = (0.3, 0.8)
    page_load_wait: tuple[float, float] = (1.5, 3.0)
    scan_interval_minutes: int = 60
    max_retries: int = 3


@dataclass
class Config:
    config_path: Path
    window_title: str = "Diablo Immortal"
    process_name: str = "DiabloImmortal.exe"
    gems: list[GemDef] = field(default_factory=list)
    templates: dict[str, TemplateDef] = field(default_factory=dict)
    regions: dict[str, Region] = field(default_factory=dict)
    timing: TimingConfig = field(default_factory=TimingConfig)

    @property
    def project_dir(self) -> Path:
        return self.config_path.parent

    @property
    def templates_dir(self) -> Path:
        return self.project_dir / "templates"

    @property
    def debug_dir(self) -> Path:
        return self.project_dir / "debug"


def load_config(path: str | Path | None = None) -> Config:
    if path is None:
        path = Path.cwd() / "config.yaml"
    path = Path(path).resolve()

    with open(path) as f:
        raw = yaml.safe_load(f) or {}

    game = raw.get("game", {})
    timing_raw = raw.get("timing", {})

    gems = []
    for category, gem_list in raw.get("gems", {}).items():
        for g in gem_list:
            gems.append(GemDef(
                name=g["name"],
                slug=g["slug"],
                category=category,
                stars=g.get("stars"),
            ))

    templates = {}
    for name, t in raw.get("templates", {}).items():
        if isinstance(t, dict) and "file" in t:
            templates[name] = TemplateDef(
                name=name,
                file=t["file"],
                confidence=t.get("confidence", 0.85),
            )

    regions = {}
    for name, r in raw.get("regions", {}).items():
        if isinstance(r, dict) and "x" in r:
            regions[name] = Region(x=r["x"], y=r["y"], w=r["w"], h=r["h"])

    click_delay = timing_raw.get("click_delay", [0.3, 0.8])
    page_load_wait = timing_raw.get("page_load_wait", [1.5, 3.0])

    return Config(
        config_path=path,
        window_title=game.get("window_title", "Diablo Immortal"),
        process_name=game.get("process_name", "DiabloImmortal.exe"),
        gems=gems,
        templates=templates,
        regions=regions,
        timing=TimingConfig(
            click_delay=tuple(click_delay),
            page_load_wait=tuple(page_load_wait),
            scan_interval_minutes=timing_raw.get("scan_interval_minutes", 60),
            max_retries=timing_raw.get("max_retries", 3),
        ),
    )


def save_config(config: Config) -> None:
    path = config.config_path
    with open(path) as f:
        raw = yaml.safe_load(f) or {}

    # Update templates section
    raw.setdefault("templates", {})
    for name, t in config.templates.items():
        raw["templates"][name] = {
            "file": t.file,
            "confidence": t.confidence,
        }

    # Update regions section
    raw.setdefault("regions", {})
    for name, r in config.regions.items():
        raw["regions"][name] = {"x": r.x, "y": r.y, "w": r.w, "h": r.h}

    with open(path, "w") as f:
        yaml.dump(raw, f, default_flow_style=False, sort_keys=False)
