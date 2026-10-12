"""Distributed-computing configuration and contingency batching."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Sequence


@dataclass(frozen=True, slots=True)
class DistributedComputer:
    name: str
    connections: int

    def validate(self) -> None:
        name = self.name.strip()
        if not name:
            raise ValueError("Every distributed computer needs a name.")
        if any(character in name for character in ('"', "\r", "\n")):
            raise ValueError(f"Invalid computer name: {self.name!r}")
        if self.connections < 1:
            raise ValueError(f"Connections for {name} must be at least 1.")


@dataclass(frozen=True, slots=True)
class DistributedConfig:
    contingencies_per_process: int
    computers: tuple[DistributedComputer, ...]

    def validate(self) -> None:
        if self.contingencies_per_process < 1:
            raise ValueError("Contingencies per process must be at least 1.")
        if not self.computers:
            raise ValueError("At least one distributed computer is required.")
        for computer in self.computers:
            computer.validate()


def render_distributed_aux(config: DistributedConfig) -> str:
    """Build PowerWorld's distributed-options AUX text without using UI labels."""
    config.validate()

    lines = [
        "DATA (DISTRIBUTED_OPTIONS, [ATCUseDistributedComputing,CTGUseDistributedComputing,DistMasterPasswordHash,",
        "    CTGNumberPerProcess])",
        "{",
        f'"NO " "YES" "" {config.contingencies_per_process}',
        "}",
        "",
        "//--------------------------------------------------------------------------------",
        "// THE FOLLOWING SECTION CONTAINS OPTIONS FOR DISTRIBUTED COMPUTING.",
        "//--------------------------------------------------------------------------------",
        "DATA (DISTRIBUTEDCOMPUTER, [CustomExpression,CustomExpression:1,Selected,NumberOfConnections,",
        "    NumberOfConnections:1,DSServerName,Enabled,Enabled:1,DistNumErrors,",
        "    DistMaxErrors,DistAuthInfoStored,DistAuthInfo,DistAuthInfo:1,DistAuthInfo:2,",
        "    CustomExpressionStr,CustomExpressionStr:1])",
        "{",
    ]
    for computer in config.computers:
        lines.append(
            f'"" "" "NO " {computer.connections} 0 "{computer.name.strip()}" '
            '"YES" "Unknown" 0 1 "NO " "" "" "" "" ""'
        )
    lines.extend(("}", ""))
    return "\n".join(lines)


def write_distributed_aux(path: Path, config: DistributedConfig) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_distributed_aux(config), encoding="utf-8", newline="\n")
    return path


def contingency_batch_bounds(total: int, batch_size: int) -> Iterator[tuple[int, int]]:
    """Yield zero-based [start, end) bounds without dropping boundary items."""
    if total < 0:
        raise ValueError("Total contingencies cannot be negative.")
    if batch_size < 1:
        raise ValueError("Batch size must be at least 1.")
    for start in range(0, total, batch_size):
        yield start, min(start + batch_size, total)


def split_sequence(values: Sequence[str], batch_size: int) -> list[list[str]]:
    return [list(values[start:end]) for start, end in contingency_batch_bounds(len(values), batch_size)]
