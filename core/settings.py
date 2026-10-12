"""Small JSON-backed replacement for the legacy My.Settings values."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path

from .aux_files import empty_aux_selections
from .distributed import DistributedComputer, DistributedConfig


@dataclass(slots=True)
class AppSettings:
    simulator_version: int = 24
    dc_monitor_percent: int = 80
    ac_monitor_percent: int = 90
    contingencies_per_file: int = 80_000
    use_model_build: bool = False
    use_distributed: bool = True
    extreme_double_bus: bool = False
    extreme_double_branch: bool = False
    extreme_bus_branch: bool = False
    extreme_p1_p7: bool = False
    contingencies_per_process: int = 100
    distributed_computers: list[dict[str, object]] = field(
        default_factory=lambda: [{"name": "localhost", "connections": 2}]
    )
    aux_files: dict[str, list[dict[str, object]]] = field(default_factory=empty_aux_selections)

    def distributed_config(self) -> DistributedConfig:
        computers = tuple(
            DistributedComputer(
                name=str(item.get("name", "")),
                connections=int(item.get("connections", 0)),
            )
            for item in self.distributed_computers
        )
        return DistributedConfig(self.contingencies_per_process, computers)


class SettingsStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        if base_dir is None:
            root = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
            base_dir = Path(root) / "NERC_TPL_CA_PY" if root else Path.home() / ".nerc_tpl_ca_py"
        self.base_dir = base_dir
        self.path = base_dir / "settings.json"
        self.distributed_aux_path = base_dir / "DistComputing.aux"

    def load(self) -> AppSettings:
        if not self.path.exists():
            return AppSettings()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            allowed = AppSettings.__dataclass_fields__.keys()
            return AppSettings(**{key: value for key, value in raw.items() if key in allowed})
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            return AppSettings()

    def save(self, settings: AppSettings) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
        temporary.replace(self.path)
