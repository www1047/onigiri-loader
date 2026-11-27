# Onigiri Loader

A mod manager for **GTA V Enhanced (single player)** built around the
NaturalVision Enhanced "onigiri" folder layout. It installs mods for you,
puts every file where it belongs, keeps your original game files safe, and
takes everything back out cleanly when you switch mods off.

> **Single player only.** Anything you load with this can be seen by GTA
> Online's anti-cheat and risks a ban. Use it for offline play only.

## Download

**v0.5.0** — [OnigiriLoader-win64.zip](https://github.com/www1047/onigiri-loader/releases/download/v0.5.0/OnigiriLoader-win64.zip) · [all releases](https://github.com/www1047/onigiri-loader/releases)

---

## What it does

- **Installs mods from archives** — `.zip` always works; `.7z` and `.rar` work
  if you have 7-Zip or WinRAR installed (both free). You can also add a single
  `.rpf` DLC pack.
- **Installs NaturalVision Enhanced** — add an NVE archive and it places the
  `onigiri` folder and core files exactly like any other mod, so NVE is a
  first-class baseline rather than a separate manual install.
- **Library with one-click on/off** — every mod sits in a list you can tick on
  and off, reorder, or remove. Ticking a mod installs its files; unticking
  removes them and restores whatever it replaced.
- **Places files correctly** — onigiri content goes to the right place in
  `onigiri\` (common, platform, dlcpacks), `.asi` plugins go next to the game
  exe, and `.NET` scripts go to `scripts\` — you don't need to know the layout.
- **Enhanced first** — when a mod ships both old-game and Enhanced content,
  only the Enhanced version is installed (same for the ASI loader:
  `xinput1_4.dll` over `dinput8.dll`).
- **Combines mods that edit the same file** — text files several mods touch are
  three-way merged (using the files already in your onigiri folder, e.g.
  NaturalVision Enhanced's, as the baseline). Conflicts that can't be merged
  are resolved by list order: the mod lower in the list wins.
- **DLC packs** — packs are placed into `dlcpacks\<name>\dlc.rpf`, registered
  in `dlclist.xml` for you, and checked against other mods' packs. The
  "DLC packs" window shows every pack, its load order, and one-click fixes.
- **Reads a mod's README** — so mods with loose files still get placed
  sensibly.
- **Core files** — shows a green ✓ / red ✗ status for the files the game needs
  next to the exe (`onigiri.asi`, `ScriptHookV.dll`, `xinput1_4.dll`,
  `ScriptHookVDotNet.asi`) and can install them with "Install core files".
- **Finds your game for you** — "Scan" searches your drives for GTA V Enhanced
  and the core files; "Browse" if you already know where it is.
- **Keeps backups** — anything overwritten is saved first and restored the
  moment a mod is disabled or removed. "Open base folder" shows the saved
  originals.
- **Starts over cleanly** — "Reset all" (with an "Are you sure?" prompt)
  unloads every mod, restores the original game files, and returns the loader
  to a fresh first-time state.
- **Remembers everything** — your mods, order, and settings are kept in
  `%APPDATA%\OnigiriLoader` and survive restarts.
- **Dark or light theme**, an activity log of everything it did, and tooltips
  on every button.

## What it does **not** do

- **Not for GTA Online.** Single player only — online use risks a ban.
- **Doesn't download mods.** No mod database, no links; you provide the
  archives from wherever you got them.
- **Doesn't run NVE's installer or configurator.** It installs NVE's files
  from an archive (see above) but won't fetch NVE, run NVE's own setup, or
  touch NVE's in-game settings.
- **Doesn't use OpenIV, ever.** `.oiv` packages and the OpenIV support files
  (`openiv.asi` / `openrpf.asi`) are never installed — they cause
  compatibility issues and crashes.
- **Doesn't touch the game itself.** It only adds and removes mod files in
  your game folder. The game exe, registry, and system files are never
  modified, and nothing is injected into the game.
- **Doesn't convert old (legacy) mods to Enhanced.** If a mod ships an
  Enhanced version, that's what gets installed; legacy files are a fallback
  only. If a mod is legacy-only, it may still work, but that's the mod's
  problem, not a conversion.
- **Doesn't merge binary conflicts.** Only text files are merged; for anything
  else, list order decides.
- **Is not a launcher.** It doesn't start the game, manage saves, or do
  anything to the game beyond placing mod files.
- **Windows only.** The app is a Windows program.

## How it works

Mods for GTA V Enhanced end up in a few well-defined places, and the loader
knows them all by heart:

- **Next to the game exe** — the ASI loader, `.asi` plugins (with their
  `.ini` files), and the input DLL.
- **`scripts\`** — `.NET` scripts and their config files.
- **`onigiri\`** — the mod content: `common\` (gameplay data such as weather,
  effects and timecycle), `platform\` (graphics and engine data), and
  `dlcpacks\` (additions the game loads on top of the world).

Enable a mod and its files are copied to the right place; disable it and they
come back out, with whatever they replaced restored from the loader's private
backups. Text files that several mods edit are three-way merged using the
files already in your onigiri folder as the baseline; where a merge isn't
possible, the mod lower in your list wins. Every action is written to the
activity log in plain English, and your whole setup — mods, order, settings —
is kept in `%APPDATA%\OnigiriLoader` and survives restarts.

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
   and core files, and every other mod you add sits on top of it.
2. **Stock GTA V + core files.** No NVE? Use **Install core files** to copy
   the core set — `onigiri.asi`, `nve.asi`, `xinput1_4.dll`, and
   `ScriptHookV.dll` (required for `.asi` plugins). The loader creates the
   skeleton `onigiri\` folder automatically the first time a mod is enabled.

[INSTALL.md](INSTALL.md) has the full walkthrough;
[MOD_COMPATIBILITY.md](MOD_COMPATIBILITY.md) explains the layout for mod
authors.

## Getting started

1. **Extract** the release zip to any folder (e.g. your Games folder).
2. **Run** `OnigiriLoader\OnigiriLoader.exe`. A UAC prompt appears — that's
   the app asking permission to write into your game folder (declining it
   only matters if your game is in a protected location like Program Files).
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
   `.rpf` DLC pack), give each a name, and **tick** it to enable it
   (double-clicking a row works too).
7. **Read the activity log** at the bottom of the window — every deploy,
   merge, skip, and flag is written there in plain English.
8. **Play offline.** To take a mod back out, untick it (your originals are
   restored); **Remove** also drops it from the library.

## Buttons at a glance

| Button | What it does |
|---|---|
| **Scan** | Searches your drives for GTA V Enhanced and the core files |
| **Browse...** | Pick the game folder yourself |
| **Add archive** | Install a mod from a `.zip` / `.7z` / `.rar`, or a single `.rpf` file — the loader works out where each file goes |
| **Enable / Disable** | Install the selected mod's files, or remove them and restore anything they replaced (double-clicking a row does the same) |
| **Move up / Move down** | Change priority — where two mods edit the same lines, the mod lower in the list wins |
| **Remove** | Uninstall the selected mod and drop it from the library |
| **Re-apply** | Redeploy every enabled mod now — use it after changing folders or editing the library by hand |
| **Install core files** | Copy `onigiri.asi`, `ScriptHookV.dll`, or the ASI loader (`xinput1_4.dll`) next to the exe; if both `dinput8.dll` and `xinput1_4.dll` are selected, only the Enhanced one goes in |
| **Folder guide** | Show the folder layout mods should follow |
| **Open onigiri folder** | Open `onigiri\` in File Explorer |
| **View README** | Read the selected mod's README and see which folders the loader found in it |
| **Open base folder** | Open the saved original files (the merge baseline) |
| **DLC packs** | Show every DLC pack, whether it's listed in `dlclist.xml`, and any conflicts — with one-click fixes |
| **Reset all** | Unload every mod (restoring originals), delete the library and backups, fresh first-time state — asks "Are you sure?", and can't be undone |

## Uninstalling

- Untick or **Remove** the mods you no longer want (this restores your
  original game files).
- Delete the `OnigiriLoader` folder you extracted.
- Delete `%APPDATA%\OnigiriLoader` to remove the library, backups, and
  settings. That's the whole footprint.

## Questions you might have

**Do I need OpenIV?** No. The loader never uses it and never installs
OpenIV packages.

**Will it break my NaturalVision Enhanced install?** It uses the files already
in your onigiri folder as the merge baseline, and disabling a mod restores
what it changed. As with any modding, keep your own backups of anything you
love.

**Why does a UAC prompt appear?** The app needs to write files into your game
folder. It asks itself for the rights it needs; the manifest-level
"always admin" demand is not used.

**Can two mods that edit the same file both work?** Usually yes — text file
edits are merged where possible; where they can't be, the mod lower in the
list wins, and the log tells you what happened.

**Where do my mods actually go?** Into `onigiri\` next to the game exe
(common/platform/dlcpacks), with `.asi` plugins and `scripts\` in the game
root. The "Folder guide" button shows the full layout.

**I installed the wrong thing / it's all a mess.** Untick everything, or use
**Reset all** (it asks "Are you sure?") to restore the originals and start
fresh.

**Can I install NaturalVision Enhanced with this?** Yes — exactly like any
other mod: **Add archive**, name it, tick it. The core files and the
`onigiri` folder get placed, and everything else you add sits on top of it.

**Are my saves touched?** No. The loader only adds and removes mod files in
your game folder; saves, the game exe, and system files are never modified.

**Where are the backups?** In `%APPDATA%\OnigiriLoader\` — `backup\` holds
whatever a mod overwrote (restored when you disable or remove the mod) and
`base\` holds the original files used as the merge baseline. **Open base
folder** shows them.

**Will any mod work?** Any mod that follows the onigiri layout — that's what
the loader is built for. Files it can't place are reported in the log rather
than guessed at, and mods shipped as OpenIV `.oiv` packages aren't supported.
