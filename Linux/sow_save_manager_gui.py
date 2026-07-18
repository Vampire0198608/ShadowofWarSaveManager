#!/usr/bin/env python3
"""
Shadow of War Save Manager (GUI)
==================================

A Tkinter-based tool for organizing save backups into playthroughs,
and backing up / restoring them. Auto-detects Steam, GOG, and
Microsoft Store installs where possible.

Known save locations this tool looks for:
    Steam:        <Steam folder>\\userdata\\<id>\\356190\\remote\\
    GOG:          %LOCALAPPDATA%\\WB Games\\Shadow of War\\
    MS Store:     %LOCALAPPDATA%\\Packages\\6DA520A3...\\SystemAppData\\wgs\\

Config and playthroughs/backups are stored under your home folder in:
    ~/ShadowOfWarSaveManager/

Run with:
    python sow_save_manager_gui.py
"""

import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk, filedialog, messagebox, simpledialog

APP_DIR = Path.home() / "ShadowOfWarSaveManager"
CONFIG_PATH = APP_DIR / "config.json"
PLAYTHROUGHS_DIR = APP_DIR / "playthroughs"
LEGACY_BACKUPS_DIR = APP_DIR / "backups"  # used by older version of this tool

STEAM_APP_ID = "356190"
DEFAULT_PLAYTHROUGH_NAME = "Default"

INVALID_NAME_CHARS = r'\/:*?"<>|'

BACKUP_META_FILENAME = "_backup_meta.json"

GAME_LOCATIONS = [
    "(none)",
    "Seregost",
    "Nurnen",
    "Cirith Ungol",
    "Minas Ithil",
    "Gorgoroth",
    "Lithlad",
]

DLC_CAMPAIGNS = [
    "The Blade of Galadriel",
    "The Desolation of Mordor",
]


# ---------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------

def find_steam_path():
    """Try the Windows registry first, then fall back to common install locations
    for both Windows and Linux (including Flatpak Steam, common on distros
    like CachyOS)."""
    if os.name == "nt":
        try:
            import winreg
            reg_targets = [
                (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
            ]
            for hive, subkey, value_name in reg_targets:
                try:
                    with winreg.OpenKey(hive, subkey) as key:
                        value, _ = winreg.QueryValueEx(key, value_name)
                        p = Path(value)
                        if p.exists():
                            return p
                except OSError:
                    continue
        except ImportError:
            pass

        guesses = []
        for drive in ["C", "D", "E", "F"]:
            guesses.append(Path(f"{drive}:/Program Files (x86)/Steam"))
            guesses.append(Path(f"{drive}:/Program Files/Steam"))
            guesses.append(Path(f"{drive}:/Steam"))
            guesses.append(Path(f"{drive}:/SteamLibrary"))
        for g in guesses:
            if g.exists():
                return g
        return None

    # Linux (native package, or Flatpak) — covers Arch/CachyOS-style installs.
    home = Path.home()
    guesses = [
        home / ".steam" / "steam",
        home / ".steam" / "root",
        home / ".local" / "share" / "Steam",
        home / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam",
        home / ".var" / "app" / "com.valvesoftware.Steam" / "data" / "Steam",
    ]
    for g in guesses:
        if (g / "steamapps").exists() or (g / "userdata").exists():
            return g
    return None


def find_steam_proton_save_dir():
    """Locate the local (non-Cloud) save folder inside a game's Proton prefix,
    for when Steam Cloud sync isn't used or hasn't run yet on this machine."""
    steam_path = find_steam_path()
    if not steam_path:
        return None
    candidate = (
        steam_path
        / "steamapps"
        / "compatdata"
        / STEAM_APP_ID
        / "pfx"
        / "drive_c"
        / "users"
        / "steamuser"
        / "Documents"
        / "My Games"
        / "Shadow of War"
    )
    return candidate if candidate.exists() else None


def find_steam_save_dirs():
    candidates = []  # list of (kind, path)

    steam_path = find_steam_path()
    if steam_path:
        userdata = steam_path / "userdata"
        if userdata.exists():
            for user_folder in userdata.iterdir():
                candidate = user_folder / STEAM_APP_ID / "remote"
                if candidate.exists():
                    candidates.append(("Cloud sync folder", candidate))

    proton_dir = find_steam_proton_save_dir()
    if proton_dir:
        candidates.append(("Proton local files", proton_dir))

    if not candidates:
        return []
    if len(candidates) == 1:
        return [("Steam", candidates[0][1])]

    # More than one match (e.g. multiple Steam accounts, or both a Cloud
    # sync folder and a local Proton prefix) — label each so they're
    # distinguishable in the dropdown.
    return [(f"Steam ({kind})", path) for kind, path in candidates]


def find_gog_save_dir():
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        p = Path(local_appdata) / "WB Games" / "Shadow of War"
        if p.exists():
            return p
    return None


def find_ms_store_save_dir():
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        packages = Path(local_appdata) / "Packages"
        if packages.exists():
            for folder in packages.glob("6DA520A3.1673586F56C6C*"):
                candidate = folder / "SystemAppData" / "wgs"
                if candidate.exists():
                    return candidate
    return None


def detect_installations():
    """Return save-folder candidates, but only for versions actually confirmed installed.

    A save folder can be left behind even after a version is uninstalled (or
    could be stale/shared from another WB Games title), so this cross-checks
    against the same install-detection used for the Launch button rather
    than just checking whether the folder happens to exist.
    """
    found = []

    if find_steam_install_exe_check():
        found.extend(find_steam_save_dirs())

    if find_gog_install_exe():
        gog_dir = find_gog_save_dir()
        if gog_dir:
            found.append(("GOG (WB Games folder)", gog_dir))

    ms_dir = find_ms_store_save_dir()
    if ms_dir:
        found.append(("Microsoft Store", ms_dir))
    return found


# ---------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------

def load_config():
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def save_config(cfg):
    APP_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))


