# Onigiri Loader — Installation & Setup

For Windows. There is no installer — the app is a portable folder you extract
and run.

> **Single player only.** Mods installed this way risk a ban in GTA Online.
> Use it for offline play only.

---

## 1. What you need

| | |
|---|---|
| **Required** | Windows 10/11 · GTA V Enhanced (the folder containing `GTA5_Enhanced.exe`) · `ScriptHookV.dll` (the `.asi` plugin engine) |
| **Recommended** | NaturalVision Enhanced as your baseline — or the stock-GTA V setup (core files + the skeleton onigiri folder the loader creates) |
| **Optional** | 7-Zip or WinRAR (free, 7-zip.org) to install `.7z`/`.rar` mods · ScriptHookVDotNet if a mod uses `.NET` scripts |

`.zip` mods never need anything extra.

## 2. Install

1. Download `OnigiriLoader-win64.zip` (link from the release page / forum post).
2. **Extract it into a folder of its own** — e.g. `C:\Games\OnigiriLoader`,
   or anywhere next to your games. Do not leave it in *Downloads*.
   - No admin rights are needed for this, and it should **not** live in
     Program Files.
3. That is the complete install — no setup wizard, and nothing is written to the registry.
4. *Optional:* right-click `OnigiriLoader.exe` →
   **Send to → Desktop (create shortcut)**.

## 3. First launch

1. Double-click **`OnigiriLoader.exe`**.
2. **UAC prompt → Yes.** The app asks for permission to write into your game
   folder. If you decline, the app still opens, but saving files will fail
   when the game sits in a protected location (e.g. Program Files).
3. Point it at your game:
   - **Scan** — searches your drives for GTA V Enhanced and the core files, or
   - **Browse...** — pick the folder that contains `GTA5_Enhanced.exe`.
4. Look at the **core files** row (green ✓ = present, red ✗ = missing):
   `onigiri.asi`, `ScriptHookV.dll`, `xinput1_4.dll` (the ASI loader), and
   `ScriptHookVDotNet.asi` (optional, for .NET scripts).
   - Missing any? Use **Install core files**, select the file(s) you have
     (from your NVE download, or the core-file set for the stock-GTA V
     pathway), and the app copies them next to the game exe. If you select
     both `dinput8.dll` and `xinput1_4.dll`, only the Enhanced one is
     installed.
   - If nothing is present and you're starting from stock GTA V: install
     `onigiri.asi`, `nve.asi`, `xinput1_4.dll`, and `ScriptHookV.dll`
     (required for `.asi` plugins) — the loader creates the onigiri skeleton
     folder automatically the first time a mod is enabled.
5. That is all. The app retains your game folder, mods, and settings between runs.

## 4. Install your first mod

1. **Add archive** → choose the mod's `.zip` / `.7z` / `.rar` (or a single
   `.rpf` DLC pack) → give it a name.
2. **Tick** the mod to enable it — the loader deploys its files.
3. Read the **activity log** (bottom of the window): what was deployed,
   merged, skipped, or flagged.
4. Launch the game (offline) and check your mod.

## 5. Everyday use — button reference

| Button | What it does |
|---|---|
| **Add archive** | Add a mod from a `.zip` / `.7z` / `.rar` archive or a `.rpf` |
| **Enable / Disable** | Install or remove the selected mod's files (originals restored) |
| **Move up / Move down** | Change priority — when two mods conflict, the **lower** mod takes precedence |
| **Remove** | Uninstall the selected mod and remove it from the library |
| **Re-apply** | Redeploy all enabled mods (after changing folders manually) |
| **Install core files** | Copy core files next to the game exe |
| **Folder guide** | Show the mod folder layout the loader expects |
| **View README** | Read the selected mod's README + the folders the loader found in it |
| **DLC packs** | Your packs, their `dlclist.xml` status, load order, conflicts + fixes |
| **Open onigiri folder** | Open the onigiri folder in File Explorer |
| **Open base folder** | Show the saved original files (merge baselines) |
| **Reset all** | Unload all mods, restore the original files, and clear the library and settings — with an "Are you sure?" confirmation |

## 6. Updating the app

1. Download the new zip.
2. Extract it **over the existing folder** (replace the files) — or extract to
   a fresh folder and use that one.
3. Your mods, library, backups, and settings live in
   `%APPDATA%\OnigiriLoader` and are **not** touched by updating the app.

## 7. Uninstalling

1. **Disable or Remove** the mods you no longer want — this restores the
   original game files.
2. Delete the `OnigiriLoader` folder you extracted.
3. Delete `%APPDATA%\OnigiriLoader` (Win+R → `%APPDATA%` → `OnigiriLoader`).

That is the complete footprint — nothing else was changed on the system.

## 8. Troubleshooting

| Problem | Fix |
|---|---|
| UAC declined, or files will not save | Accept the UAC prompt, or move the game out of a protected folder (e.g. Program Files) |
| `.7z` / `.rar` will not open | Install 7-Zip or WinRAR (free) — the app uses whichever you have |
| `.NET` script mod does nothing | Install the ScriptHookVDotNet (Enhanced) package — the log warns you when it is missing |
| Mod is ticked but nothing happens | Read the log for skips/warnings, try **Re-apply**, and confirm the mod targets the Enhanced game |
| Unusual visuals or a crash | Disable the most recently enabled mod; open **DLC packs** to check for conflicting packs |
| The setup is not working | **Reset all** (with an "Are you sure?" confirmation) restores the original files and starts fresh; then add one mod at a time |

## 9. File locations

| Location | What's in it |
|---|---|
| The folder you extracted | the app: `OnigiriLoader.exe` + `_internal\`, plus the READMEs |
| `%APPDATA%\OnigiriLoader` | everything the app stores: `library\` (your mods), `backup\`, `base\` (saved originals), `merged\`, `state.json` |
| Your game folder | `onigiri\` (mod content), core files next to `GTA5_Enhanced.exe`, `scripts\` (.NET scripts) |
