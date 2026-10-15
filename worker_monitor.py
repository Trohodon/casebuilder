"""Non-intrusive process monitor for distributed PowerWorld computers."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import queue
import threading
import tkinter as tk
from tkinter import ttk

from core.process_monitor import (
    ComputerProcessSnapshot,
    process_count_status,
    query_simulator_processes,
)
from core.settings import AppSettings


NAVY = "#0B2F5B"
LIGHT_BLUE = "#DCE7F5"


class WorkerMonitor(tk.Toplevel):
    def __init__(self, parent: tk.Misc, settings: AppSettings) -> None:
        super().__init__(parent)
        self.title("Distributed Worker Monitor")
        self.geometry("1120x680")
        self.minsize(900, 560)
        self.transient(parent)

        self.computers = [
            (str(item.get("name", "")).strip(), int(item.get("cores", item.get("connections", 0))))
            for item in settings.distributed_computers
            if str(item.get("name", "")).strip()
        ]
        self.snapshots: dict[str, ComputerProcessSnapshot] = {}
        self._result_queue: queue.Queue[tuple[list[ComputerProcessSnapshot], str]] = queue.Queue()
        self._refreshing = False
        self._after_id: str | None = None
        self.auto_var = tk.BooleanVar(value=True)
        self.interval_var = tk.StringVar(value="10")
        self.updated_var = tk.StringVar(value="Not checked")
        self.summary_var = tk.StringVar(value="Ready to check configured computers")

        self.protocol("WM_DELETE_WINDOW", self._close)
        self._build()
        self.after(100, self.refresh)

    def _build(self) -> None:
        header = tk.Frame(self, bg=NAVY)
        header.pack(fill="x")
        tk.Label(
            header,
            text="Distributed Worker Monitor",
            bg=NAVY,
            fg="white",
            font=("Segoe UI", 15, "bold"),
            padx=14,
            pady=10,
        ).pack(side="left")
        tk.Label(
            header,
            text="Read-only view of pwrworld.exe / Simulator Release processes",
            bg=NAVY,
            fg=LIGHT_BLUE,
            font=("Segoe UI", 10),
            padx=8,
        ).pack(side="left")

        body = ttk.Frame(self, padding=12)
        body.pack(fill="both", expand=True)

        controls = ttk.Frame(body)
        controls.pack(fill="x", pady=(0, 8))
        self.refresh_button = ttk.Button(controls, text="Refresh Now", command=self.refresh)
        self.refresh_button.pack(side="left")
        ttk.Checkbutton(
            controls,
            text="Auto refresh",
            variable=self.auto_var,
            command=self._schedule_next,
        ).pack(side="left", padx=(14, 5))
        ttk.Label(controls, text="every").pack(side="left")
        ttk.Combobox(
            controls,
            textvariable=self.interval_var,
            values=("5", "10", "30", "60"),
            width=5,
            state="readonly",
        ).pack(side="left", padx=5)
        ttk.Label(controls, text="seconds").pack(side="left")
        ttk.Label(controls, textvariable=self.updated_var).pack(side="right")

        ttk.Label(body, textvariable=self.summary_var, font=("Segoe UI", 10, "bold")).pack(
            fill="x", pady=(0, 8)
        )

        overview_frame = ttk.LabelFrame(body, text="All configured computers", padding=8)
        overview_frame.pack(fill="both", expand=True)
        self.overview = ttk.Treeview(
            overview_frame,
            columns=("computer", "requested", "processes", "state"),
            show="headings",
            height=12,
        )
        for column, label, width, anchor in (
            ("computer", "Computer", 210, "w"),
            ("requested", "Requested workers", 125, "center"),
            ("processes", "Simulator processes", 130, "center"),
            ("state", "Monitor status", 520, "w"),
        ):
            self.overview.heading(column, text=label)
            self.overview.column(column, width=width, anchor=anchor)
        overview_scroll = ttk.Scrollbar(
            overview_frame, orient="vertical", command=self.overview.yview
        )
        self.overview.configure(yscrollcommand=overview_scroll.set)
        self.overview.pack(side="left", fill="both", expand=True)
        overview_scroll.pack(side="right", fill="y")
        self.overview.tag_configure("ready", foreground="#176B2C")
        self.overview.tag_configure("partial", foreground="#9A6700")
        self.overview.tag_configure("none", foreground="#8A3B12")
        self.overview.tag_configure("error", foreground="#A61B1B")
        self.overview.bind("<<TreeviewSelect>>", self._show_selected_details)

        details_frame = ttk.LabelFrame(body, text="Processes on selected computer", padding=8)
        details_frame.pack(fill="both", expand=True, pady=(10, 0))
        self.details = ttk.Treeview(
            details_frame,
            columns=("pid", "session", "memory", "status", "user", "cpu", "title"),
            show="headings",
            height=7,
        )
        for column, label, width in (
            ("pid", "PID", 70),
            ("session", "Session", 100),
            ("memory", "Memory", 95),
            ("status", "Status", 90),
            ("user", "User", 165),
            ("cpu", "CPU time", 90),
            ("title", "Window title", 300),
        ):
            self.details.heading(column, text=label)
            self.details.column(column, width=width, anchor="w")
        detail_scroll = ttk.Scrollbar(details_frame, orient="vertical", command=self.details.yview)
        self.details.configure(yscrollcommand=detail_scroll.set)
        self.details.pack(side="left", fill="both", expand=True)
        detail_scroll.pack(side="right", fill="y")

        ttk.Label(
            body,
            text=(
                "This uses the current Windows account and does not open remote desktop sessions. "
                "Extra processes can belong to another user or job; select a computer to inspect them."
            ),
            foreground="#555555",
        ).pack(fill="x", pady=(8, 0))

        for name, requested in self.computers:
            self.overview.insert(
                "", "end", iid=name.casefold(), values=(name, requested, "-", "Not checked")
            )
        if self.computers:
            first = self.computers[0][0].casefold()
            self.overview.selection_set(first)
            self.overview.focus(first)

    def refresh(self) -> None:
        if self._refreshing or not self.winfo_exists():
            return
        self._cancel_scheduled()
        self._refreshing = True
        self.refresh_button.state(("disabled",))
        self.updated_var.set("Checking computers...")
        for name, requested in self.computers:
            item = name.casefold()
            if self.overview.exists(item):
                self.overview.item(item, values=(name, requested, "-", "Checking..."), tags=())

        def collect() -> None:
            snapshots: list[ComputerProcessSnapshot] = []
            workers = max(1, min(6, len(self.computers)))
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {
                    executor.submit(query_simulator_processes, name): name
                    for name, _requested in self.computers
                }
                for future in as_completed(futures):
                    name = futures[future]
                    try:
                        snapshots.append(future.result())
                    except Exception as exc:
                        snapshots.append(ComputerProcessSnapshot(name, error=str(exc)))
            self._result_queue.put((snapshots, datetime.now().strftime("%H:%M:%S")))

        threading.Thread(target=collect, daemon=True).start()
        self.after(100, self._poll_results)

    def _poll_results(self) -> None:
        if not self.winfo_exists():
            return
        try:
            snapshots, checked_at = self._result_queue.get_nowait()
        except queue.Empty:
            self.after(100, self._poll_results)
            return
        self.snapshots = {snapshot.computer.casefold(): snapshot for snapshot in snapshots}
        total_processes = 0
        reachable = 0
        for name, requested in self.computers:
            snapshot = self.snapshots.get(name.casefold(), ComputerProcessSnapshot(name, error="No result"))
            count = len(snapshot.processes)
            total_processes += count
            if snapshot.error:
                tag = "error"
            else:
                reachable += 1
                tag = "ready" if count >= requested else ("partial" if count else "none")
            self.overview.item(
                name.casefold(),
                values=(name, requested, count, process_count_status(snapshot, requested)),
                tags=(tag,),
            )
        self.summary_var.set(
            f"{total_processes} Simulator process(es) found across "
            f"{reachable} of {len(self.computers)} monitored computers"
        )
        self.updated_var.set(f"Last refreshed: {checked_at}")
        self._refreshing = False
        self.refresh_button.state(("!disabled",))
        self._show_selected_details()
        self._schedule_next()

    def _show_selected_details(self, _event=None) -> None:
        self.details.delete(*self.details.get_children())
        selected = self.overview.selection()
        if not selected:
            return
        snapshot = self.snapshots.get(selected[0])
        if snapshot is None:
            return
        for process in snapshot.processes:
            session = process.session_name
            if process.session_number:
                session = f"{session} ({process.session_number})"
            self.details.insert(
                "",
                "end",
                values=(
                    process.pid,
                    session,
                    process.memory,
                    process.status,
                    process.username,
                    process.cpu_time,
                    process.window_title,
                ),
            )

    def _cancel_scheduled(self) -> None:
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None

    def _schedule_next(self) -> None:
        self._cancel_scheduled()
        if not self.auto_var.get() or self._refreshing or not self.winfo_exists():
            return
        try:
            milliseconds = max(5, int(self.interval_var.get())) * 1000
        except ValueError:
            milliseconds = 10_000
        self._after_id = self.after(milliseconds, self.refresh)

    def _close(self) -> None:
        self.auto_var.set(False)
        self._cancel_scheduled()
        self.destroy()

