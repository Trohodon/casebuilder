"""Read-only monitoring of PowerWorld processes on configured computers."""

from __future__ import annotations

import csv
from dataclasses import dataclass
import os
import platform
import socket
import subprocess
from typing import Callable


@dataclass(frozen=True, slots=True)
class SimulatorProcess:
    image_name: str
    pid: int
    session_name: str
    session_number: str
    memory: str
    status: str
    username: str
    cpu_time: str
    window_title: str


@dataclass(frozen=True, slots=True)
class ComputerProcessSnapshot:
    computer: str
    processes: tuple[SimulatorProcess, ...] = ()
    error: str = ""


def is_local_computer(name: str) -> bool:
    computer = name.strip().casefold()
    local_names = {
        "localhost",
        ".",
        socket.gethostname().casefold(),
        socket.getfqdn().casefold(),
        os.environ.get("COMPUTERNAME", "").casefold(),
    }
    return computer in local_names


def tasklist_command(computer: str) -> list[str]:
    command = ["tasklist"]
    if not is_local_computer(computer):
        command.extend(("/S", computer.strip()))
    command.extend(("/V", "/FI", "IMAGENAME eq pwrworld.exe", "/FO", "CSV", "/NH"))
    return command


def parse_tasklist_csv(output: str) -> tuple[SimulatorProcess, ...]:
    processes: list[SimulatorProcess] = []
    for row in csv.reader(output.splitlines()):
        if len(row) < 9 or row[0].strip().casefold() != "pwrworld.exe":
            continue
        try:
            pid = int(row[1].strip())
        except ValueError:
            continue
        processes.append(
            SimulatorProcess(
                image_name=row[0].strip(),
                pid=pid,
                session_name=row[2].strip(),
                session_number=row[3].strip(),
                memory=row[4].strip(),
                status=row[5].strip(),
                username=row[6].strip(),
                cpu_time=row[7].strip(),
                window_title=row[8].strip(),
            )
        )
    return tuple(processes)


def query_simulator_processes(
    computer: str,
    *,
    timeout_seconds: float = 12.0,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    system_name: str | None = None,
) -> ComputerProcessSnapshot:
    name = computer.strip()
    if not name:
        return ComputerProcessSnapshot(computer, error="Blank computer name")
    if (system_name or platform.system()) != "Windows":
        return ComputerProcessSnapshot(name, error="Remote process monitoring requires Windows")

    try:
        completed = runner(
            tasklist_command(name),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired:
        return ComputerProcessSnapshot(name, error=f"Timed out after {timeout_seconds:g} seconds")
    except OSError as exc:
        return ComputerProcessSnapshot(name, error=f"Could not run tasklist: {exc}")

    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "tasklist failed").strip()
        return ComputerProcessSnapshot(name, error=detail)
    return ComputerProcessSnapshot(name, parse_tasklist_csv(completed.stdout or ""))


def process_count_status(snapshot: ComputerProcessSnapshot, requested_workers: int) -> str:
    if snapshot.error:
        return f"Monitoring unavailable - {snapshot.error}"
    count = len(snapshot.processes)
    if count == 0:
        return "No Simulator processes"
    if count < requested_workers:
        return f"{count} process(es) - below {requested_workers} requested"
    if count == requested_workers:
        return f"{count} process(es) - requested count reached"
    return f"{count} process(es) - includes {count - requested_workers} additional"
