from __future__ import annotations

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
class DisplayConfig:
    retina_scale: int = 2


@dataclass
class TimingConfig:
    click_delay: tuple[float, float] = (0.5, 1.5)
    page_load_wait: tuple[float, float] = (3.0, 8.0)
    scan_interval_minutes: int = 60
    max_retries: int = 3
    timeout_multiplier: float = 1.0
    poll_interval: float = 0.75


@dataclass
class Config:
    config_path: Path
    window_title: str = "BlueStacks"
    process_name: str = "BlueStacks"
    app_package: str = "com.blizzard.diab"
    select_all_method: str = "triple_click"
    gems: list[GemDef] = field(default_factory=list)
    templates: dict[str, TemplateDef] = field(default_factory=dict)
    regions: dict[str, Region] = field(default_factory=dict)
    timing: TimingConfig = field(default_factory=TimingConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)
    step_timeouts: dict[str, float] = field(default_factory=dict)

    @property
    def project_dir(self) -> Path:
        return self.config_path.parent

    @property
    def templates_dir(self) -> Path:
        return self.project_dir / "templates"

    @property
    def debug_dir(self) -> Path:
        return self.project_dir / "debug"

    def get_timeout(self, step_name: str) -> float:
        """Get the timeout for a named step, scaled by timeout_multiplier."""
        raw = self.step_timeouts.get(step_name, self.step_timeouts.get("default", 20.0))
        return raw * self.timing.timeout_multiplier


def load_config(path: str | Path | None = None) -> Config:
    if path is None:
        path = Path.cwd() / "config.yaml"
    path = Path(path).resolve()

    with open(path) as f:
        raw = yaml.safe_load(f) or {}

    game = raw.get("game", {})
    timing_raw = raw.get("timing", {})
    display_raw = raw.get("display", {})
    step_timeouts_raw = raw.get("step_timeouts", {})

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

    click_delay = timing_raw.get("click_delay", [0.5, 1.5])
    page_load_wait = timing_raw.get("page_load_wait", [3.0, 8.0])

    return Config(
        config_path=path,
        window_title=game.get("window_title", "BlueStacks"),
        process_name=game.get("process_name", "BlueStacks"),
        app_package=game.get("app_package", "com.blizzard.diab"),
        select_all_method=game.get("select_all_method", "triple_click"),
        gems=gems,
        templates=templates,
        regions=regions,
        display=DisplayConfig(
            retina_scale=display_raw.get("retina_scale", 2),
        ),
        timing=TimingConfig(
            click_delay=tuple(click_delay),
            page_load_wait=tuple(page_load_wait),
            scan_interval_minutes=timing_raw.get("scan_interval_minutes", 60),
            max_retries=timing_raw.get("max_retries", 3),
            timeout_multiplier=timing_raw.get("timeout_multiplier", 1.0),
            poll_interval=timing_raw.get("poll_interval", 0.75),
        ),
        step_timeouts={k: float(v) for k, v in step_timeouts_raw.items()},
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