def load_backup_meta(backup_path: Path):
    meta_path = backup_path / BACKUP_META_FILENAME
    if meta_path.exists():
        try:
            return json.loads(meta_path.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def save_backup_meta(backup_path: Path, meta: dict):
    meta_path = backup_path / BACKUP_META_FILENAME
    meta_path.write_text(json.dumps(meta, indent=2))


def ask_choice(parent, title, prompt, choices, initial=None):
    """Show a small modal dialog with a dropdown and OK/Cancel. Returns the chosen
    string, or None if cancelled. (tkinter's simpledialog has no built-in combobox
    prompt, so this fills that gap.)"""
    result = {"value": None}

    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.transient(parent)
    dialog.resizable(False, False)
    dialog.grab_set()

    ttk.Label(dialog, text=prompt, padding=(12, 12, 12, 4)).pack(anchor="w")

    var = tk.StringVar(value=initial if initial in choices else choices[0])
    combo = ttk.Combobox(dialog, textvariable=var, values=choices, state="readonly", width=30)
    combo.pack(padx=12, pady=(0, 12), fill="x")

    def on_ok():
        result["value"] = var.get()
        dialog.destroy()

    def on_cancel():
        dialog.destroy()

    btn_frame = ttk.Frame(dialog)
    btn_frame.pack(pady=(0, 12), padx=12, fill="x")
    ttk.Button(btn_frame, text="OK", command=on_ok).pack(side="right", padx=(4, 0))
    ttk.Button(btn_frame, text="Cancel", command=on_cancel).pack(side="right")

    dialog.protocol("WM_DELETE_WINDOW", on_cancel)
    dialog.update_idletasks()

    # Center over the parent window
    x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (dialog.winfo_width() // 2)
    y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (dialog.winfo_height() // 2)
    dialog.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    dialog.wait_window()
    return result["value"]


def ask_checklist(parent, title, prompt, items, initial=None):
    """Show a small modal dialog with a checkbox per item, plus OK/Cancel.
    Returns a dict of {item: bool}, or None if cancelled."""
    initial = initial or {}
    result = {"values": None}

    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.transient(parent)
    dialog.resizable(False, False)
    dialog.grab_set()

    ttk.Label(dialog, text=prompt, padding=(12, 12, 12, 4)).pack(anchor="w")

    check_vars = {}
    for item in items:
        var = tk.BooleanVar(value=initial.get(item, False))
        check_vars[item] = var
        ttk.Checkbutton(dialog, text=item, variable=var).pack(anchor="w", padx=16)

    def on_ok():
        result["values"] = {item: var.get() for item, var in check_vars.items()}
        dialog.destroy()

    def on_cancel():
        dialog.destroy()

    btn_frame = ttk.Frame(dialog)
    btn_frame.pack(pady=(12, 12), padx=12, fill="x")
    ttk.Button(btn_frame, text="OK", command=on_ok).pack(side="right", padx=(4, 0))
    ttk.Button(btn_frame, text="Cancel", command=on_cancel).pack(side="right")

    dialog.protocol("WM_DELETE_WINDOW", on_cancel)
    dialog.update_idletasks()

    x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (dialog.winfo_width() // 2)
    y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (dialog.winfo_height() // 2)
    dialog.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    dialog.wait_window()
    return result["values"]


# ---------------------------------------------------------------------
# Playthrough helpers
# ---------------------------------------------------------------------

def validate_playthrough_name(name):
    """Return an error string if invalid, or None if OK."""
    name = name.strip() if name else ""
    if not name:
        return "Name cannot be empty."
    if any(ch in INVALID_NAME_CHARS for ch in name):
        return f"Name cannot contain any of: {INVALID_NAME_CHARS}"
    if name in (".", ".."):
        return "Invalid name."
    return None


def ensure_playthroughs_exist():
    """Set up the playthroughs folder, migrating old flat backups if present."""
    PLAYTHROUGHS_DIR.mkdir(parents=True, exist_ok=True)
    existing = [d for d in PLAYTHROUGHS_DIR.iterdir() if d.is_dir()]
    if existing:
        return

    default_dir = PLAYTHROUGHS_DIR / DEFAULT_PLAYTHROUGH_NAME
    if LEGACY_BACKUPS_DIR.exists() and any(LEGACY_BACKUPS_DIR.iterdir()):
        shutil.move(str(LEGACY_BACKUPS_DIR), str(default_dir))
    else:
        default_dir.mkdir(parents=True, exist_ok=True)


def list_playthroughs():
    if not PLAYTHROUGHS_DIR.exists():
        return []
    return sorted(d.name for d in PLAYTHROUGHS_DIR.iterdir() if d.is_dir())


def find_gog_install_exe():
    """Best-effort search of the registry for a GOG install of Shadow of War, returning its exe path."""
    if os.name != "nt":
        return None
    try:
        import winreg
    except ImportError:
        return None

    base = r"SOFTWARE\WOW6432Node\GOG.com\Games"
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            games_key = winreg.OpenKey(hive, base)
        except OSError:
            continue

        with games_key:
            index = 0
            while True:
                try:
                    subkey_name = winreg.EnumKey(games_key, index)
                except OSError:
                    break
                index += 1

                try:
                    with winreg.OpenKey(games_key, subkey_name) as game_key:
                        try:
                            game_name, _ = winreg.QueryValueEx(game_key, "gameName")
                        except OSError:
                            game_name = ""

                        if "shadow of war" not in game_name.lower():
                            continue

                        try:
                            path_val, _ = winreg.QueryValueEx(game_key, "path")
                        except OSError:
                            continue
                        install_path = Path(path_val)
                        if not install_path.exists():
                            continue

                        exe_val = None
                        for value_name in ("exe", "EXE", "launchCommand"):
                            try:
                                exe_val, _ = winreg.QueryValueEx(game_key, value_name)
                                break
                            except OSError:
                                continue

                        if exe_val:
                            exe_path = Path(exe_val)
                            if not exe_path.is_absolute():
                                exe_path = install_path / exe_path
                            if exe_path.exists():
                                return exe_path

                        # Fall back to guessing: pick the first non-uninstaller exe.
                        for candidate in install_path.glob("*.exe"):
                            if "unins" not in candidate.name.lower():
                                return candidate
                except OSError:
                    continue
    return None


def find_steam_install_exe_check():
    """Return True if a Steam install of Shadow of War (appmanifest) can be found."""
    steam_path = find_steam_path()
    if not steam_path:
        return False
    manifest = steam_path / "steamapps" / f"appmanifest_{STEAM_APP_ID}.acf"
    return manifest.exists()


def detect_launch_options():
    """Return a list of (label, kind, value) tuples. kind is 'steam' or 'exe'."""
    options = []
    if find_steam_install_exe_check():
        options.append(("Steam", "steam", None))
    gog_exe = find_gog_install_exe()
    if gog_exe:
        options.append((f"GOG — {gog_exe}", "exe", gog_exe))
    return options


def open_in_file_explorer(path: Path):
    """Open the given folder in the OS's file browser (Explorer/Finder/etc.)."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif system == "Darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
        return True
    except Exception as exc:
        messagebox.showerror("Couldn't open folder", f"Could not open:\n{path}\n\n{exc}")
        return False


# ---------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------

class SaveManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Shadow of War Save Manager")
        self.root.geometry("780x580")
        self.root.minsize(700, 500)

        self.save_path = None
        self.detected = []
        self.current_playthrough = None
        self.launch_options = []

        ensure_playthroughs_exist()

        self._build_ui()
        self._load_playthroughs(select=self._load_last_playthrough_name())
        self._load_saved_path_or_detect()
        self._redetect_launch_options()
        self._on_launch_selected()

    # ---------------- UI construction ----------------

    def _build_ui(self):
        # --- Save folder row ---
        top = ttk.Frame(self.root, padding=(10, 10, 10, 4))
        top.pack(fill="x")

        ttk.Label(top, text="Save folder:").pack(side="left")
        self.path_var = tk.StringVar(value="(not set)")
        self.path_combo = ttk.Combobox(top, textvariable=self.path_var, width=55, state="readonly")
        self.path_combo.pack(side="left", padx=6)
        self.path_combo.bind("<<ComboboxSelected>>", self._on_combo_selected)

        ttk.Button(top, text="Detect", command=self._redetect).pack(side="left", padx=3)
        ttk.Button(top, text="Browse...", command=self._browse_path).pack(side="left", padx=3)
        ttk.Button(top, text="Open folder", command=self._open_save_folder).pack(side="left", padx=3)

        # --- Launch game row ---
        launch_frame = ttk.Frame(self.root, padding=(10, 0, 10, 4))
        launch_frame.pack(fill="x")

        ttk.Label(launch_frame, text="Launch via:").pack(side="left")
        self.launch_var = tk.StringVar(value="(none detected)")
        self.launch_combo = ttk.Combobox(launch_frame, textvariable=self.launch_var, width=45, state="readonly")
        self.launch_combo.pack(side="left", padx=6)
        self.launch_combo.bind("<<ComboboxSelected>>", self._on_launch_selected)

        ttk.Button(launch_frame, text="Redetect", command=self._redetect_launch_options).pack(side="left", padx=3)
        ttk.Button(launch_frame, text="Set custom .exe...", command=self._browse_game_exe).pack(side="left", padx=3)
        ttk.Button(launch_frame, text="Launch Game", command=self._do_launch).pack(side="left", padx=(10, 0))

        # --- Playthrough box ---
        pt_frame = ttk.LabelFrame(self.root, text="Playthrough", padding=10)
        pt_frame.pack(fill="x", padx=10, pady=(6, 4))

        self.playthrough_var = tk.StringVar()
        self.playthrough_combo = ttk.Combobox(
            pt_frame, textvariable=self.playthrough_var, width=30, state="readonly",
        )
        self.playthrough_combo.pack(side="left")
        self.playthrough_combo.bind("<<ComboboxSelected>>", self._on_playthrough_selected)

        ttk.Button(pt_frame, text="Create...", command=self._create_playthrough).pack(side="left", padx=4)
        ttk.Button(pt_frame, text="Rename...", command=self._rename_playthrough).pack(side="left", padx=4)
        ttk.Button(pt_frame, text="Delete", command=self._delete_playthrough).pack(side="left", padx=4)
        ttk.Button(pt_frame, text="Open backup folder", command=self._open_playthrough_folder).pack(side="left", padx=4)
        ttk.Button(pt_frame, text="Open all playthroughs...", command=self._open_playthroughs_root).pack(
            side="left", padx=4
        )

        # --- Main split: files / backups ---
        main = ttk.Frame(self.root, padding=(10, 4, 10, 10))
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(1, weight=1)

        ttk.Label(main, text="Current save files").grid(row=0, column=0, sticky="w")
        self.files_list = tk.Listbox(main)
        self.files_list.grid(row=1, column=0, sticky="nsew", padx=(0, 6), pady=4)

        left_btns = ttk.Frame(main)
        left_btns.grid(row=2, column=0, sticky="w", pady=(0, 4))
        ttk.Button(left_btns, text="Refresh", command=self._refresh_files).pack(side="left", padx=(0, 4))
        ttk.Button(left_btns, text="Backup current saves...", command=self._do_backup).pack(side="left")

        self.backups_label_var = tk.StringVar(value="Backups")
        ttk.Label(main, textvariable=self.backups_label_var).grid(row=0, column=1, sticky="w")
        self.backups_list = tk.Listbox(main)
        self.backups_list.grid(row=1, column=1, sticky="nsew", padx=(6, 0), pady=4)

        right_btns = ttk.Frame(main)
        right_btns.grid(row=2, column=1, sticky="w", pady=(0, 4))
        ttk.Button(right_btns, text="Refresh", command=self._refresh_backups).pack(side="left", padx=(0, 4))
        ttk.Button(right_btns, text="Restore selected", command=self._do_restore).pack(side="left", padx=(0, 4))
        ttk.Button(right_btns, text="Rename selected", command=self._rename_backup).pack(side="left", padx=(0, 4))
        ttk.Button(right_btns, text="Delete selected", command=self._do_delete).pack(side="left", padx=(0, 4))

        location_btns = ttk.Frame(main)
        location_btns.grid(row=3, column=1, sticky="w", pady=(0, 4))
        ttk.Button(location_btns, text="Set location...", command=self._set_backup_location).pack(side="left", padx=(0, 4))
        ttk.Button(location_btns, text="Set DLC status...", command=self._set_dlc_status).pack(side="left")

        info_frame = ttk.LabelFrame(main, text="Backup info", padding=8)
        info_frame.grid(row=4, column=1, sticky="ew", pady=(4, 0))
        self.info_var = tk.StringVar(value="Select a backup to see details.")
        ttk.Label(info_frame, textvariable=self.info_var, justify="left").pack(anchor="w")

        self.backups_list.bind("<<ListboxSelect>>", self._on_backup_selected)

        self.status_var = tk.StringVar(value="Ready.")
        status = ttk.Label(self.root, textvariable=self.status_var, relief="sunken", anchor="w", padding=4)
        status.pack(fill="x", side="bottom")

    # ---------------- Playthrough handling ----------------

    def _load_last_playthrough_name(self):
        cfg = load_config()
        return cfg.get("current_playthrough")

    def _load_playthroughs(self, select=None):
        names = list_playthroughs()
        self.playthrough_combo["values"] = names
        if not names:
            # Shouldn't happen since ensure_playthroughs_exist() runs first,
            # but guard against a manually emptied folder.
            ensure_playthroughs_exist()
            names = list_playthroughs()
            self.playthrough_combo["values"] = names

        if select and select in names:
            chosen = select
        else:
            chosen = names[0]

        self.playthrough_var.set(chosen)
        self.current_playthrough = chosen
        self._save_current_playthrough()
        self._refresh_backups()

    def _save_current_playthrough(self):
        cfg = load_config()
        cfg["current_playthrough"] = self.current_playthrough
        save_config(cfg)

    def _on_playthrough_selected(self, event=None):
        self.current_playthrough = self.playthrough_var.get()
        self._save_current_playthrough()
        self._refresh_backups()
        self.status_var.set(f"Switched to playthrough '{self.current_playthrough}'.")

    def _current_playthrough_dir(self):
        return PLAYTHROUGHS_DIR / self.current_playthrough

    def _create_playthrough(self):
        name = simpledialog.askstring("Create playthrough", "Name for the new playthrough:", parent=self.root)
        if name is None:
            return
        name = name.strip()
        error = validate_playthrough_name(name)
        if error:
            messagebox.showerror("Invalid name", error)
            return
        target = PLAYTHROUGHS_DIR / name
        if target.exists():
            messagebox.showerror("Already exists", f"A playthrough named '{name}' already exists.")
            return
        target.mkdir(parents=True)
        self._load_playthroughs(select=name)
        self.status_var.set(f"Created playthrough '{name}'.")

    def _rename_playthrough(self):
        if not self.current_playthrough:
            return
        new_name = simpledialog.askstring(
            "Rename playthrough",
            f"New name for '{self.current_playthrough}':",
            parent=self.root,
            initialvalue=self.current_playthrough,
        )
        if new_name is None:
            return
        new_name = new_name.strip()
        error = validate_playthrough_name(new_name)
        if error:
            messagebox.showerror("Invalid name", error)
            return
        if new_name == self.current_playthrough:
            return
        new_path = PLAYTHROUGHS_DIR / new_name
        if new_path.exists():
            messagebox.showerror("Already exists", f"A playthrough named '{new_name}' already exists.")
            return
        old_path = self._current_playthrough_dir()
        old_path.rename(new_path)
        self._load_playthroughs(select=new_name)
        self.status_var.set(f"Renamed playthrough to '{new_name}'.")

    def _delete_playthrough(self):
        if not self.current_playthrough:
            return
        name = self.current_playthrough
        num_backups = len(list((PLAYTHROUGHS_DIR / name).glob("*")))
        confirmed = messagebox.askyesno(
            "Delete playthrough",
            f"Permanently delete playthrough '{name}' and all {num_backups} backup(s) inside it?\n\n"
            "This cannot be undone.",
        )
        if not confirmed:
            return
        shutil.rmtree(PLAYTHROUGHS_DIR / name)

        remaining = list_playthroughs()
        if not remaining:
            ensure_playthroughs_exist()

        self._load_playthroughs()
        self.status_var.set(f"Deleted playthrough '{name}'.")

    # ---------------- Save path handling ----------------

    def _load_saved_path_or_detect(self):
        cfg = load_config()
        saved = cfg.get("save_path")
        self._redetect(select_saved=saved)

    def _redetect(self, select_saved=None):
        self.detected = detect_installations()
        labels = [label for label, path in self.detected]
        self.path_combo["values"] = labels

        if select_saved and Path(select_saved).exists():
            self._set_save_path(Path(select_saved))
            match = next((l for l, p in self.detected if str(p) == str(select_saved)), None)
            self.path_var.set(match if match else str(select_saved))
            self.status_var.set("Loaded previously configured save path.")
        elif self.detected:
            label, path = self.detected[0]
            self._set_save_path(path)
            self.path_var.set(label)
            self.status_var.set(f"Auto-detected {len(self.detected)} install(s).")
        else:
            self.path_var.set("(not set)")
            self.status_var.set("No install auto-detected. Use Browse... to set the save folder manually.")

    def _on_combo_selected(self, event=None):
        idx = self.path_combo.current()
        if 0 <= idx < len(self.detected):
            _, path = self.detected[idx]
            self._set_save_path(path)

    def _browse_path(self):
        chosen = filedialog.askdirectory(title="Select Shadow of War save folder")
        if chosen:
            self._set_save_path(Path(chosen))
            self.path_var.set(str(chosen))

    def _set_save_path(self, path: Path):
        self.save_path = path
        cfg = load_config()
        cfg["save_path"] = str(path)
        save_config(cfg)
        self._refresh_files()

    def _open_save_folder(self):
        if not self.save_path or not self.save_path.exists():
            messagebox.showwarning("No save folder", "Set a valid save folder first.")
            return
        open_in_file_explorer(self.save_path)

    def _open_playthrough_folder(self):
        if not self.current_playthrough:
            return
        open_in_file_explorer(self._current_playthrough_dir())

    def _open_playthroughs_root(self):
        open_in_file_explorer(PLAYTHROUGHS_DIR)

    # ---------------- Launch game ----------------

    def _redetect_launch_options(self):
        self.launch_options = detect_launch_options()

        cfg = load_config()
        custom_exe = cfg.get("custom_exe_path")
        if custom_exe and Path(custom_exe).exists():
            self.launch_options.append((f"Custom — {custom_exe}", "exe", Path(custom_exe)))

        labels = [label for label, _, _ in self.launch_options]
        self.launch_combo["values"] = labels

        if labels:
            preferred = cfg.get("last_launch_label")
            chosen = preferred if preferred in labels else labels[0]
            self.launch_var.set(chosen)
            self.status_var.set(f"Found {len(labels)} way(s) to launch the game.")
        else:
            self.launch_var.set("(none detected)")
            self.status_var.set(
                "Couldn't auto-detect a way to launch the game. Use 'Set custom .exe...' to point at it manually."
            )

    def _browse_game_exe(self):
        chosen = filedialog.askopenfilename(
            title="Select Shadow of War executable",
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")],
        )
        if not chosen:
            return
        cfg = load_config()
        cfg["custom_exe_path"] = chosen
        save_config(cfg)
        self._redetect_launch_options()
        self.launch_var.set(next((l for l in self.launch_combo["values"] if l.startswith("Custom")), self.launch_var.get()))

    def _on_launch_selected(self, event=None):
        """When the user picks a launch method, auto-switch the save folder to match it."""
        selected_label = self.launch_var.get()

        if selected_label.startswith("Steam"):
            match = next((p for l, p in self.detected if l.startswith("Steam")), None)
            if match:
                self._set_save_path(match)
                self.path_var.set(next(l for l, p in self.detected if p == match))
                self.status_var.set("Switched save folder to match the Steam version.")
        elif selected_label.startswith("GOG"):
            match = next((p for l, p in self.detected if l.startswith("GOG")), None)
            if match:
                self._set_save_path(match)
                self.path_var.set(next(l for l, p in self.detected if p == match))
                self.status_var.set("Switched save folder to match the GOG version.")
        # "Custom" exe launches don't tell us which save format to use, so the
        # save folder is left as whatever is currently selected.

    def _do_launch(self):
        selected_label = self.launch_var.get()
        match = next((opt for opt in self.launch_options if opt[0] == selected_label), None)
        if not match:
            messagebox.showwarning(
                "No launch option selected",
                "No launch method is selected. Try Redetect, or set a custom .exe.",
            )
            return

        label, kind, value = match
        cfg = load_config()
        cfg["last_launch_label"] = label
        save_config(cfg)

        try:
            if kind == "steam":
                steam_uri = f"steam://rungameid/{STEAM_APP_ID}"
                if os.name == "nt":
                    os.startfile(steam_uri)  # type: ignore[attr-defined]
                elif platform.system() == "Darwin":
                    subprocess.Popen(["open", steam_uri])
                else:
                    subprocess.Popen(["xdg-open", steam_uri])
            elif kind == "exe":
                exe_path = Path(value)
                if not exe_path.exists():
                    messagebox.showerror("Not found", f"Executable not found:\n{exe_path}")
                    return

                if os.name != "nt" and exe_path.suffix.lower() == ".exe":
                    # A Windows .exe can't run directly on Linux/macOS — try Wine.
                    wine_cmd = shutil.which("wine")
                    if not wine_cmd:
                        messagebox.showerror(
                            "Wine not found",
                            f"'{exe_path.name}' is a Windows program and needs Wine to run "
                            "on this system, but no 'wine' command was found on your PATH.\n\n"
                            "Install Wine (e.g. via your distro's package manager) and try again, "
                            "or point 'Set custom .exe...' at a native Linux binary/launch script instead.",
                        )
                        return
                    subprocess.Popen([wine_cmd, str(exe_path)], cwd=str(exe_path.parent))
                else:
                    subprocess.Popen([str(exe_path)], cwd=str(exe_path.parent))
            self.status_var.set(f"Launching via {label}...")
        except Exception as exc:
            messagebox.showerror("Couldn't launch game", f"Something went wrong launching the game:\n{exc}")

    # ---------------- File listing ----------------

    def _refresh_files(self):
        self.files_list.delete(0, "end")
        if not self.save_path or not self.save_path.exists():
            return
        files = sorted(f for f in self.save_path.glob("*") if f.is_file())
        if not files:
            self.files_list.insert("end", "(no save files found here)")
            return
        for f in files:
            size_kb = f.stat().st_size / 1024
            mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            self.files_list.insert("end", f"{f.name}   ({size_kb:.1f} KB, {mtime})")

    def _refresh_backups(self):
        self.backups_label_var.set(f"Backups — {self.current_playthrough}")
        self.backups_list.delete(0, "end")
        pt_dir = self._current_playthrough_dir()
        if pt_dir.exists():
            backups = sorted((d for d in pt_dir.iterdir() if d.is_dir()), reverse=True)
            for d in backups:
                num_files = len([f for f in d.glob("*") if f.name != BACKUP_META_FILENAME])
                self.backups_list.insert("end", f"{d.name}   ({num_files} file(s))")
        if hasattr(self, "info_var"):
            self.info_var.set("Select a backup to see details.")

    # ---------------- Backup / restore / delete actions ----------------

    def _do_backup(self):
        if not self.save_path or not self.save_path.exists():
            messagebox.showwarning("No save folder", "Set a valid save folder first.")
            return

        current_files = [f for f in self.save_path.glob("*") if f.is_file()]
        if not current_files:
            messagebox.showwarning("Nothing to back up", "No files were found in the save folder.")
            return

        save_name = simpledialog.askstring(
            "Save name",
            f"Name for this save in playthrough '{self.current_playthrough}' "
            "(leave blank to just use the date/time):",
            parent=self.root,
        )
        save_name = save_name.strip() if save_name else ""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"{timestamp}_{save_name}" if save_name else timestamp
        dest = self._current_playthrough_dir() / folder_name

        if dest.exists():
            messagebox.showerror("Backup exists", "A backup with that name already exists.")
            return

        dest.mkdir(parents=True, exist_ok=True)
        for f in current_files:
            shutil.copy2(f, dest / f.name)

        self.status_var.set(f"Backed up {len(current_files)} file(s) to '{folder_name}'.")
        self._refresh_backups()

    def _selected_backup_path(self):
        sel = self.backups_list.curselection()
        if not sel:
            return None
        text = self.backups_list.get(sel[0])
        name = text.split("   (")[0]
        path = self._current_playthrough_dir() / name
        return path if path.exists() else None

    def _do_restore(self):
        backup_path = self._selected_backup_path()
        if not backup_path:
            messagebox.showwarning("No backup selected", "Select a backup from the list first.")
            return
        if not self.save_path or not self.save_path.exists():
            messagebox.showwarning("No save folder", "Set a valid save folder first.")
            return

        confirmed = messagebox.askyesno(
            "Confirm restore",
            f"This will overwrite files in:\n{self.save_path}\n\n"
            f"with the contents of backup '{backup_path.name}' "
            f"from playthrough '{self.current_playthrough}'.\n\n"
            "Your current saves will be safety-backed-up first. Continue?",
        )
        if not confirmed:
            return

        current_files = [f for f in self.save_path.glob("*") if f.is_file()]
        if current_files:
            safety_name = datetime.now().strftime("%Y%m%d_%H%M%S") + "_pre_restore_safety"
            safety_dest = self._current_playthrough_dir() / safety_name
            safety_dest.mkdir(parents=True, exist_ok=True)
            for f in current_files:
                shutil.copy2(f, safety_dest / f.name)

        restored = 0
        for f in backup_path.glob("*"):
            if f.is_file() and f.name != BACKUP_META_FILENAME:
                shutil.copy2(f, self.save_path / f.name)
                restored += 1

        self.status_var.set(f"Restored {restored} file(s) from '{backup_path.name}'.")
        self._refresh_files()
        self._refresh_backups()
        messagebox.showinfo(
            "Restore complete",
            f"Restored {restored} file(s).\n\n"
            "If you use Steam Cloud or GOG Galaxy cloud saves, make sure sync "
            "is off before launching the game, or it may overwrite this restore.",
        )

    def _rename_backup(self):
        backup_path = self._selected_backup_path()
        if not backup_path:
            messagebox.showwarning("No backup selected", "Select a backup from the list first.")
            return

        new_name = simpledialog.askstring(
            "Rename backup",
            f"New name for backup '{backup_path.name}':",
            parent=self.root,
            initialvalue=backup_path.name,
        )
        if new_name is None:
            return
        new_name = new_name.strip()
        error = validate_playthrough_name(new_name)
        if error:
            messagebox.showerror("Invalid name", error)
            return
        if new_name == backup_path.name:
            return

        new_path = self._current_playthrough_dir() / new_name
        if new_path.exists():
            messagebox.showerror("Already exists", f"A backup named '{new_name}' already exists.")
            return

        backup_path.rename(new_path)
        self.status_var.set(f"Renamed backup to '{new_name}'.")
        self._refresh_backups()

    def _set_backup_location(self):
        backup_path = self._selected_backup_path()
        if not backup_path:
            messagebox.showwarning("No backup selected", "Select a backup from the list first.")
            return

        meta = load_backup_meta(backup_path)
        current_location = meta.get("location", "(none)")

        chosen = ask_choice(
            self.root,
            "Set location",
            f"Character location for backup '{backup_path.name}':",
            GAME_LOCATIONS,
            initial=current_location,
        )
        if chosen is None:
            return

        if chosen == "(none)":
            meta.pop("location", None)
        else:
            meta["location"] = chosen
        save_backup_meta(backup_path, meta)

        self.status_var.set(f"Set location for '{backup_path.name}' to '{chosen}'.")
        self._on_backup_selected()

    def _set_dlc_status(self):
        backup_path = self._selected_backup_path()
        if not backup_path:
            messagebox.showwarning("No backup selected", "Select a backup from the list first.")
            return

        meta = load_backup_meta(backup_path)
        current_dlc = meta.get("dlc", {})

        chosen = ask_checklist(
            self.root,
            "Set DLC status",
            f"Mark completed DLC campaigns for backup '{backup_path.name}':",
            DLC_CAMPAIGNS,
            initial=current_dlc,
        )
        if chosen is None:
            return

        meta["dlc"] = chosen
        save_backup_meta(backup_path, meta)

        self.status_var.set(f"Updated DLC status for '{backup_path.name}'.")
        self._on_backup_selected()

    def _on_backup_selected(self, event=None):
        backup_path = self._selected_backup_path()
        if not backup_path:
            self.info_var.set("Select a backup to see details.")
            return

        files = [f for f in backup_path.glob("*") if f.is_file() and f.name != BACKUP_META_FILENAME]
        total_bytes = sum(f.stat().st_size for f in files)
        total_kb = total_bytes / 1024
        created = datetime.fromtimestamp(backup_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")

        size_str = f"{total_kb / 1024:.2f} MB" if total_kb >= 1024 else f"{total_kb:.1f} KB"

        meta = load_backup_meta(backup_path)
        location = meta.get("location")
        dlc = meta.get("dlc", {})

        info_text = (
            f"Name: {backup_path.name}\n"
            f"Playthrough: {self.current_playthrough}\n"
            f"Created: {created}\n"
            f"Total size: {size_str}"
        )
        if location:
            info_text += f"\nLocation: {location}"
        for campaign in DLC_CAMPAIGNS:
            status = "Complete" if dlc.get(campaign, False) else "Incomplete"
            info_text += f"\n{campaign}: {status}"

        self.info_var.set(info_text)

    def _do_delete(self):
        backup_path = self._selected_backup_path()
        if not backup_path:
            messagebox.showwarning("No backup selected", "Select a backup from the list first.")
            return
        confirmed = messagebox.askyesno("Confirm delete", f"Permanently delete backup '{backup_path.name}'?")
        if confirmed:
            shutil.rmtree(backup_path)
            self.status_var.set(f"Deleted backup '{backup_path.name}'.")
            self._refresh_backups()


def resource_path(filename):
    """Resolve a bundled resource's path, whether running as a plain script
    or as a PyInstaller-built exe (which extracts data files to sys._MEIPASS)."""
    base_path = getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)
    return Path(base_path) / filename


def main():
    APP_DIR.mkdir(parents=True, exist_ok=True)
    root = tk.Tk()

    # iconbitmap() only understands .ico on Windows (on X11/Linux it expects
    # the old XBM format instead), so use iconphoto() with a PNG everywhere else.
    if os.name == "nt":
        icon_path = resource_path("icon.ico")
        if icon_path.exists():
            try:
                root.iconbitmap(default=str(icon_path))
            except tk.TclError:
                pass
    else:
        icon_path = resource_path("icon.png")
        if icon_path.exists():
            try:
                icon_image = tk.PhotoImage(file=str(icon_path))
                root.iconphoto(True, icon_image)
                root._icon_image_ref = icon_image  # keep a reference alive
            except tk.TclError:
                pass

    app = SaveManagerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
