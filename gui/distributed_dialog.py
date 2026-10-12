from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from core.distributed import DistributedComputer, DistributedConfig, write_distributed_aux
from core.settings import AppSettings, SettingsStore


class DistributedDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, settings: AppSettings, store: SettingsStore) -> None:
        super().__init__(parent)
        self.settings = settings
        self.store = store
        self.title("Distributed Computing")
        self.geometry("650x430")
        self.transient(parent)
        self.grab_set()

        self.ctg_var = tk.StringVar(value=str(settings.contingencies_per_process))
        self.name_var = tk.StringVar()
        self.connections_var = tk.StringVar(value="1")

        top = ttk.Frame(self, padding=12)
        top.pack(fill="both", expand=True)
        ttk.Label(top, text="Contingencies per process").grid(row=0, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.ctg_var, width=12).grid(row=0, column=1, sticky="w", padx=8)

        self.tree = ttk.Treeview(top, columns=("name", "connections"), show="headings", height=10)
        self.tree.heading("name", text="Computer")
        self.tree.heading("connections", text="Connections")
        self.tree.column("name", width=320)
        self.tree.column("connections", width=110, anchor="center")
        self.tree.grid(row=1, column=0, columnspan=4, sticky="nsew", pady=10)
        top.rowconfigure(1, weight=1)
        top.columnconfigure(2, weight=1)

        ttk.Entry(top, textvariable=self.name_var, width=28).grid(row=2, column=0, sticky="ew")
        ttk.Entry(top, textvariable=self.connections_var, width=10).grid(row=2, column=1, padx=8)
        ttk.Button(top, text="Add", command=self._add).grid(row=2, column=2, sticky="w")
        ttk.Button(top, text="Remove selected", command=self._remove).grid(row=2, column=3, sticky="e")

        buttons = ttk.Frame(top)
        buttons.grid(row=3, column=0, columnspan=4, sticky="e", pady=(14, 0))
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(buttons, text="Save AUX", command=self._save).pack(side="right", padx=8)

        for item in settings.distributed_computers:
            self.tree.insert("", "end", values=(item["name"], item["connections"]))

    def _add(self) -> None:
        try:
            computer = DistributedComputer(self.name_var.get(), int(self.connections_var.get()))
            computer.validate()
        except ValueError as exc:
            messagebox.showerror("Invalid computer", str(exc), parent=self)
            return
        self.tree.insert("", "end", values=(computer.name.strip(), computer.connections))
        self.name_var.set("")
        self.connections_var.set("1")

    def _remove(self) -> None:
        for item in self.tree.selection():
            self.tree.delete(item)

    def _save(self) -> None:
        try:
            computers = tuple(
                DistributedComputer(str(values[0]), int(values[1]))
                for item in self.tree.get_children()
                if (values := self.tree.item(item, "values"))
            )
            config = DistributedConfig(int(self.ctg_var.get()), computers)
            config.validate()
            write_distributed_aux(self.store.distributed_aux_path, config)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Distributed computing", str(exc), parent=self)
            return

        self.settings.contingencies_per_process = config.contingencies_per_process
        self.settings.distributed_computers = [
            {"name": computer.name.strip(), "connections": computer.connections}
            for computer in config.computers
        ]
        self.store.save(self.settings)
        messagebox.showinfo(
            "Distributed computing",
            f"Wrote {self.store.distributed_aux_path}",
            parent=self,
        )
        self.destroy()
