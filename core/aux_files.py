"""AUX-file categories and case-specific selection rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

MANUAL = "manual"
GENERIC_CONTINGENCY = "generic_contingency"
JOIN_ACTIVE_CONTINGENCY = "join_active_contingency"
GENERIC_CONTINGENCY_POST = "generic_contingency_post"
OPERATING_GUIDE = "operating_guide"
COMMON_STRUCTURE = "common_structure"

CATEGORY_LABELS = {
    MANUAL: "Manipulation",
    GENERIC_CONTINGENCY: "Generic contingency",
    JOIN_ACTIVE_CONTINGENCY: "Join-active contingency",
    GENERIC_CONTINGENCY_POST: "Generic contingency (post)",
    OPERATING_GUIDE: "Operating guides",
    COMMON_STRUCTURE: "Common structure",
}
CATEGORY_ORDER = tuple(CATEGORY_LABELS)

NETWORK_ROOT = (
    r"\\mbu.ad.dominionnet.com\data\TRANSMISSION OPERATIONS CENTER\7T\Data2"
    r"\DESC_Trans_Planning\LTR_Basecases\Current Cases"
)


@dataclass(slots=True)
class AuxFileEntry:
    path: str
    apply_to_all: bool = True
    cases: list[str] = field(default_factory=list)

    @property
    def exists(self) -> bool:
        return Path(self.path).is_file()

    def applies_to(self, case_path: str) -> bool:
        return self.apply_to_all or case_path in self.cases

    def validate(self) -> None:
        if not self.path.strip():
            raise ValueError("AUX file paths cannot be blank.")


def empty_aux_selections() -> dict[str, list[dict[str, object]]]:
    return {category: [] for category in CATEGORY_ORDER}


def default_aux_selections(case_paths: Iterable[str] = ()) -> dict[str, list[dict[str, object]]]:
    del case_paths  # Defaults intentionally apply to present and future cases.
    mapped_generic = Path(r"G:\LTR_Basecases\Current Cases\AUX Cont\External Combinable Conts.aux")
    generic_path = str(mapped_generic) if mapped_generic.is_file() else (
        NETWORK_ROOT + r"\AUX Cont\External Combinable Conts.aux"
    )
    defaults = empty_aux_selections()
    paths = {
        MANUAL: NETWORK_ROOT + r"\AUX Manipulating\2Filters&Monitor_Settings&EquivalenceVACAR&SOCO.aux",
        GENERIC_CONTINGENCY: generic_path,
        JOIN_ACTIVE_CONTINGENCY: NETWORK_ROOT + r"\AUX Cont\P2+Switching.aux",
        GENERIC_CONTINGENCY_POST: NETWORK_ROOT + r"\AUX Cont\External NONCombinable Conts.aux",
        OPERATING_GUIDE: NETWORK_ROOT + r"\AUX Op Guide\OpGuides_P3&P6.aux",
    }
    for category, path in paths.items():
        defaults[category].append({"path": path, "apply_to_all": True, "cases": []})
    return defaults


def decode_entries(records: Iterable[dict[str, object]]) -> list[AuxFileEntry]:
    entries: list[AuxFileEntry] = []
    for record in records:
        entry = AuxFileEntry(
            path=str(record.get("path", "")),
            apply_to_all=bool(record.get("apply_to_all", True)),
            cases=[str(value) for value in record.get("cases", [])],
        )
        entry.validate()
        entries.append(entry)
    return entries


def encode_entries(entries: Iterable[AuxFileEntry]) -> list[dict[str, object]]:
    return [
        {"path": entry.path, "apply_to_all": entry.apply_to_all, "cases": list(entry.cases)}
        for entry in entries
    ]


def paths_for_case(
    selections: dict[str, list[dict[str, object]]], category: str, case_path: str
) -> list[str]:
    return [entry.path for entry in decode_entries(selections.get(category, [])) if entry.applies_to(case_path)]
