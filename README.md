# Onigiri Loader

A mod manager for **GTA V Enhanced (single player)** built around the
NaturalVision Enhanced "onigiri" folder layout. It installs mods for you,
places every file in the correct location, keeps your original game files safe, and
removes them cleanly when you disable a mod.

> **Single player only.** Content loaded this way may be detected by GTA
> Online's anti-cheat and risks a ban. Use it for offline play only.

## Download

**v0.5.0** — [OnigiriLoader-win64.zip](https://github.com/www1047/onigiri-loader/releases/download/v0.5.0/OnigiriLoader-win64.zip) · [all releases](https://github.com/www1047/onigiri-loader/releases)

---

## What it does

- **Installs mods from archives** — `.zip` always works; `.7z` and `.rar` work
  if you have 7-Zip or WinRAR installed (both free). You can also add a single
  `.rpf` DLC pack.
- **Installs NaturalVision Enhanced** — add an NVE archive and it places the
  `onigiri` folder and core files exactly like any other mod. NVE is fully
  supported as a baseline and requires no separate manual install.
- **Library with one-click on/off** — every mod appears in a list you can
  enable, disable, reorder, or remove. Enabling a mod installs its files;
  disabling it removes them and restores the files it replaced.
- **Places files correctly** — onigiri content goes to the right place in
  `onigiri\` (common, platform, dlcpacks), `.asi` plugins go next to the game
  exe, and `.NET` scripts go to `scripts\`. No knowledge of the layout is
  required.
- **Enhanced first** — when a mod ships both old-game and Enhanced content,
  only the Enhanced version is installed (same for the ASI loader:
  `xinput1_4.dll` over `dinput8.dll`).
- **Combines mods that edit the same file** — text files several mods touch are
  three-way merged (using the files already in your onigiri folder, e.g.
  NaturalVision Enhanced's, as the baseline). Conflicts that cannot be merged
  are resolved by list order: the lower mod in the list takes precedence.
- **DLC packs** — packs are placed into `dlcpacks\<name>\dlc.rpf`, registered
  in `dlclist.xml` for you, and checked against other mods' packs. The
  "DLC packs" window shows every pack, its load order, and one-click fixes.
- **Reads a mod's README** — so mods with loose files are still placed
  correctly.
- **Core files** — shows a green ✓ / red ✗ status for the files the game needs
  next to the exe (`onigiri.asi`, `ScriptHookV.dll`, `xinput1_4.dll`,
  `ScriptHookVDotNet.asi`) and can install them with "Install core files".
- **Locates the game automatically** — "Scan" searches your drives for GTA V
  Enhanced and the core files; "Browse" if you already know where it is.
- **Keeps backups** — anything overwritten is saved first and restored as
  soon as the mod is disabled or removed. "Open base folder" shows the saved
  originals.
- **Resets cleanly** — "Reset all" (with an "Are you sure?" confirmation)
  unloads every mod, restores the original game files, and returns the loader
  to a fresh first-time state.
- **Retains your configuration** — your mods, order, and settings are stored
  in `%APPDATA%\OnigiriLoader` and persist across restarts.
- **Dark or light theme**, an activity log of everything it did, and tooltips
  on every button.

## What it does **not** do

- **Not for GTA Online.** Single player only — online use risks a ban.
- **Does not download mods.** No mod database, no links; you provide the
  archives from wherever you got them.
- **Does not run NVE's installer or configurator.** It installs NVE's files
  from an archive (see above) but does not fetch NVE, run NVE's own setup, or
  modify NVE's in-game settings.
- **Does not use OpenIV.** `.oiv` packages and the OpenIV support files
  (`openiv.asi` / `openrpf.asi`) are never installed — they cause
  compatibility issues and crashes.
- **Does not modify the game itself.** It only adds and removes mod files in
  your game folder. The game exe, registry, and system files are never
  modified, and nothing is injected into the game.
- **Does not convert legacy mods to Enhanced.** If a mod ships an
  Enhanced version, that version is installed; legacy files are a fallback
  only. If a mod is legacy-only, it may still work, but that is a limitation
  of the mod, not a conversion by the loader.
- **Does not merge binary conflicts.** Only text files are merged; for
  anything else, list order determines the outcome.
- **Is not a launcher.** It does not start the game, manage saves, or make
  any changes to the game beyond placing mod files.
- **Windows only.** The app is a Windows program.

## How it works

Mods for GTA V Enhanced end up in a few well-defined places, all of which
the loader manages automatically:

- **Next to the game exe** — the ASI loader, `.asi` plugins (with their
  `.ini` files), and the input DLL.
- **`scripts\`** — `.NET` scripts and their config files.
- **`onigiri\`** — the mod content: `common\` (gameplay data such as weather,
  effects and timecycle), `platform\` (graphics and engine data), and
  `dlcpacks\` (additions the game loads on top of the world).

Enabling a mod copies its files to the correct location; disabling it
removes them and restores the files they replaced from the loader's private
backups. Text files that several mods edit are three-way merged using the
files already in your onigiri folder as the baseline; where a merge is not
possible, the lower mod in the list takes precedence. Every action is recorded
in the activity log in clear terms, and your complete setup — mods, order,
settings — is stored in `%APPDATA%\OnigiriLoader` and persists across
restarts.

## Requirements

| | |
|---|---|
| **Required** | Windows 10/11 · GTA V Enhanced (the folder containing `GTA5_Enhanced.exe`) · `ScriptHookV.dll` (the `.asi` plugin engine) |
| **Recommended** | NaturalVision Enhanced as your baseline (or the stock-GTA V core-file setup) |
| **Optional** | 7-Zip or WinRAR (free) to install `.7z`/`.rar` mods · ScriptHookVDotNet if a mod uses `.NET` scripts |

## Lay the foundation (pick one)

The loader manages mods; the engine that loads them comes from one of two
setups. Both are fully supported:

1. **NaturalVision Enhanced (recommended).** Add your NVE archive with
   **Add archive**, name it, and tick it. That installs the `onigiri` folder
   and core files, and every other mod you add is layered on top of it.
2. **Stock GTA V + core files.** Without NVE, use **Install core files** to copy
   the core set — `onigiri.asi`, `nve.asi`, `xinput1_4.dll`, and
   `ScriptHookV.dll` (required for `.asi` plugins). The loader creates the
   skeleton `onigiri\` folder automatically the first time a mod is enabled.

[INSTALL.md](INSTALL.md) has the full walkthrough;
[MOD_COMPATIBILITY.md](MOD_COMPATIBILITY.md) explains the layout for mod
authors.

## Getting started

1. **Extract** the release zip into a folder of its own
   (e.g. `C:\Games\OnigiriLoader`).
2. **Run** `OnigiriLoader.exe`. A UAC prompt appears — the app
   is requesting permission to write into your game folder (declining it only
   matters if your game is in a protected location such as Program Files).
3. **Point it at the game** — **Scan** searches your drives for GTA V
   Enhanced and the core files, or **Browse...** picks the folder that
   contains `GTA5_Enhanced.exe`. The `onigiri\` folder is set next to the
   exe automatically.
4. **Check the core-files row** — green ✓ = present, red ✗ = missing. If
   anything is missing, use **Install core files** and pick the files you
   have (from your NVE download, or the stock-GTA V core set).
5. **Lay the foundation** (above): add your NVE archive and tick it, or
   install the core-file set for stock GTA V.
6. **Add mods** with **Add archive** (`.zip` / `.7z` / `.rar`, or a single
   `.rpf` DLC pack), give each a name, and enable it
   (double-clicking a row has the same effect).
7. **Read the activity log** at the bottom of the window — every deploy,
   merge, skip, and flag is recorded there in clear terms.
8. **Play offline.** To remove a mod, disable it (your original files are
   restored); **Remove** also deletes it from the library.

## Buttons at a glance

| Button | What it does |
|---|---|
| **Scan** | Searches your drives for GTA V Enhanced and the core files |
| **Browse...** | Select the game folder manually |
| **Add archive** | Install a mod from a `.zip` / `.7z` / `.rar`, or a single `.rpf` file — the loader determines where each file goes |
| **Enable / Disable** | Install the selected mod's files, or remove them and restore the files they replaced (double-clicking a row has the same effect) |
| **Move up / Move down** | Change priority — where two mods edit the same lines, the lower mod in the list takes precedence |
| **Remove** | Uninstall the selected mod and remove it from the library |
| **Re-apply** | Redeploy every enabled mod now — use it after changing folders or editing the library manually |
| **Install core files** | Copy `onigiri.asi`, `ScriptHookV.dll`, or the ASI loader (`xinput1_4.dll`) next to the exe; if both `dinput8.dll` and `xinput1_4.dll` are selected, only the Enhanced version is installed |
| **Folder guide** | Show the folder layout mods should follow |
| **Open onigiri folder** | Open `onigiri\` in File Explorer |
| **View README** | Read the selected mod's README and see which folders the loader found in it |
| **Open base folder** | Open the saved original files (the merge baseline) |
| **DLC packs** | Show every DLC pack, whether it's listed in `dlclist.xml`, and any conflicts — with one-click fixes |
| **Reset all** | Unload every mod (restoring originals), delete the library and backups, and return to a fresh first-time state — requires an "Are you sure?" confirmation and cannot be undone |

## Uninstalling

- Disable or **Remove** the mods you no longer want (this restores the
  original game files).
- Delete the `OnigiriLoader` folder you extracted.
- Delete `%APPDATA%\OnigiriLoader` to remove the library, backups, and
  settings. That is the complete footprint.

## Frequently asked questions

**Do I need OpenIV?** No. The loader never uses it and never installs
OpenIV packages.

**Will it interfere with my NaturalVision Enhanced install?** It uses the files
already in your onigiri folder as the merge baseline, and disabling a mod
restores the files it changed. As with any modding, keep your own backups of
anything important to you.

**Why does a UAC prompt appear?** The app requires write access to the game
folder and requests the elevated rights it needs; the manifest-level
"always run as administrator" requirement is not used.

**Can two mods that edit the same file both work?** Usually — text file
edits are merged where possible; where they cannot be, the lower mod in the
list takes precedence, and the log records the outcome.

**Where are my mods installed?** Into `onigiri\` next to the game exe
(common/platform/dlcpacks), with `.asi` plugins and `scripts\` in the game
root. The "Folder guide" button shows the full layout.

**I installed the wrong thing / the setup is not working.** Disable
everything, or use **Reset all** (with an "Are you sure?" confirmation) to
restore the originals and start fresh.

**Can I install NaturalVision Enhanced with this?** Yes — exactly like any
other mod: **Add archive**, name it, enable it. The core files and the
`onigiri` folder are placed, and everything else you add is layered on top
of it.

**Are my saves affected?** No. The loader only adds and removes mod files in
your game folder; saves, the game exe, and system files are never modified.

**Where are the backups?** In `%APPDATA%\OnigiriLoader\` — `backup\` holds
the files a mod overwrote (restored when the mod is disabled or removed) and
`base\` holds the original files used as the merge baseline. **Open base
folder** shows them.

**Will any mod work?** The loader is designed for mods that follow the
onigiri layout. Files that cannot be placed are reported in the log rather
than guessed at, and mods shipped as OpenIV `.oiv` packages are not
supported.
