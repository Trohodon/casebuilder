"""Small, testable case-preparation workflows used by the GUI buttons."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

from .powerworld import PowerWorldClient, PowerWorldError

LogCallback = Callable[[str], None]


def default_prepared_case_path(case_path: str | Path, suffix: str) -> Path:
    case = Path(case_path)
    return case.with_name(f"{case.stem}{suffix}.PWB")


def apply_input_file(client: PowerWorldClient, path: str | Path) -> None:
    source = Path(path)
    if source.suffix.casefold() == ".con":
        client.read_pti_contingencies(source)
    else:
        client.process_aux_file(source)


def prepare_case(
    client: PowerWorldClient,
    case_path: str | Path,
    output_path: str | Path,
    input_files: Iterable[str | Path],
    *,
    log: LogCallback | None = None,
) -> Path:
    """Open a case, apply ordered AUX/CON files, save a PWB, and close it."""
    source = Path(case_path)
    destination = Path(output_path)
    write_log = log or (lambda _message: None)
    if not source.is_file():
        raise PowerWorldError(f"The case file does not exist: {source}")

    opened = False
    try:
        write_log(f"Opening case: {source}")
        client.open_case(source)
        opened = True
        for input_file in input_files:
            write_log(f"Applying file: {input_file}")
            apply_input_file(client, input_file)
        write_log(f"Saving prepared case: {destination}")
        client.save_case(destination, "PWB", True)
        return destination
    finally:
        if opened:
            try:
                client.close_case()
            except PowerWorldError as exc:
                write_log(f"Warning: {exc}")
