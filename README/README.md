# Shadow of War Save Manager

A tool for backing up, organizing, and restoring your Middle-earth: Shadow
of War save files — with support for multiple playthroughs, Steam/GOG
detection, one-click game launching, and per-backup notes like story
location and DLC completion. Works on Windows and Linux (including
CachyOS/Arch).

---

## Getting Started

### Windows
Run **ShadowOfWarSaveManager_Setup.exe** and follow the install wizard. It
installs the app, adds a Start Menu shortcut (and an optional Desktop
shortcut), and registers a proper uninstaller in Windows' "Add or Remove
Programs".

> Windows may show a SmartScreen warning the first time ("Windows protected
> your PC") since this is an unsigned personal build, not because anything
> is wrong with it. Click **More info → Run anyway** to continue.

### Linux (CachyOS / Arch / other distros)

Install the pre-built package with pacman:
```bash
sudo pacman -U shadowofwarsavemanager-1.0.0-1-x86_64.pkg.tar.zst
```
This installs the binary, icon, and application menu entry, and registers
it with pacman so it can be cleanly removed later with:
```bash
sudo pacman -R shadowofwarsavemanager
```
Launch it by running `shadowofwarsavemanager` in a terminal, or find it in
your app menu.

---

## First-Time Setup

When you open the app, it automatically tries to find your save folder:
- **Steam (Windows)** — via the Steam install found in your registry
- **Steam (Linux)** — checks native Steam locations (`~/.steam/steam`,
  `~/.local/share/Steam`, Flatpak Steam paths), and looks in *two* possible
  spots: the Steam Cloud sync folder, and the local save folder inside the
  game's Proton prefix. If both exist, they show up as separate options.
- **GOG (Windows)** — via the GOG Galaxy registry entries
- **Microsoft Store (Windows)** — via its known package location

If it finds a match, the **Save folder** dropdown at the top fills in
automatically. If nothing is detected (or you want a different one), click
**Browse...** and point it at the correct folder yourself. You can also
click **Detect** any time to re-scan.

> GOG auto-detection only works on Windows — GOG doesn't have a native
> Linux build of this game. If you're running a GOG copy through
> Wine/Lutris/Heroic on Linux, use **Set custom .exe...** under Launch to
> point at it manually (see below).

---

## Launching the Game

The **Launch via** row lets you start the game directly from the app:
- If Steam (or GOG, on Windows) installs are detected, they'll appear in
  the dropdown.
- If neither is found, click **Set custom .exe...** and browse to the
  game's executable once — it'll be remembered from then on.
- Click **Launch Game** to start it.

Picking **Steam** or **GOG** here also automatically switches the **Save
folder** dropdown to match that version, so you don't end up backing up or
restoring against the wrong save location.

> **Linux note:** if you point "Set custom .exe..." at a Windows `.exe`
> (e.g. a GOG install running under Wine), the app automatically launches
> it through `wine` for you. If Wine isn't installed, you'll get a clear
> message telling you so instead of a silent failure.

---

## Playthroughs

Playthroughs let you keep separate save histories for different characters,
difficulty settings, or experiments — each with its own independent list of
backups.

- **Create...** — start a new, empty playthrough.
- **Rename...** — rename the current one (its backups move with it).
- **Delete** — permanently deletes the playthrough and everything backed up
  inside it (you'll be asked to confirm first).
- **Open backup folder** — opens the current playthrough's folder in your
  file explorer.
- **Open all playthroughs...** — opens the parent folder containing every
  playthrough, in case you want to browse between them directly.

Whichever playthrough is selected determines which backups show up in the
**Backups** list on the right.

---

## Backing Up and Restoring Saves

**Left panel — Current save files**
Shows what's currently in your live save folder. Click **Refresh** any time
to update the list.

**Backup current saves...**
Copies everything in your save folder into a new, timestamped backup inside
the current playthrough. You'll be asked for an optional **save name** — if
you leave it blank, the backup is just named after the date and time.

**Right panel — Backups**
Lists every backup saved under the current playthrough, newest first.

- **Restore selected** — copies the chosen backup's files back into your
  live save folder. Before doing this, it automatically makes a safety
  backup of whatever's currently there, so a restore is never a one-way
  door.
- **Rename selected** — renames that backup.
- **Delete selected** — permanently deletes it (after confirming).

> **Cloud saves:** If you use Steam Cloud or GOG Galaxy cloud sync, turn
> sync off before launching the game after a restore — otherwise cloud sync
> could overwrite your restored save.

---

## Tagging Backups (Location & DLC Status)

Select a backup and use:

- **Set location...** — tag it with the in-game region you were in when it
  was made (e.g. Seregost, Nurnen, Cirith Ungol, Minas Ithil, Gorgoroth,
  Lithlad). Handy for finding "the save right before I went to X" later.
- **Set DLC status...** — mark whether *The Blade of Galadriel* and/or *The
  Desolation of Mordor* were completed as of that save.

Both show up automatically in the **Backup info** card below the list once
you select that backup.

---

## Backup Info Card

Selecting any backup shows:
- **Name** — the backup's folder name
- **Playthrough** — which playthrough it belongs to
- **Created** — date and time it was made
- **Total size** — combined size of the saved files
- **Location** — if you've tagged one
- **DLC campaign status** — Complete/Incomplete for each DLC campaign

---

## Where Everything Is Stored

All of this tool's own data (not your actual game saves) lives under your
home folder, on both Windows and Linux:

```
~/ShadowOfWarSaveManager/
├── config.json          # remembered settings (save path, last playthrough, etc.)
└── playthroughs/
    ├── Default/
    │   ├── 20260714_153000_before_boss_fight/
    │   │   ├── <your save files>
    │   │   └── _backup_meta.json   (location/DLC tags — hidden from the app's file counts)
    │   └── ...
    └── <other playthroughs>/
```

Deleting the whole `ShadowOfWarSaveManager` folder resets the app back to a
blank slate (it will not touch your actual game save folder).

---

## Troubleshooting

- **Nothing auto-detected for save folder / launch:** Use **Browse...** /
  **Set custom .exe...** to point at things manually — detection is
  best-effort and can vary by system, especially for GOG.
- **Restored save doesn't show up in-game:** Make sure cloud sync (Steam
  Cloud / GOG Galaxy) isn't overwriting it — turn sync off before launching.
- **(Windows) SmartScreen / antivirus flags the exe:** Expected for an
  unsigned personal build — it's not a sign anything is actually wrong.
- **(Linux) "Wine not found" when launching a custom .exe:** Install Wine
  (e.g. `sudo pacman -S wine`), or point the custom exe setting at a native
  Linux binary/launch script instead.
- **(Linux) App menu entry doesn't appear right after installing:** Log out
  and back in, or restart your desktop panel — menu caches sometimes need a
  refresh to pick up new `.desktop` entries.
