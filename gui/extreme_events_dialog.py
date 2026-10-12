from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from core.settings import AppSettings, SettingsStore


class ExtremeEventsDialog(tk.Toplevel):
    """Small selector matching the four choices in the legacy program."""

    def __init__(
        self,
        parent: tk.Misc,
        settings: AppSettings,
        store: SettingsStore,
        on_saved=None,
    ) -> None:
        super().__init__(parent)
        self.settings = settings
        self.store = store
        self.on_saved = on_saved
        self.title("Choose Extreme Events")
        self.geometry("430x285")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.double_bus_var = tk.BooleanVar(value=settings.extreme_double_bus)
        self.double_branch_var = tk.BooleanVar(value=settings.extreme_double_branch)
        self.bus_branch_var = tk.BooleanVar(value=settings.extreme_bus_branch)
        self.p1_p7_var = tk.BooleanVar(value=settings.extreme_p1_p7)

        body = ttk.Frame(self, padding=18)
        body.pack(fill="both", expand=True)
        ttk.Label(
            body,
            text="Choose the extreme-event contingency groups to include.",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(0, 12))

        ttk.Checkbutton(body, text="Double Bus", variable=self.double_bus_var).pack(anchor="w", pady=3)
        ttk.Checkbutton(body, text="Double Branch", variable=self.double_branch_var).pack(anchor="w", pady=3)
        ttk.Checkbutton(body, text="Bus + Branch", variable=self.bus_branch_var).pack(anchor="w", pady=3)
        ttk.Checkbutton(
            body,
            text="P1 + P7 (Common Structure)",
            variable=self.p1_p7_var,
        ).pack(anchor="w", pady=3)

        buttons = ttk.Frame(body)
        buttons.pack(fill="x", side="bottom", pady=(14, 0))
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(buttons, text="OK", command=self._save).pack(side="right", padx=8)

    def _save(self) -> None:
        self.settings.extreme_double_bus = self.double_bus_var.get()
        self.settings.extreme_double_branch = self.double_branch_var.get()
        self.settings.extreme_bus_branch = self.bus_branch_var.get()
        self.settings.extreme_p1_p7 = self.p1_p7_var.get()
        self.store.save(self.settings)
        if self.on_saved is not None:
            self.on_saved(self.selected_count())
        self.destroy()

    def selected_count(self) -> int:
        return sum(
            (
                self.double_bus_var.get(),
                self.double_branch_var.get(),
                self.bus_branch_var.get(),
                self.p1_p7_var.get(),
            )
        )
